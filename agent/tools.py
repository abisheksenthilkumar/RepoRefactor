"""
agent/tools.py
──────────────
Defines all 8 tool schemas (for Gemini Function Calling) and their
Python implementations.  Every tool receives a WorkspaceContext that
scopes file-system operations to the cloned repository directory so the
agent cannot accidentally touch anything outside the sandbox.
"""

from __future__ import annotations

import os
import subprocess
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


# ── Workspace Context ──────────────────────────────────────────────────────────

@dataclass
class WorkspaceContext:
    """All agent tool calls are scoped to this directory."""
    repo_path: Path
    # Tracks every action taken: used by the replay visualizer
    action_log: list[dict] = field(default_factory=list)

    def log(self, action: str, detail: str, result: str = "") -> None:
        self.action_log.append({
            "action": action,
            "detail": detail,
            "result": result[:300] if result else ""
        })
        console.log(f"[bold cyan][TOOL][/bold cyan] {action} → {detail}")

    def _safe_path(self, relative_path: str) -> Path:
        """Resolve path and ensure it stays within the repo sandbox."""
        # Normalize separators and reject obvious traversal attempts
        normalized = relative_path.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise PermissionError(
                f"Path traversal attempt blocked: '{relative_path}' contains '..'."
            )
        resolved = (self.repo_path / relative_path).resolve()
        if not str(resolved).startswith(str(self.repo_path.resolve())):
            raise PermissionError(
                f"Path traversal attempt blocked: '{relative_path}' "
                f"resolves outside the repo sandbox."
            )
        return resolved


# ── Tool Implementations ───────────────────────────────────────────────────────

def read_file(ctx: WorkspaceContext, path: str) -> str:
    """Read the full content of a file in the repository."""
    try:
        fp = ctx._safe_path(path)
        content = fp.read_text(encoding="utf-8", errors="replace")
        ctx.log("read_file", path, content[:100])
        return content
    except FileNotFoundError:
        return f"ERROR: File not found — '{path}'"
    except Exception as e:
        return f"ERROR reading '{path}': {e}"


def edit_file(ctx: WorkspaceContext, path: str, target: str, replacement: str) -> str:
    """Replace an exact block of text in a file with new content."""
    try:
        fp = ctx._safe_path(path)
        original = fp.read_text(encoding="utf-8", errors="replace")
        if target not in original:
            return (
                f"ERROR: Target string not found in '{path}'.\n"
                f"Make sure the target matches the file content exactly, "
                f"including whitespace and indentation."
            )
        updated = original.replace(target, replacement, 1)
        fp.write_text(updated, encoding="utf-8")
        ctx.log("edit_file", path, f"Replaced {len(target)} chars → {len(replacement)} chars")
        return f"SUCCESS: '{path}' updated."
    except Exception as e:
        return f"ERROR editing '{path}': {e}"


def create_file(ctx: WorkspaceContext, path: str, content: str) -> str:
    """Create a new file (including any intermediate directories)."""
    try:
        fp = ctx._safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        if fp.exists():
            return f"ERROR: '{path}' already exists. Use edit_file to modify it."
        fp.write_text(content, encoding="utf-8")
        ctx.log("create_file", path)
        return f"SUCCESS: Created '{path}'."
    except Exception as e:
        return f"ERROR creating '{path}': {e}"


def delete_file(ctx: WorkspaceContext, path: str) -> str:
    """Delete a file from the repository."""
    try:
        fp = ctx._safe_path(path)
        if not fp.exists():
            return f"ERROR: '{path}' does not exist."
        fp.unlink()
        ctx.log("delete_file", path)
        return f"SUCCESS: Deleted '{path}'."
    except Exception as e:
        return f"ERROR deleting '{path}': {e}"


def run_tests(ctx: WorkspaceContext, command: str, timeout: int = 30) -> str:
    """
    Run a test command inside the repository sandbox and return
    the combined stdout + stderr output.
    """
    try:
        ctx.log("run_tests", command)
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(ctx.repo_path),
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        status = "PASSED ✅" if result.returncode == 0 else "FAILED ❌"
        ctx.log("run_tests", command, f"{status}\n{output[:200]}")
        return f"EXIT CODE: {result.returncode}\nSTATUS: {status}\n\n{output}"
    except subprocess.TimeoutExpired:
        return f"ERROR: Test command timed out after {timeout}s."
    except Exception as e:
        return f"ERROR running tests: {e}"


def run_linter(ctx: WorkspaceContext, path: str = ".") -> str:
    """Run ruff (fast Python linter) on the given path and return the report."""
    try:
        ctx.log("run_linter", path)
        result = subprocess.run(
            f"ruff check {path} --output-format=text",
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(ctx.repo_path),
            timeout=20,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return "LINTER: No issues found ✅"
        return f"LINTER ISSUES:\n{output}"
    except FileNotFoundError:
        # ruff not installed — fall back to a basic message
        return "LINTER: ruff not available. Skipping lint check."
    except Exception as e:
        return f"ERROR running linter: {e}"


def search_code(ctx: WorkspaceContext, query: str, file_pattern: str = "*.py") -> str:
    """
    Search for a string or regex pattern across all files matching
    file_pattern. Returns file paths and matching line numbers.
    """
    try:
        ctx.log("search_code", f"query='{query}' pattern='{file_pattern}'")
        matches = []
        for fp in ctx.repo_path.rglob(file_pattern):
            try:
                lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    if query.lower() in line.lower():
                        rel = fp.relative_to(ctx.repo_path)
                        matches.append(f"{rel}:{i}: {line.strip()}")
            except Exception:
                continue
        if not matches:
            return f"No matches found for '{query}' in '{file_pattern}' files."
        return "\n".join(matches[:50])  # cap at 50 results
    except Exception as e:
        return f"ERROR searching code: {e}"


def git_commit(ctx: WorkspaceContext, message: str, branch_name: str = "") -> str:
    """
    Stage all changes and create a Git commit.
    Optionally creates and checks out a new branch first.
    """
    try:
        if branch_name:
            subprocess.run(
                f"git checkout -b {branch_name}",
                shell=True, cwd=str(ctx.repo_path),
                capture_output=True, timeout=15
            )
            ctx.log("git_commit", f"Created branch: {branch_name}")

        subprocess.run(
            "git add -A",
            shell=True, cwd=str(ctx.repo_path),
            capture_output=True, timeout=15
        )
        result = subprocess.run(
            f'git commit -m "{message}"',
            shell=True, capture_output=True, text=True,
            cwd=str(ctx.repo_path), timeout=15
        )
        output = result.stdout + result.stderr
        ctx.log("git_commit", message, output)
        if result.returncode != 0:
            return f"ERROR: git commit failed.\n{output}"
        return f"SUCCESS: Committed.\n{output}"
    except Exception as e:
        return f"ERROR committing: {e}"


# ── Tool Dispatch ──────────────────────────────────────────────────────────────

TOOL_IMPLEMENTATIONS = {
    "read_file": read_file,
    "edit_file": edit_file,
    "create_file": create_file,
    "delete_file": delete_file,
    "run_tests": run_tests,
    "run_linter": run_linter,
    "search_code": search_code,
    "git_commit": git_commit,
}


def dispatch_tool(ctx: WorkspaceContext, tool_name: str, args: dict[str, Any]) -> str:
    """Route a Gemini function call to the correct Python implementation."""
    fn = TOOL_IMPLEMENTATIONS.get(tool_name)
    if fn is None:
        return f"ERROR: Unknown tool '{tool_name}'."
    return fn(ctx, **args)


# ── Gemini Function Call Schemas ───────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": (
            "Read the full text content of a file in the repository. "
            "Use this before editing to see exactly what is there."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file within the repository root."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "edit_file",
        "description": (
            "Replace an exact, verbatim block of text in a file with new content. "
            "The 'target' must match the file content character-for-character, "
            "including all whitespace and indentation. "
            "Read the file first to ensure accuracy."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path."},
                "target": {
                    "type": "string",
                    "description": "Exact string to find and replace. Must exist in the file."
                },
                "replacement": {
                    "type": "string",
                    "description": "New content that will replace the target string."
                }
            },
            "required": ["path", "target", "replacement"]
        }
    },
    {
        "name": "create_file",
        "description": (
            "Create a brand-new file with the given content. "
            "Fails if the file already exists — use edit_file for existing files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path for the new file."},
                "content": {"type": "string", "description": "Full file content to write."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "delete_file",
        "description": "Permanently delete a file from the repository.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path of the file to delete."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "run_tests",
        "description": (
            "Execute the test suite and return the full output (stdout + stderr). "
            "Use 'pytest tests/' for Python projects or 'npm test' for Node.js. "
            "An exit code of 0 means all tests passed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run, e.g. 'pytest tests/ -v' or 'npm test'."
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "run_linter",
        "description": (
            "Run the ruff linter on the codebase and return style/quality issues. "
            "Provide '.' to lint the whole repo or a specific path like 'src/'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to lint. Defaults to '.' (entire repo).",
                    "default": "."
                }
            },
            "required": []
        }
    },
    {
        "name": "search_code",
        "description": (
            "Search for a text pattern across all matching files in the repo. "
            "Returns file paths and line numbers of matches. "
            "Useful for finding all usages of a function, import, or pattern."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text or pattern to search for (case-insensitive)."
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern for files to search, e.g. '*.py' or '*.js'.",
                    "default": "*.py"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "git_commit",
        "description": (
            "Stage all modified files and create a Git commit with the given message. "
            "Optionally creates a new branch before committing. "
            "Call this only after verifying tests pass."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Conventional commit message, e.g. 'feat: migrate Flask routes to FastAPI'."
                },
                "branch_name": {
                    "type": "string",
                    "description": "If provided, create and check out this branch before committing.",
                    "default": ""
                }
            },
            "required": ["message"]
        }
    }
]
