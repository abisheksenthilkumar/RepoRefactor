# 🤖 RepoRefactor AI

[![CI — Test & Lint](https://github.com/abisheksenthilkumar/RepoRefactor/actions/workflows/ci.yml/badge.svg)](https://github.com/abisheksenthilkumar/RepoRefactor/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Gemini 3.8 Flash](https://img.shields.io/badge/Gemini-3.8%20Flash-4285F4?logo=google&logoColor=white)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**An autonomous enterprise coding agent powered by Gemini 3.8 Flash native Function Calling.**

> Inspects GitHub repositories, plans refactoring tasks, executes multi-file code changes,
> self-corrects via test feedback loops, and opens verified Pull Requests — automatically.

---

## 🎯 What It Does

| Feature | Description |
|:--------|:------------|
| **Planner + Executor Dual-Agent** | Separates reasoning (plan) from execution (tool calls) |
| **8 Tool-Calling Actions** | `read_file`, `edit_file`, `create_file`, `delete_file`, `run_tests`, `run_linter`, `search_code`, `git_commit` |
| **Self-Correcting Test Loop** | Reads `pytest` failures, reflects on the error, re-edits code — up to 5 iterations |
| **1M-Token Context Window** | Entire repo ingested at once — no RAG chunking, no retrieval loss |
| **OWASP Security Scanner** | Detects SQL Injection (CWE-89), hardcoded secrets (CWE-798), command injection (CWE-78), and 4 more |
| **Automated PR Generation** | Commits to a new branch, opens a GitHub Draft PR with AI-written description |
| **Replay Visualizer** | Streamlit dashboard shows every tool call the agent made, step by step |
| **Cost Analytics** | Tracks token usage, estimated API cost, and iteration count per task |

---

## 🏗️ Architecture

```
[GitHub Repo URL + Task Description]
              │
              ▼
   ┌──────────────────────┐
   │   Planner Agent      │  ← Gemini 3.8 Flash
   │   (Task Decomp.)     │    Creates ordered step plan
   └──────────┬───────────┘
              │ plan
              ▼
   ┌──────────────────────┐
   │   Executor Agent     │  ← Gemini Function Calling
   │   (Agentic Loop)     │    Drives 8 tools iteratively
   └──────────┬───────────┘
              │ tool calls
    ┌─────────┼──────────┐
    ▼         ▼          ▼
read_file  edit_file  run_tests ──► Self-Correction Loop
                                    (reads failures, re-edits)
              │
              ▼
   ┌──────────────────────┐
   │  GitHub PR Generator │  ← Gemini writes PR body
   └──────────────────────┘
```

---

## 📊 Benchmark Results

Evaluated against 5 synthetic legacy codebases — each with intentional bugs, vulnerabilities, or outdated patterns:

| Test Case | Result | Iterations | Self-Corrections | Tokens |
|:----------|:------:|:----------:|:----------------:|-------:|
| Flask → FastAPI Migration | ✅ PASS | 14 | 2 | ~48,000 |
| SQL Injection Fix (3 CVEs) | ✅ PASS | 8 | 1 | ~31,500 |
| Hardcoded Secrets Removal | ✅ PASS | 6 | 0 | ~22,000 |
| Error Handling + Logging | ✅ PASS | 11 | 2 | ~39,600 |
| Python 2 → 3 Modernization | ✅ PASS | 9 | 1 | ~28,400 |

**🏆 Pass Rate: 5/5 (100%) — 25 unit tests, 100% green.**

> Run it yourself: `python -m evaluation.benchmark`

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/abisheksenthilkumar/RepoRefactor.git
cd RepoRefactor
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY and GITHUB_TOKEN
```

Get your **FREE** Gemini API key: https://aistudio.google.com/app/apikey

### 3. Run the API

```bash
uvicorn api.main:app --reload
# → http://localhost:8000
# → Swagger Docs: http://localhost:8000/docs
```

### 4. Run the Dashboard

```bash
streamlit run dashboard/app.py
# → http://localhost:8501
```

### 5. Trigger a Task (via API)

```bash
curl -X POST http://localhost:8000/api/v1/refactor \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/YOUR_USERNAME/YOUR_LEGACY_REPO",
    "task": "Migrate this Flask app to FastAPI and add a Dockerfile.",
    "mode": "migrate"
  }'
```

---

## 🔒 Security Scan

```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/YOUR_USERNAME/YOUR_REPO"}'
```

Returns OWASP findings with CWE IDs, severity, line numbers, and fix recommendations.

**OWASP rules implemented:**
- CWE-89: SQL Injection
- CWE-798: Hardcoded Credentials
- CWE-78: OS Command Injection
- CWE-16: Security Misconfiguration (debug mode)
- CWE-327: Weak Cryptographic Hash (MD5/SHA1)
- CWE-95: Improper Code Evaluation (`eval`)
- CWE-918: Server-Side Request Forgery (SSRF)

---

## 🧪 Run Tests

```bash
python -m pytest tests/ -v --cov=. --cov-report=term-missing
# → 25 passed in ~12s (100% GREEN)
```

---

## ☁️ Deploy to Google Cloud Run (Free Tier)

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/repo-refactor-ai

# Deploy (scales to zero = $0/month on free tier)
gcloud run deploy repo-refactor-ai \
  --image gcr.io/YOUR_PROJECT/repo-refactor-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,GITHUB_TOKEN=github-token:latest
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|:------|:-----------|
| **LLM** | Gemini 3.8 Flash (Google AI Studio — FREE tier) |
| **Agent Framework** | Native `google-genai` SDK Function Calling (no LangChain) |
| **API** | FastAPI + Uvicorn |
| **Dashboard** | Streamlit + Plotly |
| **GitHub Integration** | PyGithub + GitPython |
| **Security Scanning** | Custom OWASP 7-rule regex engine + Gemini LLM deep scan |
| **Containerization** | Docker + docker-compose |
| **Deployment** | Google Cloud Run |
| **Testing** | pytest + pytest-cov + pytest-asyncio |
| **Linting** | ruff |

---

## 📁 Project Structure

```
RepoRefactor/
├── agent/
│   ├── planner.py          # Gemini call: task → step plan
│   ├── executor.py         # Agentic tool-calling loop
│   ├── tools.py            # 8 tool definitions + path-traversal guards
│   ├── self_corrector.py   # Test failure → targeted fix prompt
│   └── memory.py           # In-session edit memory
├── github_integration/
│   ├── repo_loader.py      # Clone + build 1M-token context string
│   └── pr_generator.py     # Create branch + open GitHub Draft PR
├── security/
│   └── owasp_scanner.py    # 7-CWE pattern scanner + LLM deep scan
├── evaluation/
│   ├── benchmark.py        # 5-repo benchmark harness
│   └── test_repos/         # 5 synthetic legacy codebases
│       ├── flask_to_fastapi/
│       ├── sql_injection_fix/
│       ├── hardcoded_secrets/
│       ├── add_error_handling/
│       └── python2_to_python3/
├── api/
│   ├── main.py             # FastAPI: /refactor, /status, /metrics, /scan
│   └── models.py           # Pydantic request/response schemas
├── dashboard/
│   └── app.py              # Streamlit: Task Launcher, Replay, Metrics, Security
├── demo_repo/              # Synthetic Flask app with 5 bugs + 3 OWASP vulns
├── tests/                  # 25 unit tests — 100% passing
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

*Built as a portfolio project demonstrating Google FDE competencies:
Gemini Function Calling, agentic system design, enterprise security scanning,
self-healing test loops, and Google Cloud deployment.*
