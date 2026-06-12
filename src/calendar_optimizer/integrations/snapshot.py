"""Local calendar snapshots for offline and authentication fallback use."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from calendar_optimizer.domain.calendar import WeeklyCalendar

SNAPSHOT_SCHEMA_VERSION = 1


def save_calendar_snapshot(calendar: WeeklyCalendar, path: Path) -> Path:
    """Persist an immutable weekly calendar snapshot as JSON."""

    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "calendar": calendar.model_dump(mode="json"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_calendar_snapshot(path: Path) -> WeeklyCalendar:
    """Load and validate a previously stored weekly calendar snapshot."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("Nicht unterstützte Kalender-Snapshot-Version.")
    return WeeklyCalendar.model_validate(payload["calendar"])
