"""
agent/planner.py
────────────────
Planner Agent — the first Gemini call in the dual-agent architecture.

Responsibility:
  Given a repo context string and a user task, decompose the task into
  an ordered, concrete execution plan that the Executor can follow step
  by step.  Output is plain text (not tool calls).
"""

from __future__ import annotations

import time

from google import genai
from google.genai import types

from config import config

# Configure Gemini client
_client = genai.Client(api_key=config.GEMINI_API_KEY)


PLANNER_SYSTEM_PROMPT = """You are the Planning Agent in an autonomous enterprise coding system.

Your job is to read a repository's full source code and produce a CLEAR, ORDERED,
STEP-BY-STEP execution plan for the Executor Agent to follow using its tools.

## Available Executor Tools
1. read_file(path)         — Read a file's content
2. edit_file(path, target, replacement) — Replace exact text in a file
3. create_file(path, content) — Create a new file
4. delete_file(path)      — Delete a file
5. run_tests(command)     — Run pytest / npm test and get output
6. run_linter(path)       — Run ruff linter
7. search_code(query, file_pattern) — Grep across the repo
8. git_commit(message, branch_name) — Stage + commit all changes

## Planning Rules
- Be SPECIFIC: name exact files, exact function signatures, exact import statements.
- Order steps so dependencies come first (e.g., create requirements.txt before modifying imports).
- Always include a "run_tests" step near the end to verify changes work.
- Always end with a "git_commit" step.
- If the task involves security issues, add explicit steps to ADD a regression test
  for each vulnerability BEFORE patching it.
- Keep each step to ONE logical action — don't bundle multiple edits into one step.
- Be concise: use numbered bullet points, not long paragraphs.

## Output Format
Return ONLY the numbered plan. No preamble, no explanation.
Example:
1. read_file("app.py") — understand current Flask route structure
2. search_code("from flask import", "*.py") — find all Flask imports
3. edit_file("requirements.txt", "flask", "fastapi\nuvicorn[standard]") — update deps
...
N. run_tests("pytest tests/ -v") — verify all tests pass
N+1. git_commit("feat: migrate Flask app to FastAPI", "agent/fastapi-migration")
"""


def create_plan(repo_context: str, task: str, mode: str = "general") -> str:
    """
    Call the Planner Agent and return the execution plan as a string.

    Args:
        repo_context:  The full repo source code as a single context string.
        task:          The user's natural-language task description.
        mode:          "migrate" | "security" | "general"

    Returns:
        A numbered step-by-step plan as plain text.
    """
    mode_hints = {
        "migrate": (
            "MIGRATION MODE: Focus on converting the stack (e.g., Flask → FastAPI, "
            "Python 2 → 3, SQLite → PostgreSQL). Ensure Dockerfile and CI config are updated."
        ),
        "security": (
            "SECURITY MODE: First SCAN for OWASP issues (SQL injection, hardcoded secrets, "
            "unvalidated input, insecure deserialization). For each vulnerability: "
            "(1) write a failing regression test, (2) patch the code, (3) verify test passes."
        ),
        "general": (
            "GENERAL MODE: Analyse the codebase holistically. Apply the most impactful "
            "improvements: modernise patterns, add error handling, improve logging, "
            "fix obvious bugs, and add missing tests."
        ),
    }

    prompt = f"""
{mode_hints.get(mode, mode_hints['general'])}

## User Task
{task}

## Repository Source Code
{repo_context}

## Your Job
Produce the step-by-step execution plan now.
"""

    models_to_try = [config.GEMINI_MODEL] + [
        m for m in getattr(config, "FALLBACK_MODELS", []) if m != config.GEMINI_MODEL
    ]
    last_err = None

    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = _client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=PLANNER_SYSTEM_PROMPT,
                        temperature=0.2,
                        max_output_tokens=2048,
                    ),
                )
                return response.text.strip()
            except Exception as e:
                last_err = e
                err = str(e)
                if "RESOURCE_EXHAUSTED" in err or "429" in err:
                    print(f"[Planner] Quota exhausted on {model_name}, switching to next model...")
                    break
                elif "503" in err or "UNAVAILABLE" in err:
                    time.sleep(10)
                else:
                    break

    if last_err:
        raise last_err
    return ""
