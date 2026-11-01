"""
agent/self_corrector.py
────────────────────────
Generates a focused correction prompt when the agent's test run fails.
This prompt is injected into the Gemini conversation to guide the agent
to reflect on the error traceback and produce a targeted fix.
"""

from __future__ import annotations


def build_correction_prompt(test_output: str, files_changed: set[str]) -> str:
    """
    Build a self-correction instruction injected after a failed test run.

    Args:
        test_output:    The full stdout/stderr from run_tests().
        files_changed:  Set of file paths the agent has modified so far.

    Returns:
        A string prompt that steers Gemini to fix the failing tests.
    """
    changed_list = ", ".join(files_changed) if files_changed else "unknown files"

    return f"""
🔄 SELF-CORRECTION REQUIRED

The tests above FAILED. You must fix the issue before proceeding.

## Files You Have Modified So Far
{changed_list}

## Instructions for Self-Correction
1. Read the error traceback carefully — identify the EXACT file and line number causing the failure.
2. Use read_file() to inspect the current state of the relevant file.
3. Identify whether the error is:
   - A syntax error (check indentation, missing colons, mismatched brackets)
   - An import error (wrong module name, missing dependency in requirements.txt)
   - A logic error (wrong variable name, incorrect type, wrong return value)
   - A test expectation mismatch (the test expectation needs updating after a valid refactor)
4. Make the MINIMUM change needed to fix the error using edit_file().
5. Run tests again with run_tests() to verify the fix worked.
6. Do NOT make large unrelated changes during self-correction.

Analyse the error now and apply a precise fix.
"""


def extract_error_summary(test_output: str) -> str:
    """
    Extract just the key error lines from pytest/npm test output
    to include in metrics/logs without overwhelming context.
    """
    lines = test_output.splitlines()
    error_lines = [
        line for line in lines
        if any(kw in line for kw in ["ERROR", "FAILED", "Error:", "assert", "Traceback"])
    ]
    return "\n".join(error_lines[:20]) if error_lines else test_output[:500]
