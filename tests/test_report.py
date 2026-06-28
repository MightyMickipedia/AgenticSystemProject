from __future__ import annotations

from datetime import datetime

from calendar_optimizer.domain.calendar import OptimizationReport, OptimizationVariant, WeeklyCalendar
from calendar_optimizer.report import render_markdown


def test_report_explicitly_states_read_only(calendar: WeeklyCalendar) -> None:
    report = OptimizationReport(
        week_start=calendar.week_start,
        generated_at=datetime.fromisoformat("2026-06-12T12:00:00+02:00"),
        recommended_variant=OptimizationVariant(name="Status quo", summary="No change"),
        human_recommendations=("Keep the current plan, but protect travel slack.",),
    )
    output = render_markdown(calendar, report)
    assert "No changes were made to the calendar" in output
    assert "calendar.events.readonly" in output
    assert "guaranteed free of scheduling overlaps" in output
    assert "## Human recommendations" in output
    assert "Keep the current plan, but protect travel slack." in output
