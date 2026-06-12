from __future__ import annotations

from datetime import date, time
from pathlib import Path

from calendar_optimizer.integrations.google_calendar import load_json_calendar


def test_sample_calendar_loads_as_one_week() -> None:
    sample = Path(__file__).parents[1] / "examples" / "sample_calendar.json"
    calendar = load_json_calendar(
        sample,
        week_start=date(2026, 6, 8),
        timezone="Europe/Berlin",
        day_start=time(7, 0),
        day_end=time(22, 0),
    )
    assert calendar.week_start == date(2026, 6, 8)
    assert len(calendar.events) == 6
    assert calendar.event_by_id("all-day-deadline").all_day is True
