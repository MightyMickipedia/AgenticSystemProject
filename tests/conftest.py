from __future__ import annotations

from datetime import date, datetime, time

import pytest

from calendar_optimizer.domain.calendar import CalendarEvent, WeeklyCalendar


@pytest.fixture
def calendar() -> WeeklyCalendar:
    events = (
        CalendarEvent(
            id="meeting",
            title="Meeting",
            start=datetime.fromisoformat("2026-06-08T10:00:00+02:00"),
            end=datetime.fromisoformat("2026-06-08T11:00:00+02:00"),
            location="Campus",
        ),
        CalendarEvent(
            id="online",
            title="Online Sync",
            start=datetime.fromisoformat("2026-06-08T11:10:00+02:00"),
            end=datetime.fromisoformat("2026-06-08T12:00:00+02:00"),
            location="Google Meet",
        ),
        CalendarEvent(
            id="all-day",
            title="Deadline",
            start=datetime.fromisoformat("2026-06-09T00:00:00+02:00"),
            end=datetime.fromisoformat("2026-06-10T00:00:00+02:00"),
            all_day=True,
        ),
    )
    return WeeklyCalendar(
        week_start=date(2026, 6, 8),
        timezone="Europe/Berlin",
        events=events,
        day_start=time(7, 0),
        day_end=time(22, 0),
    )
