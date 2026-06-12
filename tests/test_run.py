from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

import calendar_optimizer.run as run
from calendar_optimizer.domain.calendar import WeeklyCalendar
from calendar_optimizer.integrations.snapshot import save_calendar_snapshot
from calendar_optimizer.run import PROJECT_ROOT, build_parser


def test_default_paths_are_relative_to_project_root() -> None:
    args = build_parser().parse_args([])
    assert args.credentials == PROJECT_ROOT / "credentials.json"
    assert args.token == PROJECT_ROOT / ".secrets" / "google-token.json"
    assert args.snapshot == PROJECT_ROOT / "snapshots" / "latest.json"


def test_google_auth_failure_uses_snapshot(
    tmp_path: Path,
    calendar: WeeklyCalendar,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = tmp_path / "snapshot.json"
    save_calendar_snapshot(calendar, snapshot)
    args = build_parser().parse_args(["--snapshot", str(snapshot)])

    def fail_google_import(**kwargs: object) -> WeeklyCalendar:
        del kwargs
        raise RuntimeError("auth not configured")

    monkeypatch.setattr(run, "load_google_calendar", fail_google_import)
    loaded = run.load_calendar_source(args, date(2026, 6, 8))
    assert loaded == calendar


def test_successful_google_import_creates_snapshot_once(
    tmp_path: Path,
    calendar: WeeklyCalendar,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = tmp_path / "snapshot.json"
    args = build_parser().parse_args(["--snapshot", str(snapshot)])
    monkeypatch.setattr(run, "load_google_calendar", lambda **kwargs: calendar)
    loaded = run.load_calendar_source(args, date(2026, 6, 8))
    assert loaded == calendar
    assert snapshot.exists()


def test_successful_google_import_does_not_overwrite_existing_snapshot(
    tmp_path: Path,
    calendar: WeeklyCalendar,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = tmp_path / "snapshot.json"
    save_calendar_snapshot(calendar, snapshot)
    original_content = snapshot.read_text(encoding="utf-8")
    changed_calendar = calendar.model_copy(update={"events": ()})
    args = build_parser().parse_args(["--snapshot", str(snapshot)])
    monkeypatch.setattr(run, "load_google_calendar", lambda **kwargs: changed_calendar)
    loaded = run.load_calendar_source(args, date(2026, 6, 8))
    assert loaded == changed_calendar
    assert snapshot.read_text(encoding="utf-8") == original_content
