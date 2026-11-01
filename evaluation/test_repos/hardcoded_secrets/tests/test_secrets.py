"""
Tests for hardcoded_secrets benchmark repo.
Verifies that NO secrets appear in source code after the agent fixes it.
"""
import ast
import os
import glob


KNOWN_SECRET_PATTERNS = [
    "SuperSecret123",
    "AKIAIOSFODNN7EXAMPLEFAKE",
    "wJalrXUtnFEMI",
    "sk_live_REPLACE_ME",
    "SG.xxxxxxxxxxxx",
    "admin123",
    "my-super-secret-jwt-token",
]


def get_python_files():
    base = os.path.dirname(os.path.dirname(__file__))
    return [f for f in glob.glob(os.path.join(base, "*.py")) if "__pycache__" not in f]


def test_no_hardcoded_secrets_in_source():
    """No raw secret strings should appear in source .py files."""
    py_files = get_python_files()
    assert py_files, "No Python files found"
    violations = []
    for filepath in py_files:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        for secret in KNOWN_SECRET_PATTERNS:
            if secret in content:
                violations.append(f"{filepath}: contains '{secret[:15]}...'")
    assert not violations, f"Hardcoded secrets found:\n" + "\n".join(violations)


def test_env_example_exists():
    """A .env.example file should be created listing all required variables."""
    base = os.path.dirname(os.path.dirname(__file__))
    env_example = os.path.join(base, ".env.example")
    assert os.path.exists(env_example), ".env.example not found — agent must create it"
    with open(env_example) as f:
        content = f.read()
    required_keys = ["DATABASE_URL", "AWS_ACCESS_KEY", "STRIPE_API_KEY"]
    for key in required_keys:
        assert key in content, f"{key} missing from .env.example"


def test_app_uses_os_getenv():
    """app.py should use os.getenv() or os.environ for secrets."""
    base = os.path.dirname(os.path.dirname(__file__))
    app_file = os.path.join(base, "app.py")
    with open(app_file, encoding="utf-8") as f:
        content = f.read()
    assert "os.getenv" in content or "os.environ" in content, \
        "app.py must use os.getenv() to load secrets"


def test_python_files_parse_cleanly():
    """All .py files must be valid Python (no syntax errors from refactoring)."""
    for filepath in get_python_files():
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            raise AssertionError(f"Syntax error in {filepath}: {e}")
