"""
security/owasp_scanner.py
──────────────────────────
Two-layer OWASP vulnerability scanner:

Layer 1 — Pattern-based (fast, deterministic):
  Regex rules against common OWASP Top-10 patterns.
  Each rule maps to a CWE ID, severity, and fix hint.

Layer 2 — LLM-assisted (Gemini):
  Feeds suspicious code sections to Gemini for deeper analysis
  of logic-level vulnerabilities that regex cannot catch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from google import genai

from config import config

def _get_client():
    """Lazy client init — avoids crashing at import time during tests."""
    return genai.Client(api_key=config.GEMINI_API_KEY)


# ── Vulnerability Data Model ───────────────────────────────────────────────────

@dataclass
class Vulnerability:
    cwe_id: str           # e.g. "CWE-89"
    owasp_category: str   # e.g. "A03:2021 – Injection"
    severity: str         # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    fix_hint: str


# ── Pattern-Based Rules ────────────────────────────────────────────────────────

class OWASPRule(NamedTuple):
    pattern: re.Pattern
    cwe_id: str
    owasp_category: str
    severity: str
    description: str
    fix_hint: str


OWASP_RULES: list[OWASPRule] = [
    # A03: Injection — SQL Injection
    OWASPRule(
        re.compile(
            r'(execute|cursor\.execute|db\.execute|query)\s*\(\s*["\'].*?\%s.*?["\']|'
            r'f["\'].*?SELECT.*?WHERE.*?\{.*?\}',
            re.IGNORECASE | re.DOTALL
        ),
        "CWE-89", "A03:2021 – Injection", "CRITICAL",
        "Potential SQL injection: user input interpolated directly into SQL query.",
        "Use parameterised queries: cursor.execute('SELECT * FROM t WHERE id=%s', (user_id,))"
    ),
    # A02: Cryptographic Failures — Hardcoded Secrets
    OWASPRule(
        re.compile(
            r'(api_key|secret_key|password|token|passwd|access_key)\s*=\s*["\'][^"\']{8,}["\']',
            re.IGNORECASE
        ),
        "CWE-798", "A02:2021 – Cryptographic Failures", "HIGH",
        "Hardcoded credential or secret detected in source code.",
        "Move secrets to environment variables and load with os.getenv() or python-dotenv."
    ),
    # A03: Injection — Command Injection
    OWASPRule(
        re.compile(
            r'(os\.system|subprocess\.call|subprocess\.run|popen)\s*\(.*?\+|'
            r'(os\.system|subprocess\.call)\s*\(f["\']',
            re.IGNORECASE
        ),
        "CWE-78", "A03:2021 – Injection", "CRITICAL",
        "Potential command injection: user-controlled data passed to shell command.",
        "Use subprocess with a list of arguments (never shell=True with user input): "
        "subprocess.run(['cmd', arg], shell=False)"
    ),
    # A01: Broken Access Control — Debug mode in production
    OWASPRule(
        re.compile(r'app\.run\(.*?debug\s*=\s*True', re.IGNORECASE),
        "CWE-16", "A01:2021 – Broken Access Control", "HIGH",
        "Flask app running with debug=True — exposes interactive debugger in production.",
        "Set debug=False in production, or use DEBUG=os.getenv('DEBUG', 'false') == 'true'."
    ),
    # A02: Cryptographic Failures — MD5/SHA1 usage
    OWASPRule(
        re.compile(r'hashlib\.(md5|sha1)\s*\(', re.IGNORECASE),
        "CWE-327", "A02:2021 – Cryptographic Failures", "MEDIUM",
        "Weak cryptographic hash function (MD5/SHA1) used for security-sensitive data.",
        "Use hashlib.sha256() or hashlib.sha3_256() for security-sensitive hashing. "
        "For passwords, use bcrypt or argon2."
    ),
    # A05: Security Misconfiguration — eval() usage
    OWASPRule(
        re.compile(r'\beval\s*\(', re.IGNORECASE),
        "CWE-95", "A05:2021 – Security Misconfiguration", "HIGH",
        "Use of eval() can execute arbitrary code if user input reaches it.",
        "Replace eval() with ast.literal_eval() for data parsing, or redesign the logic."
    ),
    # A10: SSRF — requests with user-supplied URL
    OWASPRule(
        re.compile(
            r'requests\.(get|post|put|delete)\s*\(\s*(request\.|user_|input_)',
            re.IGNORECASE
        ),
        "CWE-918", "A10:2021 – Server-Side Request Forgery", "HIGH",
        "Potential SSRF: outbound HTTP request using user-supplied URL.",
        "Validate and whitelist allowed URL schemes and domains before making requests."
    ),
]


# ── Pattern Scanner ────────────────────────────────────────────────────────────

def scan_file_patterns(filepath: Path, repo_root: Path) -> list[Vulnerability]:
    """Run all regex rules against a single file."""
    vulns: list[Vulnerability] = []
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    full_text = "\n".join(lines)
    rel_path = str(filepath.relative_to(repo_root))

    for rule in OWASP_RULES:
        for match in rule.pattern.finditer(full_text):
            # Find the line number of the match
            line_num = full_text[: match.start()].count("\n") + 1
            snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
            vulns.append(Vulnerability(
                cwe_id=rule.cwe_id,
                owasp_category=rule.owasp_category,
                severity=rule.severity,
                file_path=rel_path,
                line_number=line_num,
                code_snippet=snippet,
                description=rule.description,
                fix_hint=rule.fix_hint,
            ))

    return vulns


def scan_repository(repo_path: Path) -> list[Vulnerability]:
    """
    Run the full pattern-based scanner across all Python files
    in the repository and return a deduplicated list of findings.
    """
    all_vulns: list[Vulnerability] = []
    seen: set[tuple] = set()

    for filepath in sorted(repo_path.rglob("*.py")):
        if any(skip in filepath.parts for skip in [".git", "venv", "__pycache__"]):
            continue
        for v in scan_file_patterns(filepath, repo_path):
            key = (v.cwe_id, v.file_path, v.line_number)
            if key not in seen:
                seen.add(key)
                all_vulns.append(v)

    return sorted(all_vulns, key=lambda v: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[v.severity])


def llm_deep_scan(file_content: str, file_path: str) -> str:
    """
    Feed a suspicious file to Gemini for deeper vulnerability analysis
    beyond what regex can catch (e.g., logic flaws, auth bypass, IDOR).
    """
    response = _get_client().models.generate_content(model=config.GEMINI_MODEL, contents=prompt)
    return response.text.strip()
