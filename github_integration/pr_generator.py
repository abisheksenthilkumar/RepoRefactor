"""
github_integration/pr_generator.py
────────────────────────────────────
Pushes the agent's committed branch to GitHub and opens a Draft PR
with an AI-generated title, description, and structured changelog.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from google import genai
from github import Github, GithubException

from config import config
from rich.console import Console

console = Console()

_client = genai.Client(api_key=config.GEMINI_API_KEY)


def push_branch(repo_path: Path, branch_name: str, remote_url: str) -> bool:
    """Push a local branch to the GitHub remote."""
    try:
        # Set the remote URL with auth token
        auth_url = remote_url.replace(
            "https://github.com",
            f"https://{config.GITHUB_TOKEN}@github.com"
        )
        subprocess.run(
            ["git", "remote", "set-url", "origin", auth_url],
            cwd=str(repo_path), capture_output=True, check=True
        )
        result = subprocess.run(
            ["git", "push", "origin", branch_name],
            cwd=str(repo_path), capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            console.log(f"[red]Push failed: {result.stderr}[/red]")
            return False
        console.log(f"[green]✅ Branch '{branch_name}' pushed to GitHub.[/green]")
        return True
    except Exception as e:
        console.log(f"[red]Push error: {e}[/red]")
        return False


def generate_pr_body(task: str, files_changed: list[str], action_log: list[dict]) -> str:
    """Use Gemini to write a professional PR description from the agent's work log."""
    model = genai.GenerativeModel(model_name=config.GEMINI_MODEL)

    action_summary = "\n".join(
        f"- [{a['action']}] {a['detail']}" for a in action_log[:30]
    )

    prompt = f"""You are a senior software engineer writing a GitHub Pull Request description.

## Context
- Task requested: {task}
- Files modified: {', '.join(files_changed) or 'None recorded'}
- Agent action log:
{action_summary}

## Write a professional PR description with these sections:
### 🎯 Summary
One paragraph describing what this PR does and why.

### ✅ Changes Made
A bullet-point list of the actual changes (be specific about files and what changed).

### 🧪 Testing
How the changes were verified (tests run, results).

### ⚠️ Review Notes
Any areas that need human review, edge cases, or known limitations.

Keep the tone professional. Use emojis sparingly (only in headers).
"""

    response = _client.models.generate_content(model=config.GEMINI_MODEL, contents=prompt)
    return response.text.strip()


def open_pull_request(
    github_url: str,
    branch_name: str,
    task: str,
    files_changed: list[str],
    action_log: list[dict],
) -> str:
    """
    Open a GitHub Draft Pull Request and return the PR URL.

    Args:
        github_url:    HTTPS URL of the repository.
        branch_name:   The branch the agent committed to.
        task:          Original user task (used for PR title generation).
        files_changed: List of files the agent modified.
        action_log:    Agent's action log from WorkspaceContext.

    Returns:
        The URL of the created PR, or an empty string on failure.
    """
    try:
        g = Github(config.GITHUB_TOKEN)

        # Extract "owner/repo" from the GitHub URL
        # e.g. https://github.com/alice/my-app → alice/my-app
        repo_slug = github_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
        gh_repo = g.get_repo(repo_slug)

        # Generate PR title (short, conventional commit style)
        pr_title = f"[RepoRefactor AI] {task[:80]}"

        # Generate PR body with Gemini
        console.log("[cyan]Generating PR description with Gemini...[/cyan]")
        pr_body = generate_pr_body(task, files_changed, action_log)

        pr = gh_repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=gh_repo.default_branch,
            draft=True,
        )

        console.log(f"[green]✅ Draft PR created: {pr.html_url}[/green]")
        return pr.html_url

    except GithubException as e:
        console.log(f"[red]GitHub API error: {e.data}[/red]")
        return ""
    except Exception as e:
        console.log(f"[red]PR creation failed: {e}[/red]")
        return ""
