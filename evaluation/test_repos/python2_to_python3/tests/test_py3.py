"""
Tests for python2_to_python3 benchmark repo.
Verifies all Python 2 anti-patterns have been removed and type hints added.
"""
import ast
import os
import subprocess
import sys


def get_source():
    base = os.path.dirname(os.path.dirname(__file__))
    app_file = os.path.join(base, "app.py")
    with open(app_file, encoding="utf-8") as f:
        return f.read(), app_file


def test_no_percent_string_formatting():
    """No % string formatting for user-visible strings — use f-strings."""
    source, _ = get_source()
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Mod)
                and isinstance(node.left, ast.Constant)
                and isinstance(node.left.value, str)):
            violations.append(f"Line {node.lineno}: % formatting found")
    assert not violations, "Old-style % string formatting found:\n" + "\n".join(violations)


def test_no_urllib2():
    """No urllib2 imports — Python 2 only."""
    source, _ = get_source()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "urllib2", "import urllib2 found — replace with urllib.request"
        if isinstance(node, ast.ImportFrom):
            assert node.module != "urllib2", "from urllib2 found — replace with urllib.request"


def test_no_has_key():
    """No .has_key() attribute calls — use `key in dict`."""
    source, _ = get_source()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "has_key":
            raise AssertionError(f"Line {node.lineno}: .has_key() found — replace with in operator")


def test_no_unicode_builtin():
    """No unicode() calls — use str() in Python 3."""
    source, _ = get_source()
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "unicode"):
            violations.append(f"Line {node.lineno}: unicode() call")
    assert not violations, "unicode() calls found: " + str(violations)


def test_no_xrange():
    """No xrange() calls — use range()."""
    source, _ = get_source()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "xrange":
            raise AssertionError(f"Line {node.lineno}: xrange() found — replace with range()")


def test_no_iteritems():
    """No .iteritems() calls — use .items()."""
    source, _ = get_source()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "iteritems":
            raise AssertionError(f"Line {node.lineno}: .iteritems() found — replace with .items()")


def test_functions_have_type_hints():
    """All top-level functions must have return type annotations."""
    source, _ = get_source()
    tree = ast.parse(source)
    missing = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.returns is None and not node.name.startswith("_"):
                missing.append(f"Line {node.lineno}: {node.name}() missing return type hint")
    assert not missing, "Functions missing type hints:\n" + "\n".join(missing)


def test_file_compiles_cleanly():
    """app.py must compile without errors in Python 3."""
    _, app_file = get_source()
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", app_file],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Compile error:\n{result.stderr}"
