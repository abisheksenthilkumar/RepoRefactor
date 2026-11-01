"""
github_integration/repo_loader.py
───────────────────────────────────
Clone a GitHub repository and build the full-context string
that is fed to Gemini's 1M-token context window.

Key design choice: we do NOT chunk files or use vector search.
Instead we concatenate ALL source files into a single prompt.
This is Gemini's unfair advantage — and a key talking point in
FDE interviews.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from config import config
from rich.console import Console

console = Console()

# File extensions to include in the context string
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb",
    ".rs", ".cpp", ".c", ".h", ".cs", ".php", ".swift", ".kt",
    ".html", ".css", ".scss", ".sql", ".sh", ".yaml", ".yml",
    ".json", ".toml", ".cfg", ".ini", ".md", ".txt", ".env.example",
    ".dockerfile", "Dockerfile", "Makefile", "requirements.txt",
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
}

# Directories to skip entirely
SKIP_DIRS = {
    ".git", ".github", "node_modules", "__pycache__", ".pytest_cache",
    "venv", ".venv", "env", "dist", "build", ".eggs", "*.egg-info",
    ".tox", "coverage", ".coverage", "htmlcov", ".idea", ".vscode",
}


def clone_repo(github_url: str, target_dir: Path | None = None) -> Path:
    """
    Clone a GitHub repository into a temp directory (or target_dir).
    Returns the path to the cloned repo root.
    """
    if target_dir is None:
        target_dir = Path(tempfile.mkdtemp(prefix="rra_repo_"))

    console.log(f"[cyan]Cloning {github_url} → {target_dir}[/cyan]")

    # Inject token for private repos if available
    if config.GITHUB_TOKEN and "github.com" in github_url:
        # Transform: https://github.com/... → https://TOKEN@github.com/...
        auth_url = github_url.replace(
            "https://github.com",
            f"https://{config.GITHUB_TOKEN}@github.com"
        )
    else:
        auth_url = github_url

    result = subprocess.run(
        ["git", "clone", "--depth=1", auth_url, str(target_dir)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"git clone failed:\n{result.stderr}"
        )

    console.log(f"[green]✅ Cloned successfully.[/green]")
    return target_dir


def build_file_tree(repo_path: Path) -> str:
    """Build a visual tree string of the repository structure."""
    lines = [f"📁 {repo_path.name}/"]
    for entry in sorted(repo_path.rglob("*")):
        if any(skip in entry.parts for skip in SKIP_DIRS):
            continue
        rel = entry.relative_to(repo_path)
        depth = len(rel.parts) - 1
        indent = "  " * depth
        prefix = "📄 " if entry.is_file() else "📁 "
        lines.append(f"{indent}{prefix}{entry.name}")
    return "\n".join(lines[:200])  # cap at 200 lines


def _should_include(path: Path) -> bool:
    """Return True if this file should be included in the context string."""
    if any(skip in path.parts for skip in SKIP_DIRS):
        return False
    # Include by extension or exact filename match
    return (
        path.suffix in SOURCE_EXTENSIONS
        or path.name in SOURCE_EXTENSIONS
    )


def build_repo_context(repo_path: Path) -> str:
    """
    Walk the entire repository and concatenate all source files into
    a single structured string for Gemini's context window.

    This is the core Gemini advantage: NO chunking, NO retrieval loss,
    NO vector approximation — the agent sees the ENTIRE codebase at once.
    """
    parts: list[str] = []
    parts.append("=" * 60)
    parts.append("REPOSITORY CONTEXT — FULL SOURCE CODE")
    parts.append("=" * 60)
    parts.append("")
    parts.append("## File Tree")
    parts.append(build_file_tree(repo_path))
    parts.append("")
    parts.append("## File Contents")
    parts.append("")

    total_chars = 0
    file_count = 0
    skipped = 0

    for filepath in sorted(repo_path.rglob("*")):
        if not filepath.is_file():
            continue
        if not _should_include(filepath):
            skipped += 1
            continue
        if file_count >= config.MAX_REPO_FILES:
            parts.append(f"\n[... {skipped} more files omitted (MAX_REPO_FILES reached) ...]")
            break

        rel = filepath.relative_to(repo_path)
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            content = f"[Could not read file: {e}]"

        section = f"\n--- FILE: {rel} ---\n{content}\n"
        total_chars += len(section)

        if total_chars > config.MAX_CONTEXT_CHARS:
            parts.append(
                f"\n[Context budget exhausted at {total_chars:,} chars — "
                f"{file_count} files included, remaining files omitted.]"
            )
            break

        parts.append(section)
        file_count += 1

    console.log(
        f"[green]Repo context built: {file_count} files, "
        f"{total_chars:,} chars (~{total_chars // 4:,} tokens)[/green]"
    )

    return "\n".join(parts)


def cleanup_repo(repo_path: Path) -> None:
    """Remove the cloned repo directory from disk."""
    if repo_path.exists():
        shutil.rmtree(repo_path, ignore_errors=True)
        console.log(f"[dim]Cleaned up {repo_path}[/dim]")
