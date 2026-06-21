"""Calendar REST endpoints: upload, list, query."""

from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile

from calendar_optimizer.domain.calendar import CalendarEvent, WeeklyCalendar
from calendar_optimizer.integrations.google_calendar import load_json_calendar
from calendar_optimizer.integrations.snapshot import load_calendar_snapshot
from calendar_optimizer.web.dependencies import ensure_session, get_session

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@router.post("/upload")
async def upload_calendar(
    file: UploadFile,
    request: Request,
    response: Response,
    timezone: str = "Europe/Berlin",
    week_start: str | None = None,
    day_start: str = "07:00",
    day_end: str = "22:00",
) -> dict[str, Any]:
    session = ensure_session(request, response)

    content = await file.read()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    if week_start:
        ws = date.fromisoformat(week_start)
    else:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        today = datetime.now(ZoneInfo(timezone)).date()
        ws = today - timedelta(days=today.weekday())

    ds = time.fromisoformat(day_start)
    de = time.fromisoformat(day_end)

    try:
        events = tuple(CalendarEvent.model_validate(item) for item in payload["events"])
        calendar = WeeklyCalendar(
            week_start=ws, timezone=timezone, events=(), day_start=ds, day_end=de,
        )
        selected = tuple(
            sorted(
                (e for e in events if e.start < calendar.end and e.end > calendar.start),
                key=lambda e: e.start,
            )
        )
        calendar = calendar.model_copy(update={"events": selected})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session["calendar"] = calendar
    return calendar.model_dump(mode="json")


@router.post("/load-snapshot")
async def load_snapshot(
    request: Request,
    response: Response,
    path: str | None = None,
) -> dict[str, Any]:
    session = ensure_session(request, response)
    snapshot_path = Path(path) if path else PROJECT_ROOT / "snapshots" / "latest.json"
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")

    calendar = load_calendar_snapshot(snapshot_path)
    session["calendar"] = calendar
    return calendar.model_dump(mode="json")


@router.get("")
async def get_calendar(request: Request) -> dict[str, Any]:
    session = get_session(request)
    calendar: WeeklyCalendar | None = session.get("calendar")
    if calendar is None:
        raise HTTPException(status_code=404, detail="No calendar loaded")
    return calendar.model_dump(mode="json")


@router.get("/events")
async def list_events(request: Request) -> list[dict[str, Any]]:
    session = get_session(request)
    calendar: WeeklyCalendar | None = session.get("calendar")
    if calendar is None:
        raise HTTPException(status_code=404, detail="No calendar loaded")
    return [e.model_dump(mode="json") for e in calendar.events]


@router.get("/events/{day}")
async def events_for_day(day: str, request: Request) -> list[dict[str, Any]]:
    session = get_session(request)
    calendar: WeeklyCalendar | None = session.get("calendar")
    if calendar is None:
        raise HTTPException(status_code=404, detail="No calendar loaded")
    try:
        d = date.fromisoformat(day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format") from exc
    return [e.model_dump(mode="json") for e in calendar.events_on(d)]


@router.get("/conflicts")
async def list_conflicts(request: Request) -> list[dict[str, str]]:
    session = get_session(request)
    calendar: WeeklyCalendar | None = session.get("calendar")
    if calendar is None:
        raise HTTPException(status_code=404, detail="No calendar loaded")
    return [
        {"first_event_id": a, "second_event_id": b}
        for a, b in calendar.conflict_pairs()
    ]


@router.get("/free-slots/{day}")
async def free_slots(day: str, request: Request, minimum_minutes: int = 30) -> list[dict[str, Any]]:
    session = get_session(request)
    calendar: WeeklyCalendar | None = session.get("calendar")
    if calendar is None:
        raise HTTPException(status_code=404, detail="No calendar loaded")
    try:
        d = date.fromisoformat(day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format") from exc
    return [s.model_dump(mode="json") for s in calendar.free_slots(d, minimum_minutes)]
