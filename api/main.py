"""
api/main.py
────────────
FastAPI application — the production-ready Cloud Run API.

Endpoints:
  POST /api/v1/refactor        — Queue a repo refactoring/migration job
  GET  /api/v1/status/{job_id} — Poll job status and agent progress
  GET  /api/v1/metrics/{job_id}— Get token usage, cost, and benchmark metrics
  POST /api/v1/scan            — Run OWASP security scanner on a repo
  GET  /health                 — Health check (Cloud Run liveness probe)
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.models import (
    RefactorRequest, RefactorResponse, JobStatusResponse,
    MetricsResponse, ScanRequest, ScanResponse,
    JobStatus, ActionStep, VulnerabilityItem,
)
from agent.planner import create_plan
from agent.executor import run_executor, ExecutionResult
from agent.tools import WorkspaceContext
from agent.memory import AgentMemory
from github_integration.repo_loader import clone_repo, build_repo_context, cleanup_repo
from github_integration.pr_generator import push_branch, open_pull_request
from security.owasp_scanner import scan_repository
from config import config

# ── In-memory job store (swap for Redis in production) ─────────────────────────
_jobs: dict[str, dict] = {}


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 RepoRefactor AI API starting...")
    yield
    # Shutdown — clean up any temp repos still on disk
    print("👋 Shutting down.")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RepoRefactor AI",
    description=(
        "An autonomous enterprise coding agent powered by Gemini Function Calling. "
        "Refactors, migrates, and security-hardens codebases — then opens a GitHub PR."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Background Job Runner ──────────────────────────────────────────────────────

async def _run_agent_job(job_id: str, request: RefactorRequest) -> None:
    """Run the full agent pipeline in the background."""
    _jobs[job_id]["status"] = JobStatus.running
    repo_path: Path | None = None

    try:
        # 1. Clone repository
        repo_path = clone_repo(request.github_url)
        _jobs[job_id]["repo_path"] = str(repo_path)

        # 2. Build full-context string (Gemini's 1M-token advantage)
        repo_context = build_repo_context(repo_path)

        # 3. Planner Agent — decompose task into steps
        plan = create_plan(repo_context, request.task, request.mode.value)
        _jobs[job_id]["plan"] = plan

        # 4. Executor Agent — agentic tool-calling loop
        workspace = WorkspaceContext(repo_path=repo_path)
        memory = AgentMemory()

        result: ExecutionResult = await asyncio.to_thread(
            run_executor,
            plan,
            repo_context,
            workspace,
            memory,
            request.task,
        )

        _jobs[job_id]["result"] = result
        _jobs[job_id]["progress"] = workspace.action_log

        # 5. Open GitHub PR if agent succeeded and tests passed
        pr_url = ""
        if result.success and result.files_changed:
            branch_name = f"agent/{job_id[:8]}"
            pushed = push_branch(repo_path, branch_name, request.github_url)
            if pushed:
                pr_url = open_pull_request(
                    github_url=request.github_url,
                    branch_name=branch_name,
                    task=request.task,
                    files_changed=result.files_changed,
                    action_log=workspace.action_log,
                )

        _jobs[job_id]["pr_url"] = pr_url
        _jobs[job_id]["status"] = JobStatus.complete if result.success else JobStatus.failed

    except Exception as e:
        _jobs[job_id]["status"] = JobStatus.failed
        _jobs[job_id]["error"] = str(e)
    finally:
        if repo_path:
            cleanup_repo(repo_path)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Cloud Run liveness probe."""
    return {"status": "ok", "service": "repo-refactor-ai"}


@app.post("/api/v1/refactor", response_model=RefactorResponse, status_code=202)
async def refactor(request: RefactorRequest, background_tasks: BackgroundTasks):
    """
    Queue an autonomous refactoring / migration job.
    Returns a job_id to poll for status.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.queued,
        "request": request,
        "progress": [],
        "pr_url": "",
        "error": "",
        "result": None,
    }
    background_tasks.add_task(_run_agent_job, job_id, request)
    return RefactorResponse(job_id=job_id, status=JobStatus.queued, message="Job queued.")


@app.get("/api/v1/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    """Poll the live status and step-by-step progress of an agent job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    result: ExecutionResult | None = job.get("result")
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=[ActionStep(**s) for s in job.get("progress", [])],
        pr_url=job.get("pr_url", ""),
        summary=result.summary if result else "",
        error=job.get("error", result.error if result else ""),
    )


@app.get("/api/v1/metrics/{job_id}", response_model=MetricsResponse)
async def get_metrics(job_id: str):
    """Retrieve token usage, cost, iteration count, and benchmark metrics."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    result: ExecutionResult | None = job.get("result")
    if not result:
        return MetricsResponse(job_id=job_id)

    # Gemini 2.0 Flash pricing: ~$0.075 per 1M input tokens (as of 2025)
    cost = (result.tokens_used / 1_000_000) * 0.075

    return MetricsResponse(
        job_id=job_id,
        tokens_used=result.tokens_used,
        estimated_cost_usd=round(cost, 6),
        iterations=result.iterations,
        self_corrections=result.self_corrections,
        files_changed=result.files_changed,
        test_pass_rate=1.0 if result.success else 0.0,
        duration_seconds=round(result.duration_seconds, 2),
    )


@app.post("/api/v1/scan", response_model=ScanResponse)
async def security_scan(request: ScanRequest):
    """
    Run the OWASP vulnerability scanner on a repository.
    Returns categorised findings with CWE IDs and fix hints.
    """
    repo_path: Path | None = None
    try:
        repo_path = clone_repo(request.github_url)
        vulns = scan_repository(repo_path)

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for v in vulns:
            severity_counts[v.severity] = severity_counts.get(v.severity, 0) + 1

        return ScanResponse(
            github_url=request.github_url,
            total_findings=len(vulns),
            critical=severity_counts["CRITICAL"],
            high=severity_counts["HIGH"],
            medium=severity_counts["MEDIUM"],
            low=severity_counts["LOW"],
            vulnerabilities=[VulnerabilityItem(**v.__dict__) for v in vulns],
        )
    finally:
        if repo_path:
            cleanup_repo(repo_path)
