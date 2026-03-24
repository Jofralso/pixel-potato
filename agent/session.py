"""
Session management for concurrent client connections.
Stores messages in OpenAI-compatible format to support proper tool call threading.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    session_id: str
    messages: list[dict] = field(default_factory=list)
    _cancelled: bool = False
    created_at: float = field(default_factory=time.time)
    cwd: str = "/workspace"

    # ── Message helpers (OpenAI-compatible format) ────────────

    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_text(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

    def add_assistant_tool_calls(self, content: str | None, tool_calls: list[dict]):
        """Store an assistant turn that includes tool_calls (OpenAI format)."""
        msg: dict[str, Any] = {"role": "assistant", "tool_calls": tool_calls}
        if content:
            msg["content"] = content
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, name: str, content: str):
        """Store a tool result that references its call by id."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })

    # ── Conversion for each LLM provider ─────────────────────

    def get_messages_openai(self) -> list[dict]:
        """Return messages in native OpenAI format (tool_calls + tool role)."""
        return self.messages

    def get_messages_ollama(self) -> list[dict]:
        """Ollama uses the same format as OpenAI for tool calling."""
        return self.messages

    def get_messages_anthropic(self) -> list[dict]:
        """Convert to Anthropic format: content blocks + tool_use/tool_result."""
        out: list[dict] = []
        i = 0
        while i < len(self.messages):
            msg = self.messages[i]
            role = msg["role"]

            if role == "user":
                out.append({"role": "user", "content": msg["content"]})

            elif role == "assistant":
                blocks: list[dict] = []
                if msg.get("content"):
                    blocks.append({"type": "text", "text": msg["content"]})
                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", tc)
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        import json
                        args = json.loads(args)
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", fn.get("name", "")),
                        "name": fn.get("name", ""),
                        "input": args,
                    })
                if blocks:
                    out.append({"role": "assistant", "content": blocks})

            elif role == "tool":
                # Group consecutive tool results into one user turn
                results: list[dict] = []
                while i < len(self.messages) and self.messages[i]["role"] == "tool":
                    t = self.messages[i]
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": t.get("tool_call_id", ""),
                        "content": t.get("content", ""),
                    })
                    i += 1
                out.append({"role": "user", "content": results})
                continue  # skip i += 1 at bottom

            i += 1
        return out

    # ── Cancellation ──────────────────────────────────────────

    def cancel_current(self):
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def reset_cancel(self):
        self._cancelled = False


class SessionManager:
    def __init__(self, max_sessions: int = 2):
        self.max_sessions = max_sessions
        self._sessions: dict[str, Session] = {}

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    def can_accept(self) -> bool:
        return self.active_count < self.max_sessions

    def create_session(self, session_id: str) -> Session:
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def remove_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)
