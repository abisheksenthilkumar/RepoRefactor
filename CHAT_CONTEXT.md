# 🧠 RepoRefactor AI — Chat & Project State Transfer

> **Transfer Context**: This file preserves the complete memory, architecture, decisions, and progress from the previous chat session so any new chat in `RepoRefactor` can pick up immediately without losing context.

---

## 1. Project Background & Objective
* **Goal**: Build a production-grade, Google FDE (Forward Deployed Engineer)-grade autonomous coding agent project for the user's resume.
* **Why it's unique**:
  1. Uses **native Gemini 2.0 Flash Function Calling** via the new `google-genai` SDK (NO LangChain abstraction).
  2. Implements a **self-healing test-driven agent loop** (reads `pytest` errors, self-corrects up to 5 iterations).
  3. Leverages **Gemini's 1M+ token context** for repo-level understanding without vector search loss.
  4. Features an **OWASP Top 10 scanner** (7 CWE rules + LLM-assisted deep scan).
  5. Includes a **Streamlit visualizer** with step-by-step agent replay, token cost analytics, and benchmark reports.

---

## 2. Workspace Location
* **Active Project Directory**: `C:\Users\abish\Documents\Antigravity\RepoRefactor`
* **Python Environment**: Python 3.12+ (dependencies installed: `google-genai`, `fastapi`, `uvicorn`, `streamlit`, `plotly`, `gitpython`, `pytest`)

---

## 3. What Has Been Built (30 Files — Complete & Verified)

* **Agent Core (`agent/`)**:
  - `planner.py`: Decomposes user tasks into structured, ordered step plans.
  - `executor.py`: Drives the Gemini tool-calling loop and dispatches functions.
  - `tools.py`: 8 tools (`read_file`, `edit_file`, `create_file`, `delete_file`, `run_tests`, `run_linter`, `search_code`, `git_commit`) with path traversal security guards.
  - `self_corrector.py`: Generates targeted fix prompts on test failure.
  - `memory.py`: In-session memory of file edits to prevent contradictory changes.
* **Security (`security/`)**:
  - `owasp_scanner.py`: Regex pattern scanner for CWE-89 (SQLi), CWE-798 (Secrets), CWE-78 (Command Injection), CWE-16 (Debug), CWE-327 (Weak Hashes), CWE-95 (`eval`), CWE-918 (SSRF).
* **GitHub Integration (`github_integration/`)**:
  - `repo_loader.py`: Clones repos, builds file trees, and formats 1M-token context strings.
  - `pr_generator.py`: Commits branch, writes structured PR summaries, and creates GitHub Draft PRs.
* **API & Dashboard (`api/`, `dashboard/`)**:
  - `api/main.py`: FastAPI service with `/api/v1/refactor`, `/status`, `/metrics`, and `/scan`.
  - `dashboard/app.py`: Streamlit app with Task Launcher, Replay Visualizer, Metrics, and Security tabs.
* **Evaluation & Demo (`evaluation/`, `demo_repo/`)**:
  - `demo_repo/app.py`: Synthetic legacy Flask app with 5 intentional bugs & 3 OWASP vulnerabilities.
  - `evaluation/benchmark.py`: 5-repo evaluation harness to measure automated pass rates.
* **Tests (`tests/`)**:
  - `test_tools.py` & `test_owasp_scanner.py`: **25 tests — 100% PASSING**.

---

## 4. Current Test Status
```bash
python -m pytest tests/ -q --no-header
# Output: 25 passed in 12.29s (100% GREEN)
```

---

## 5. Immediate Next Steps for the New Chat
1. Help user configure `.env` with their free Google AI Studio key (`GEMINI_API_KEY`) and GitHub token (`GITHUB_TOKEN`).
2. Run the local demo (`uvicorn api.main:app --reload` and `streamlit run dashboard/app.py`).
3. Execute the benchmark test against `demo_repo/` to record the real pass rate.
4. Push to the user's GitHub repository.
