"""Read-only Google Calendar OAuth integration."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from calendar_optimizer.domain.calendar import CalendarEvent, WeeklyCalendar

SCOPES = ("https://www.googleapis.com/auth/calendar.events.readonly",)


def _parse_datetime(value: str, timezone: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
    return parsed


def google_event_to_domain(
    item: dict[str, Any],
    timezone: str,
    calendar_id: str = "primary",
) -> CalendarEvent:
    """Convert a Google Calendar event resource into the internal model."""

    start_value = item["start"]
    end_value = item["end"]
    all_day = "date" in start_value
    if all_day:
        zone = ZoneInfo(timezone)
        start = datetime.combine(date.fromisoformat(start_value["date"]), time.min, zone)
        end = datetime.combine(date.fromisoformat(end_value["date"]), time.min, zone)
    else:
        start = _parse_datetime(start_value["dateTime"], start_value.get("timeZone", timezone))
        end = _parse_datetime(end_value["dateTime"], end_value.get("timeZone", timezone))

    return CalendarEvent(
        id=item["id"],
        title=item.get("summary", "(Ohne Titel)"),
        start=start,
        end=end,
        all_day=all_day,
        location=item.get("location", ""),
        description=item.get("description", ""),
        calendar_id=calendar_id,
        recurring_event_id=item.get("recurringEventId"),
        html_link=item.get("htmlLink"),
    )


def _is_self_declined(item: dict[str, Any]) -> bool:
    return any(
        attendee.get("self") and attendee.get("responseStatus") == "declined"
        for attendee in item.get("attendees", [])
    )


def fetch_google_events(
    service: Any,
    calendar_id: str,
    week_start: date,
    timezone: str,
) -> tuple[CalendarEvent, ...]:
    """Fetch one expanded week from an authenticated Google Calendar service."""

    zone = ZoneInfo(timezone)
    start = datetime.combine(week_start, time.min, zone)
    end = start + timedelta(days=7)
    items: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            )
            .execute()
        )
        items.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return tuple(
        google_event_to_domain(item, timezone, calendar_id)
        for item in items
        if item.get("status") != "cancelled" and not _is_self_declined(item)
    )


def load_google_calendar(
    calendar_id: str,
    week_start: date,
    timezone: str,
    credentials_path: Path,
    token_path: Path,
    day_start: time = time(7, 0),
    day_end: time = time(22, 0),
) -> WeeklyCalendar:
    """Authenticate locally and import one Google Calendar week read-only."""

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as error:
        raise RuntimeError(
            "Google dependencies are missing. Install the requirements first."
        ) from error

    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Google OAuth file not found: {credentials_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    events = fetch_google_events(service, calendar_id, week_start, timezone)
    return WeeklyCalendar(
        week_start=week_start,
        timezone=timezone,
        events=events,
        day_start=day_start,
        day_end=day_end,
    )


def load_json_calendar(
    input_path: Path,
    week_start: date,
    timezone: str,
    day_start: time = time(7, 0),
    day_end: time = time(22, 0),
) -> WeeklyCalendar:
    """Load deterministic local input for demos and tests."""

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    events = tuple(CalendarEvent.model_validate(item) for item in payload["events"])
    calendar = WeeklyCalendar(
        week_start=week_start,
        timezone=timezone,
        events=(),
        day_start=day_start,
        day_end=day_end,
    )
    selected = tuple(
        sorted(
            (
                event
                for event in events
                if event.start < calendar.end and event.end > calendar.start
            ),
            key=lambda event: event.start,
        )
    )
    return calendar.model_copy(update={"events": selected})
