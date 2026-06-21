"""Google OAuth web redirect flow."""

from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from calendar_optimizer.domain.calendar import WeeklyCalendar
from calendar_optimizer.integrations.google_calendar import SCOPES, fetch_google_events
from calendar_optimizer.web.dependencies import ensure_session, get_session

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CREDENTIALS_PATH = Path(
    os.environ.get("GOOGLE_CREDENTIALS_PATH", str(PROJECT_ROOT / "credentials.json"))
)
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")


def _get_flow() -> Any:
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="google-auth-oauthlib not installed") from exc

    if not CREDENTIALS_PATH.exists():
        raise HTTPException(status_code=500, detail=f"credentials.json not found at {CREDENTIALS_PATH}")

    return Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=list(SCOPES),
        redirect_uri=REDIRECT_URI,
    )


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    flow = _get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    request: Request,
    response: Response,
) -> RedirectResponse:
    flow = _get_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    session = ensure_session(request, response)
    session["google_credentials"] = credentials

    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        timezone = "Europe/Berlin"
        today = datetime.now(ZoneInfo(timezone)).date()
        week_start = today - timedelta(days=today.weekday())
        events = fetch_google_events(service, "primary", week_start, timezone)
        calendar = WeeklyCalendar(
            week_start=week_start,
            timezone=timezone,
            events=events,
            day_start=time(7, 0),
            day_end=time(22, 0),
        )
        session["calendar"] = calendar
    except Exception:
        pass

    redirect = RedirectResponse(url="/")
    redirect.set_cookie("session_id", request.cookies.get("session_id", ""), httponly=True, samesite="lax")
    return redirect


@router.get("/status")
async def auth_status(request: Request) -> dict[str, Any]:
    session = get_session(request)
    creds = session.get("google_credentials")
    return {
        "authenticated": creds is not None and (not hasattr(creds, "valid") or creds.valid),
        "has_calendar": session.get("calendar") is not None,
    }


@router.post("/logout")
async def logout(request: Request) -> dict[str, str]:
    session = get_session(request)
    session.pop("google_credentials", None)
    return {"status": "ok"}
