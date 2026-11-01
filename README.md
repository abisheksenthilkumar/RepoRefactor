# 🤖 RepoRefactor AI

**An autonomous enterprise coding agent powered by Gemini 2.0 Flash Function Calling.**

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
| **OWASP Security Scanner** | Detects SQL Injection (CWE-89), hardcoded secrets (CWE-798), command injection (CWE-78), and more |
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
   │   Planner Agent      │  ← Gemini 2.0 Flash
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
                                    (if tests fail)
              │
              ▼
   ┌──────────────────────┐
   │  GitHub PR Generator │  ← Gemini writes PR body
   └──────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/repo-refactor-ai
cd repo-refactor-ai
python -m venv .venv
.venv\Scripts\activate      # Windows
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
# → Docs: http://localhost:8000/docs
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

Returns OWASP findings with CWE IDs, severity, and fix recommendations.

---

## 📊 Benchmark Results

| Test Case | Result | Iterations | Self-Corrections | Tokens |
|:----------|:-------|:----------:|:----------------:|-------:|
| Flask → FastAPI Migration | ✅ PASS | 14 | 2 | 48,211 |
| SQL Injection Fix | ✅ PASS | 8 | 1 | 31,500 |
| Hardcoded Secrets Removal | ✅ PASS | 6 | 0 | 22,180 |
| Add Error Handling + Logging | ✅ PASS | 11 | 2 | 39,600 |
| Python 2 → 3 Modernization | ❌ FAIL | 20 | 5 | 71,400 |

**Pass Rate: 4/5 (80%) across the benchmark suite.**

---

## 🧪 Run Tests

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## ☁️ Deploy to Google Cloud Run (Free)

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
| LLM | Gemini 2.0 Flash (Google AI Studio — FREE) |
| Agent Framework | Native Gemini Function Calling (no LangChain) |
| API | FastAPI + Uvicorn |
| Containerization | Docker |
| Deployment | Google Cloud Run |
| Secrets | Google Secret Manager |
| Version Control | GitHub API (PyGithub) |
| Dashboard | Streamlit + Plotly |
| Testing | pytest + pytest-cov |
| Linting | ruff |

---

## 📁 Project Structure

```
repo-refactor-ai/
├── agent/
│   ├── planner.py          # Gemini call: task → step plan
│   ├── executor.py         # Agentic tool-calling loop
│   ├── tools.py            # 8 tool definitions + implementations
│   ├── self_corrector.py   # Test failure → fix prompt
│   └── memory.py           # Session memory layer
├── github_integration/
│   ├── repo_loader.py      # Clone + build 1M-token context
│   └── pr_generator.py     # Create branch + open GitHub PR
├── security/
│   └── owasp_scanner.py    # OWASP Top 10 pattern + LLM scanner
├── evaluation/
│   └── benchmark.py        # 5-repo benchmark suite
├── api/
│   ├── main.py             # FastAPI endpoints
│   └── models.py           # Pydantic schemas
├── dashboard/
│   └── app.py              # Streamlit analytics + replay
├── demo_repo/              # Synthetic legacy codebase for demos
├── tests/                  # Unit tests for tools + scanner
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

*Built as a portfolio project showcasing Google FDE competencies:
Gemini Function Calling, agentic system design, enterprise security,
and Google Cloud deployment.*
