"""
evaluation/benchmark.py
────────────────────────
Runs the agent against 5 curated legacy test repositories and
reports a quantitative success rate — the number you put on your resume.

Usage:
    python -m evaluation.benchmark

Output:
    A JSON report + a printed summary table.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.table import Table

from agent.planner import create_plan
from agent.executor import run_executor, ExecutionResult
from agent.tools import WorkspaceContext
from agent.memory import AgentMemory
from github_integration.repo_loader import build_repo_context, clone_repo, cleanup_repo

console = Console()


@dataclass
class BenchmarkCase:
    name: str
    description: str
    task: str
    mode: str           # "migrate" | "security" | "general"
    # A shell command to run inside the repo to verify success
    # Returns 0 on success, non-zero on failure
    verify_command: str


@dataclass
class BenchmarkResult:
    case_name: str
    success: bool
    test_exit_code: int
    iterations: int
    self_corrections: int
    tokens_used: int
    duration_seconds: float
    error: str = ""


# ── 5 Benchmark Cases ──────────────────────────────────────────────────────────
# These are run against repos under evaluation/test_repos/
# We use local paths (not GitHub) for fast, free, offline benchmarking

BENCHMARK_CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        name="flask_to_fastapi",
        description="Migrate Flask+SQLite CRUD app to FastAPI+SQLAlchemy",
        task=(
            "Migrate this Flask application to FastAPI. "
            "Replace sqlite3 with SQLAlchemy (async). "
            "Update requirements.txt. Ensure all tests pass."
        ),
        mode="migrate",
        verify_command="pytest tests/ -v --tb=short -q",
    ),
    BenchmarkCase(
        name="sql_injection_fix",
        description="Fix SQL injection vulnerabilities and add regression tests",
        task=(
            "Identify all SQL injection vulnerabilities in this codebase. "
            "For each vulnerability: first write a failing regression test, "
            "then fix it using parameterised queries. Verify tests pass."
        ),
        mode="security",
        verify_command="pytest tests/ -v -k 'sql' --tb=short -q",
    ),
    BenchmarkCase(
        name="hardcoded_secrets",
        description="Move hardcoded secrets to environment variables",
        task=(
            "Find all hardcoded API keys, passwords, and secrets in the source code. "
            "Move them to a .env file loaded with python-dotenv. "
            "Update all references to use os.getenv(). Add a .env.example file."
        ),
        mode="security",
        verify_command="python -c \"import ast; import os; [ast.parse(open(f).read()) for f in __import__('glob').glob('*.py')]\"",
    ),
    BenchmarkCase(
        name="add_error_handling",
        description="Add comprehensive error handling and structured logging",
        task=(
            "Add try/except blocks to all route handlers and database operations. "
            "Replace all print() statements with Python's logging module. "
            "Return proper HTTP error responses (400, 404, 500) instead of unhandled exceptions."
        ),
        mode="general",
        verify_command="pytest tests/ -v --tb=short -q",
    ),
    BenchmarkCase(
        name="python2_to_python3",
        description="Update Python 2-style code to Python 3.11+",
        task=(
            "Update all Python 2-style patterns to Python 3.11+: "
            "replace print statements with print(), update urllib usage, "
            "add type hints to all function signatures, "
            "replace .has_key() with 'in', replace unicode() with str()."
        ),
        mode="migrate",
        verify_command="python -m py_compile *.py && python -m mypy . --ignore-missing-imports",
    ),
]


def run_benchmark(cases: list[BenchmarkCase] | None = None) -> list[BenchmarkResult]:
    """Run all benchmark cases and return results."""
    if cases is None:
        cases = BENCHMARK_CASES

    results: list[BenchmarkResult] = []

    for case in cases:
        console.rule(f"[bold cyan]📋 Benchmark: {case.name}")
        console.print(f"  Task: {case.task[:80]}...")

        # Each benchmark case has a matching repo under evaluation/test_repos/<name>/
        test_repo_path = Path(__file__).parent / "test_repos" / case.name

        if not test_repo_path.exists():
            console.print(f"[yellow]⚠ Test repo not found: {test_repo_path}. Skipping.[/yellow]")
            results.append(BenchmarkResult(
                case_name=case.name,
                success=False,
                test_exit_code=-1,
                iterations=0,
                self_corrections=0,
                tokens_used=0,
                duration_seconds=0,
                error=f"Test repo not found: {test_repo_path}"
            ))
            continue

        # Copy the test repo to a temp working directory so we don't mutate the original
        import shutil
        work_dir = Path(tempfile.mkdtemp(prefix=f"bench_{case.name}_"))
        shutil.copytree(str(test_repo_path), str(work_dir), dirs_exist_ok=True)

        try:
            repo_context = build_repo_context(work_dir)
            plan = create_plan(repo_context, case.task, case.mode)

            workspace = WorkspaceContext(repo_path=work_dir)
            memory = AgentMemory()

            result: ExecutionResult = run_executor(
                plan, repo_context, workspace, memory, case.task
            )

            # Verify with the benchmark's verification command
            verify = subprocess.run(
                case.verify_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(work_dir),
                timeout=60,
            )

            bench_result = BenchmarkResult(
                case_name=case.name,
                success=verify.returncode == 0,
                test_exit_code=verify.returncode,
                iterations=result.iterations,
                self_corrections=result.self_corrections,
                tokens_used=result.tokens_used,
                duration_seconds=result.duration_seconds,
                error=result.error or (verify.stderr[:200] if verify.returncode != 0 else ""),
            )
        except Exception as e:
            bench_result = BenchmarkResult(
                case_name=case.name,
                success=False,
                test_exit_code=-1,
                iterations=0,
                self_corrections=0,
                tokens_used=0,
                duration_seconds=0,
                error=str(e),
            )
        finally:
            shutil.rmtree(str(work_dir), ignore_errors=True)

        results.append(bench_result)
        status_icon = "✅" if bench_result.success else "❌"
        console.print(f"  Result: {status_icon} | Iterations: {bench_result.iterations} | Tokens: {bench_result.tokens_used:,}")

    return results


def print_report(results: list[BenchmarkResult]) -> None:
    """Print a rich-formatted summary table."""
    table = Table(title="📊 RepoRefactor AI — Benchmark Report", show_lines=True)
    table.add_column("Case", style="cyan")
    table.add_column("Status")
    table.add_column("Iterations", justify="right")
    table.add_column("Self-Corrections", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Duration", justify="right")

    passed = 0
    for r in results:
        icon = "[green]✅ PASS[/green]" if r.success else "[red]❌ FAIL[/red]"
        if r.success:
            passed += 1
        table.add_row(
            r.case_name,
            icon,
            str(r.iterations),
            str(r.self_corrections),
            f"{r.tokens_used:,}",
            f"{r.duration_seconds:.1f}s",
        )

    console.print(table)
    pass_rate = (passed / len(results)) * 100 if results else 0
    console.print(f"\n[bold]Pass Rate: {passed}/{len(results)} ({pass_rate:.0f}%)[/bold]")
    console.print(f"[dim]→ This is the number to put on your resume.[/dim]\n")


def save_report(results: list[BenchmarkResult], output_path: str = "benchmark_report.json") -> None:
    """Save results to a JSON file for the dashboard."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "pass_rate": sum(1 for r in results if r.success) / len(results) if results else 0,
        "results": [asdict(r) for r in results],
    }
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    console.print(f"[dim]Report saved to {output_path}[/dim]")


if __name__ == "__main__":
    results = run_benchmark()
    print_report(results)
    save_report(results)
