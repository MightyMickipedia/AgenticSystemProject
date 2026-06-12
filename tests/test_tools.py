from __future__ import annotations

import asyncio
import json

from calendar_optimizer.domain.calendar import WeeklyCalendar
from calendar_optimizer.tools.calendar_tools import (
    analyze_transitions,
    build_calendar_tools,
    transition_buffer_minutes,
)


def test_transition_heuristics() -> None:
    assert transition_buffer_minutes("", "Campus") == (15, "niedrig")
    assert transition_buffer_minutes("Campus", "Google Meet") == (20, "mittel")
    assert transition_buffer_minutes("Campus A", "Campus B") == (30, "mittel")
    assert transition_buffer_minutes("Zoom", "Google Meet") == (0, "hoch")


def test_analyze_transitions_detects_short_buffer(calendar: WeeklyCalendar) -> None:
    warnings = analyze_transitions(calendar)
    assert len(warnings) == 1
    assert warnings[0]["from_event"] == "meeting"
    assert warnings[0]["recommended_minutes"] == 20


def test_calendar_tools_are_read_only(calendar: WeeklyCalendar) -> None:
    tools = {tool.name: tool for tool in build_calendar_tools(calendar)}
    before = calendar.model_dump_json()
    result = asyncio.run(
        tools["find_free_slots"].func(day="2026-06-08", minimum_minutes=60)
    )
    assert len(json.loads(result)) == 2
    assert calendar.model_dump_json() == before


def test_list_events_accepts_filter_by_date_alias(calendar: WeeklyCalendar) -> None:
    tools = {tool.name: tool for tool in build_calendar_tools(calendar)}
    result = asyncio.run(tools["list_events"].func(filter_by_date="2026-06-08"))
    assert [event["id"] for event in json.loads(result)] == ["meeting", "online"]
