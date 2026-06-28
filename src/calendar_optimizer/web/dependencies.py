"""In-memory session state for the web interface."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request, Response


_sessions: dict[str, dict[str, Any]] = {}

# One week, in seconds.
_COOKIE_MAX_AGE = 60 * 60 * 24 * 7


def get_session_id(request: Request) -> str:
    return request.cookies.get("session_id", "")


def ensure_session(request: Request, response: Response) -> dict[str, Any]:
    """Return the session for this request, creating one if needed.

    The ``session_id`` cookie is always (re)written onto ``response`` so the
    Set-Cookie header is guaranteed to reach the browser even when ``response``
    is a freshly constructed ``RedirectResponse``. This is what makes the
    Google OAuth callback bind the imported calendar to the caller's session.
    """

    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in _sessions:
        session_id = uuid.uuid4().hex
    if session_id not in _sessions:
        _sessions[session_id] = {}
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
    )
    return _sessions[session_id]


def get_session(request: Request) -> dict[str, Any]:
    session_id = request.cookies.get("session_id", "")
    return _sessions.get(session_id, {})


def clear_sessions() -> None:
    _sessions.clear()
