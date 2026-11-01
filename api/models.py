"""
api/models.py
─────────────
Pydantic request/response schemas for the FastAPI endpoints.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class AgentMode(str, Enum):
    migrate = "migrate"
    security = "security"
    general = "general"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


# ── Request Models ─────────────────────────────────────────────────────────────

class RefactorRequest(BaseModel):
    github_url: str = Field(..., description="HTTPS URL of the GitHub repository.")
    task: str = Field(
        ...,
        description=(
            "Natural language description of what the agent should do. "
            "E.g. 'Migrate this Flask app to FastAPI and add a Dockerfile.'"
        ),
        min_length=10,
        max_length=1000,
    )
    mode: AgentMode = Field(
        AgentMode.general,
        description="Agent operating mode: migrate | security | general"
    )


class ScanRequest(BaseModel):
    github_url: str = Field(..., description="HTTPS URL of the GitHub repository to scan.")


# ── Response Models ────────────────────────────────────────────────────────────

class ActionStep(BaseModel):
    action: str
    detail: str
    result: str = ""


class RefactorResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str = ""


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: list[ActionStep] = []
    pr_url: str = ""
    summary: str = ""
    error: str = ""


class MetricsResponse(BaseModel):
    job_id: str
    tokens_used: int = 0
    estimated_cost_usd: float = 0.0
    iterations: int = 0
    self_corrections: int = 0
    files_changed: list[str] = []
    test_pass_rate: float = 0.0
    duration_seconds: float = 0.0


class VulnerabilityItem(BaseModel):
    cwe_id: str
    owasp_category: str
    severity: str
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    fix_hint: str


class ScanResponse(BaseModel):
    github_url: str
    total_findings: int
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    vulnerabilities: list[VulnerabilityItem] = []
