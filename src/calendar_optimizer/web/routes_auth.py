"""Google OAuth web redirect flow."""

from __future__ import annotations

import os
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from calendar_optimizer.domain.calendar import WeeklyCalendar
from calendar_optimizer.integrations.google_calendar import SCOPES, fetch_google_events
from calendar_optimizer.web.dependencies import ensure_session, get_session

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CREDENTIALS_PATH = Path(
    os.environ.get("GOOGLE_CREDENTIALS_PATH", str(PROJECT_ROOT / "credentials.json"))
)
REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback"
)
# Where to send the browser after the OAuth round-trip finishes. In production
# the frontend is served from the same origin, so "/" is correct. For local
# development set FRONTEND_URL=http://localhost:5173 so the user lands back on
# the Vite dev server instead of the bare backend.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "/")
DEFAULT_TIMEZONE = os.environ.get("CALENDAR_TIMEZONE", "Europe/Berlin")


def _get_flow() -> Any:
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="google-auth-oauthlib not installed") from exc

    if not CREDENTIALS_PATH.exists():
        raise HTTPException(
            status_code=500, detail=f"credentials.json not found at {CREDENTIALS_PATH}"
        )

    return Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=list(SCOPES),
        redirect_uri=REDIRECT_URI,
    )


def _post_login_url(suffix: str = "") -> str:
    base = FRONTEND_URL.rstrip("/") if FRONTEND_URL != "/" else ""
    return f"{base}/{suffix}" if suffix else (base or "/")


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    flow = _get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        return RedirectResponse(url=_post_login_url(f"?auth_error={error}"))
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    flow = _get_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Build the redirect first and bind the session cookie to it, so the new
    # session_id actually reaches the browser. Storing on a separate Response
    # object would drop the Set-Cookie header and orphan the imported calendar.
    redirect = RedirectResponse(url=_post_login_url())
    session = ensure_session(request, redirect)
    session["google_credentials"] = credentials
    session.pop("google_import_error", None)

    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        today = datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date()
        week_start = today - timedelta(days=today.weekday())
        events = fetch_google_events(service, "primary", week_start, DEFAULT_TIMEZONE)
        session["calendar"] = WeeklyCalendar(
            week_start=week_start,
            timezone=DEFAULT_TIMEZONE,
            events=events,
            day_start=time(7, 0),
            day_end=time(22, 0),
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the client via /status
        session["google_import_error"] = str(exc)

    return redirect


@router.get("/status")
async def auth_status(request: Request) -> dict[str, Any]:
    session = get_session(request)
    creds = session.get("google_credentials")

    authenticated = creds is not None
    if creds is not None and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        try:
            from google.auth.transport.requests import Request as GoogleRequest

            creds.refresh(GoogleRequest())
        except Exception:  # noqa: BLE001 - treat unrefreshable creds as logged out
            authenticated = False
    elif creds is not None and hasattr(creds, "valid"):
        authenticated = bool(creds.valid)

    return {
        "authenticated": authenticated,
        "has_calendar": session.get("calendar") is not None,
        "import_error": session.get("google_import_error"),
    }


@router.post("/logout")
async def logout(request: Request) -> dict[str, str]:
    session = get_session(request)
    session.pop("google_credentials", None)
    session.pop("google_import_error", None)
    return {"status": "ok"}
