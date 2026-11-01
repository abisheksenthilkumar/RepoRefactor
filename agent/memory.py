"""
agent/memory.py
───────────────
Short-term in-session memory for the agent.
Tracks which files were read/edited in the current session so the agent
avoids contradictory edits across multiple tool calls.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryEntry:
    file_path: str
    action: str          # "read" | "edited" | "created" | "deleted"
    summary: str         # brief description of what changed
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentMemory:
    """
    Lightweight in-memory store.  In Phase 2 this can be swapped for
    a Redis backend (just replace the list with Redis LPUSH/LRANGE calls).
    """

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []

    def record(self, file_path: str, action: str, summary: str) -> None:
        self._entries.append(MemoryEntry(file_path, action, summary))

    def recall(self, file_path: str) -> list[MemoryEntry]:
        """Return all memory entries for a given file."""
        return [e for e in self._entries if e.file_path == file_path]

    def recent(self, n: int = 10) -> list[MemoryEntry]:
        """Return the N most recent entries."""
        return self._entries[-n:]

    def to_context_string(self) -> str:
        """
        Summarise memory into a string injected into every Gemini prompt
        so the agent always knows what it already did this session.
        """
        if not self._entries:
            return "No previous actions in this session."
        lines = ["=== SESSION MEMORY (what you have already done) ==="]
        for e in self._entries[-20:]:   # last 20 actions
            lines.append(f"  [{e.action.upper()}] {e.file_path} — {e.summary}")
        return "\n".join(lines)

    def clear(self) -> None:
        self._entries.clear()
