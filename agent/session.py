"""
Session management for concurrent client connections.
"""

import asyncio
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Session:
    session_id: str
    messages: list[Message] = field(default_factory=list)
    _cancelled: bool = False

    def add_message(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))

    def cancel_current(self):
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def reset_cancel(self):
        self._cancelled = False

    def get_history(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


class SessionManager:
    def __init__(self, max_sessions: int = 2):
        self.max_sessions = max_sessions
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

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
