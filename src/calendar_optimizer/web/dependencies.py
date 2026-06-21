"""In-memory session state for the web interface."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request, Response


_sessions: dict[str, dict[str, Any]] = {}


def get_session_id(request: Request) -> str:
    return request.cookies.get("session_id", "")


def ensure_session(request: Request, response: Response) -> dict[str, Any]:
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in _sessions:
        session_id = uuid.uuid4().hex
        response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    if session_id not in _sessions:
        _sessions[session_id] = {}
    return _sessions[session_id]


def get_session(request: Request) -> dict[str, Any]:
    session_id = request.cookies.get("session_id", "")
    return _sessions.get(session_id, {})


def clear_sessions() -> None:
    _sessions.clear()
