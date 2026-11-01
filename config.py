"""
config.py — Centralized configuration loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Gemini ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    FALLBACK_MODELS: list[str] = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
    ]

    # ── GitHub ─────────────────────────────────────────────────────────────
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_USERNAME: str = os.getenv("GITHUB_USERNAME", "repo-refactor-ai-bot")

    # ── Agent Behaviour ────────────────────────────────────────────────────
    MAX_SELF_CORRECTION_ITERATIONS: int = int(
        os.getenv("MAX_SELF_CORRECTION_ITERATIONS", "5")
    )
    SANDBOX_TIMEOUT_SECONDS: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "30"))
    MAX_REPO_FILES: int = int(os.getenv("MAX_REPO_FILES", "200"))
    MAX_CONTEXT_CHARS: int = int(os.getenv("MAX_CONTEXT_CHARS", "800000"))

    # ── Google Cloud (optional, for production) ────────────────────────────
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")

    @classmethod
    def validate(cls) -> None:
        """Raise at startup if required credentials are missing."""
        missing = []
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.GITHUB_TOKEN:
            missing.append("GITHUB_TOKEN")
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Copy .env.example → .env and fill in your values."
            )


config = Config()
