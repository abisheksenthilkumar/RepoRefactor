"""
agent/executor.py
─────────────────
Executor Agent — the agentic loop that drives Gemini to call tools
iteratively until the task is complete (or the iteration cap is hit).

Architecture:
  1. Receives the plan from the Planner.
  2. Sends the plan + repo context + available tools to Gemini.
  3. Gemini responds with a function_call → we dispatch the tool.
  4. Tool result is sent back to Gemini as a function_response.
  5. Loop continues until Gemini returns plain text (task complete)
     or the max iteration cap is hit.

Self-Correction:
  When run_tests() returns a non-zero exit code, the SelfCorrector
  is invoked to generate a focused fix prompt that is injected back
  into the conversation before the next loop iteration.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types

from config import config
from agent.tools import TOOL_SCHEMAS, WorkspaceContext, dispatch_tool
from agent.memory import AgentMemory
from agent.self_corrector import build_correction_prompt
from rich.console import Console

console = Console()

_client = genai.Client(api_key=config.GEMINI_API_KEY)


EXECUTOR_SYSTEM_PROMPT = """You are the Executor Agent in an autonomous enterprise coding system.

You have been given a step-by-step plan and a set of tools.
Execute the plan precisely, calling tools one at a time.

## Key Rules
- ALWAYS call read_file before edit_file to see the current content.
- The 'target' in edit_file MUST be an exact, verbatim substring of the file.
- If run_tests returns FAILED, analyse the error carefully and fix it before committing.
- Never commit if tests are failing.
- When all tasks are done, reply with a plain-text summary starting with "TASK_COMPLETE:".
- Track what you have already done using the session memory provided to you.
- Be conservative: make the minimum change needed to accomplish each step.
"""


@dataclass
class ExecutionResult:
    """Summary of a completed agent run."""
    success: bool
    summary: str
    files_changed: list[str] = field(default_factory=list)
    iterations: int = 0
    self_corrections: int = 0
    tokens_used: int = 0
    duration_seconds: float = 0.0
    action_log: list[dict] = field(default_factory=list)
    pr_url: str = ""
    error: str = ""


def _build_tools_config() -> types.Tool:
    """Convert our JSON schema list into a google.genai Tool object."""
    fn_declarations = [
        types.FunctionDeclaration(
            name=s["name"],
            description=s["description"],
            parameters=s.get("parameters", {}),
        )
        for s in TOOL_SCHEMAS
    ]
    return types.Tool(function_declarations=fn_declarations)


def run_executor(
    plan: str,
    repo_context: str,
    workspace: WorkspaceContext,
    memory: AgentMemory,
    task: str,
    max_iterations: int | None = None,
) -> ExecutionResult:
    """
    Run the agentic executor loop.

    Args:
        plan:           The step-by-step plan from the Planner.
        repo_context:   Full repository source code string.
        workspace:      WorkspaceContext scoped to the cloned repo directory.
        memory:         AgentMemory instance (session-scoped).
        task:           Original user task string (for context).
        max_iterations: Override for config.MAX_SELF_CORRECTION_ITERATIONS.

    Returns:
        ExecutionResult with metrics and status.
    """
    tool_config = _build_tools_config()
    chat = _client.chats.create(
        model=config.GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=EXECUTOR_SYSTEM_PROMPT,
            tools=[tool_config],
            temperature=0.1,
        ),
    )
    max_iters = max_iterations or config.MAX_SELF_CORRECTION_ITERATIONS
    start_time = time.time()
    iteration = 0
    self_corrections = 0
    total_tokens = 0
    files_changed: set[str] = set()

    initial_message = (
        f"## Task\n{task}\n\n"
        f"## Plan\n{plan}\n\n"
        f"## Session Memory\n{memory.to_context_string()}\n\n"
        f"## Repo Context (first 50k chars)\n{repo_context[:50_000]}\n\n"
        f"Begin executing the plan now. Start with step 1."
    )

    console.rule("[bold green]🤖 EXECUTOR AGENT STARTED")

    while iteration < max_iters * 10:  # generous loop cap
        iteration += 1
        console.log(f"[yellow]Iteration {iteration}[/yellow]")

        response = None
        for attempt in range(4):
            try:
                if iteration == 1:
                    response = chat.send_message(initial_message)
                else:
                    response = chat.send_message("Continue with the next step in the plan.")
                break
            except Exception as e:
                err_str = str(e)
                if attempt < 3 and any(code in err_str for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                    wait = 15 * (attempt + 1)
                    console.log(f"[yellow]Transient error on iteration {iteration} (attempt {attempt+1}/4) — waiting {wait}s...[/yellow]")
                    time.sleep(wait)
                else:
                    console.log(f"[red]Gemini API error: {e}[/red]")
                    return ExecutionResult(
                        success=False, summary="", error=err_str,
                        iterations=iteration, self_corrections=self_corrections,
                        tokens_used=total_tokens, duration_seconds=time.time() - start_time,
                        action_log=workspace.action_log,
                    )

        # Track token usage — handle different attribute names across SDK versions
        if response.usage_metadata:
            um = response.usage_metadata
            total_tokens += (
                getattr(um, "total_token_count", None)
                or (getattr(um, "prompt_token_count", 0) + getattr(um, "candidates_token_count", 0))
            )

        # Check for function calls
        candidate = response.candidates[0]
        parts = candidate.content.parts
        called_any_tool = False

        for part in parts:
            if part.function_call:
                called_any_tool = True
                fn = part.function_call
                tool_name = fn.name
                tool_args: dict[str, Any] = dict(fn.args)

                console.log(f"[bold magenta]→ Tool:[/bold magenta] {tool_name}({tool_args})")
                tool_result = dispatch_tool(workspace, tool_name, tool_args)

                if tool_name in ("edit_file", "create_file", "delete_file"):
                    files_changed.add(tool_args.get("path", ""))
                    memory.record(tool_args.get("path", ""), tool_name, tool_name)

                if tool_name == "run_tests":
                    if "FAILED" in tool_result or "error" in tool_result.lower():
                        if self_corrections < config.MAX_SELF_CORRECTION_ITERATIONS:
                            self_corrections += 1
                            tool_result += f"\n\n{build_correction_prompt(tool_result, files_changed)}"

                # Send function response back (with retry on transient errors)
                func_response_part = types.Part.from_function_response(
                    name=tool_name,
                    response={"result": tool_result},
                )
                for attempt in range(4):
                    try:
                        response = chat.send_message(func_response_part)
                        break
                    except Exception as e:
                        if attempt < 3 and any(code in str(e) for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                            wait = 15 * (attempt + 1)
                            console.log(f"[yellow]Transient error sending tool response (attempt {attempt+1}/4) — waiting {wait}s...[/yellow]")
                            time.sleep(wait)
                        else:
                            raise

                if response.usage_metadata:
                    total_tokens += getattr(response.usage_metadata, "total_token_count", 0)

        # Check if Gemini returned a plain-text completion signal
        if not called_any_tool:
            full_text = "".join(
                p.text for p in parts if hasattr(p, "text")
            )
            # Accept TASK_COMPLETE, empty response, or any plain-text summary as done
            is_done = (
                "TASK_COMPLETE" in full_text
                or not full_text.strip()
                or any(phrase in full_text.lower() for phrase in (
                    "all steps complete", "task is complete", "all changes have been made",
                    "migration complete", "refactoring complete", "all tests pass",
                    "successfully completed", "implementation is complete",
                ))
            )
            if is_done:
                console.rule("[bold green]✅ TASK COMPLETE")
                duration = time.time() - start_time
                return ExecutionResult(
                    success=True,
                    summary=full_text,
                    files_changed=list(files_changed),
                    iterations=iteration,
                    self_corrections=self_corrections,
                    tokens_used=total_tokens,
                    duration_seconds=duration,
                    action_log=workspace.action_log,
                )
            # Gemini gave text but no TASK_COMPLETE — keep going
            console.log(f"[dim]Model text (no tool call): {full_text[:200]}[/dim]")

    # Exceeded iteration cap
    duration = time.time() - start_time
    console.rule("[bold red]⚠ ITERATION CAP REACHED")
    return ExecutionResult(
        success=False,
        summary="",
        error=f"Exceeded {max_iters * 10} iterations without TASK_COMPLETE.",
        files_changed=list(files_changed),
        iterations=iteration,
        self_corrections=self_corrections,
        tokens_used=total_tokens,
        duration_seconds=duration,
        action_log=workspace.action_log,
    )
