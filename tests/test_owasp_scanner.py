"""
tests/test_owasp_scanner.py
────────────────────────────
Unit tests for the OWASP pattern-based vulnerability scanner.

Run: pytest tests/test_owasp_scanner.py -v
"""

import pytest
import tempfile
from pathlib import Path

from security.owasp_scanner import scan_repository, scan_file_patterns, Vulnerability


@pytest.fixture
def vuln_repo(tmp_path: Path) -> Path:
    """Create a temp directory with known vulnerable Python code."""

    # SQL Injection
    (tmp_path / "users.py").write_text(
        'def get_user(username):\n'
        '    query = f"SELECT * FROM users WHERE username = \'{username}\'"\n'
        '    cursor.execute(query)\n'
    )

    # Hardcoded secret
    (tmp_path / "config.py").write_text(
        'api_key = "sk-abc123secretkey9999"\n'
        'password = "mysecretpassword"\n'
    )

    # Debug mode
    (tmp_path / "app.py").write_text(
        'from flask import Flask\n'
        'app = Flask(__name__)\n'
        'app.run(debug=True)\n'
    )

    # Clean file — should produce no findings
    (tmp_path / "clean.py").write_text(
        'def add(a: int, b: int) -> int:\n'
        '    return a + b\n'
    )

    return tmp_path


class TestPatternScanner:
    def test_detects_sql_injection(self, vuln_repo):
        vulns = scan_repository(vuln_repo)
        cwe_ids = {v.cwe_id for v in vulns}
        assert "CWE-89" in cwe_ids, "Should detect SQL injection (CWE-89)"

    def test_detects_hardcoded_secret(self, vuln_repo):
        vulns = scan_repository(vuln_repo)
        cwe_ids = {v.cwe_id for v in vulns}
        assert "CWE-798" in cwe_ids, "Should detect hardcoded credentials (CWE-798)"

    def test_detects_debug_mode(self, vuln_repo):
        vulns = scan_repository(vuln_repo)
        cwe_ids = {v.cwe_id for v in vulns}
        assert "CWE-16" in cwe_ids, "Should detect debug=True (CWE-16)"

    def test_no_false_positives_on_clean_file(self, vuln_repo):
        clean_file = vuln_repo / "clean.py"
        vulns = scan_file_patterns(clean_file, vuln_repo)
        assert len(vulns) == 0, "Clean file should produce zero findings"

    def test_severity_ordering(self, vuln_repo):
        vulns = scan_repository(vuln_repo)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        for i in range(len(vulns) - 1):
            assert severity_order[vulns[i].severity] <= severity_order[vulns[i + 1].severity], \
                "Vulnerabilities should be sorted by severity (CRITICAL first)"

    def test_file_path_is_relative(self, vuln_repo):
        vulns = scan_repository(vuln_repo)
        for v in vulns:
            assert not Path(v.file_path).is_absolute(), \
                f"File path should be relative, got: {v.file_path}"

    def test_vulnerability_has_all_fields(self, vuln_repo):
        vulns = scan_repository(vuln_repo)
        assert len(vulns) > 0
        v = vulns[0]
        assert v.cwe_id
        assert v.owasp_category
        assert v.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert v.file_path
        assert v.line_number > 0
        assert v.description
        assert v.fix_hint
