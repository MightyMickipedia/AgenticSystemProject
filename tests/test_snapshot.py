from __future__ import annotations

from pathlib import Path

from calendar_optimizer.domain.calendar import WeeklyCalendar
from calendar_optimizer.integrations.snapshot import (
    load_calendar_snapshot,
    save_calendar_snapshot,
)


def test_snapshot_round_trip(tmp_path: Path, calendar: WeeklyCalendar) -> None:
    path = tmp_path / "snapshot.json"
    assert save_calendar_snapshot(calendar, path) == path
    restored = load_calendar_snapshot(path)
    assert restored == calendar
