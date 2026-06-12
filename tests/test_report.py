from __future__ import annotations

from datetime import datetime

from calendar_optimizer.domain.calendar import OptimizationReport, OptimizationVariant, WeeklyCalendar
from calendar_optimizer.report import render_markdown


def test_report_explicitly_states_read_only(calendar: WeeklyCalendar) -> None:
    report = OptimizationReport(
        week_start=calendar.week_start,
        generated_at=datetime.fromisoformat("2026-06-12T12:00:00+02:00"),
        recommended_variant=OptimizationVariant(name="Status quo", summary="Keine Änderung"),
    )
    output = render_markdown(calendar, report)
    assert "Es wurden keine Änderungen am Kalender vorgenommen" in output
    assert "calendar.events.readonly" in output
    assert "garantiert frei von Terminüberschneidungen" in output
