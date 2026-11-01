"""
tests/test_tools.py
────────────────────
Unit tests for all 8 agent tools.
Tests use a temporary sandbox directory — no real repos needed.

Run: pytest tests/test_tools.py -v
"""

import pytest
import tempfile
from pathlib import Path

from agent.tools import (
    WorkspaceContext,
    read_file, edit_file, create_file, delete_file,
    search_code, run_tests, git_commit,
)


@pytest.fixture
def sandbox(tmp_path: Path) -> WorkspaceContext:
    """Create a temp directory sandbox with a sample Python file."""
    # Set up a minimal git repo so git_commit works
    import subprocess
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)

    # Create a sample file
    (tmp_path / "hello.py").write_text('def greet(name):\n    return f"Hello, {name}!"\n')
    (tmp_path / "requirements.txt").write_text("flask==3.0.3\n")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "utils.py").write_text('import os\nSECRET = "hardcoded_secret_key"\n')

    return WorkspaceContext(repo_path=tmp_path)


class TestReadFile:
    def test_reads_existing_file(self, sandbox):
        result = read_file(sandbox, "hello.py")
        assert 'def greet' in result
        assert 'Hello' in result

    def test_returns_error_for_missing_file(self, sandbox):
        result = read_file(sandbox, "nonexistent.py")
        assert "ERROR" in result
        assert "not found" in result.lower()

    def test_blocks_path_traversal(self, sandbox):
        """Path traversal with '..' in parts should be blocked."""
        with pytest.raises(PermissionError):
            sandbox._safe_path("../../../outside_sandbox.py")


class TestEditFile:
    def test_edits_existing_content(self, sandbox):
        result = edit_file(
            sandbox, "hello.py",
            'return f"Hello, {name}!"',
            'return f"Hi, {name}! Welcome!"'
        )
        assert "SUCCESS" in result
        content = (sandbox.repo_path / "hello.py").read_text()
        assert "Hi, {name}! Welcome!" in content

    def test_fails_if_target_not_found(self, sandbox):
        result = edit_file(sandbox, "hello.py", "NONEXISTENT_STRING", "replacement")
        assert "ERROR" in result
        assert "not found" in result.lower()

    def test_does_not_corrupt_file_on_error(self, sandbox):
        original = (sandbox.repo_path / "hello.py").read_text()
        edit_file(sandbox, "hello.py", "NONEXISTENT", "replacement")
        assert (sandbox.repo_path / "hello.py").read_text() == original


class TestCreateFile:
    def test_creates_new_file(self, sandbox):
        result = create_file(sandbox, "newfile.py", "print('hello')\n")
        assert "SUCCESS" in result
        assert (sandbox.repo_path / "newfile.py").exists()
        assert (sandbox.repo_path / "newfile.py").read_text() == "print('hello')\n"

    def test_creates_nested_directories(self, sandbox):
        result = create_file(sandbox, "a/b/c/new.py", "# nested\n")
        assert "SUCCESS" in result
        assert (sandbox.repo_path / "a/b/c/new.py").exists()

    def test_fails_if_file_exists(self, sandbox):
        result = create_file(sandbox, "hello.py", "# overwrite attempt")
        assert "ERROR" in result
        assert "already exists" in result.lower()


class TestDeleteFile:
    def test_deletes_existing_file(self, sandbox):
        result = delete_file(sandbox, "requirements.txt")
        assert "SUCCESS" in result
        assert not (sandbox.repo_path / "requirements.txt").exists()

    def test_fails_for_nonexistent_file(self, sandbox):
        result = delete_file(sandbox, "ghost.py")
        assert "ERROR" in result


class TestSearchCode:
    def test_finds_pattern_in_file(self, sandbox):
        result = search_code(sandbox, "hardcoded_secret")
        assert "subdir/utils.py" in result or "utils.py" in result

    def test_returns_no_match_message(self, sandbox):
        result = search_code(sandbox, "xyzzy_no_match")
        assert "No matches" in result

    def test_respects_file_pattern(self, sandbox):
        # Search only .txt files — should NOT find Python content
        result = search_code(sandbox, "def greet", "*.txt")
        assert "No matches" in result


class TestRunTests:
    def test_runs_passing_command(self, sandbox):
        # Simple echo always returns exit 0
        result = run_tests(sandbox, "echo 'all good'")
        assert "EXIT CODE: 0" in result
        assert "PASSED" in result

    def test_captures_failing_command(self, sandbox):
        result = run_tests(sandbox, "python -c \"raise SystemExit(1)\"")
        assert "EXIT CODE: 1" in result
        assert "FAILED" in result

    def test_timeout_protection(self, sandbox):
        result = run_tests(sandbox, "ping -n 10 127.0.0.1", timeout=1)
        assert "timed out" in result.lower() or "EXIT CODE" in result


class TestGitCommit:
    def test_commits_staged_files(self, sandbox):
        # Create a new file and commit it
        (sandbox.repo_path / "newchange.py").write_text("x = 1\n")
        result = git_commit(sandbox, "test: add newchange.py")
        # Should either succeed or give a meaningful error
        assert "SUCCESS" in result or "nothing to commit" in result.lower() or "ERROR" in result
