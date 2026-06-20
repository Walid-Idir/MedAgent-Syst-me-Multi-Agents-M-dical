from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SessionData:
    state: dict
    last_interrupt: dict | None


SESSION_STORE: dict[str, SessionData] = {}


def save_session(thread_id: str, state: dict, last_interrupt: dict | None) -> None:
    SESSION_STORE[thread_id] = SessionData(state=state, last_interrupt=last_interrupt)


def get_session(thread_id: str) -> SessionData | None:
    return SESSION_STORE.get(thread_id)
