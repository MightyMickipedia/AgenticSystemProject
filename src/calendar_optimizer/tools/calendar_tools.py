"""Read-only calendar tools and deterministic travel heuristics."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from agent_squad.utils import AgentTool

from calendar_optimizer.domain.calendar import WeeklyCalendar


def _is_virtual(location: str) -> bool:
    lowered = location.lower()
    return any(token in lowered for token in ("zoom", "meet", "teams", "online", "virtual"))


def transition_buffer_minutes(first_location: str, second_location: str) -> tuple[int, str]:
    """Return the conservative transition buffer and confidence label."""

    if not first_location or not second_location:
        return 15, "low"
    first_virtual = _is_virtual(first_location)
    second_virtual = _is_virtual(second_location)
    if first_virtual != second_virtual:
        return 20, "medium"
    if first_virtual and second_virtual:
        return 0, "high"
    if first_location.strip().casefold() == second_location.strip().casefold():
        return 0, "high"
    return 30, "medium"


def analyze_transitions(calendar: WeeklyCalendar) -> list[dict[str, Any]]:
    """Analyze travel/transition buffers between consecutive timed events."""

    warnings: list[dict[str, Any]] = []
    for day_offset in range(7):
        day = calendar.week_start.fromordinal(calendar.week_start.toordinal() + day_offset)
        events = sorted(
            (event for event in calendar.events_on(day) if not event.all_day),
            key=lambda event: event.start,
        )
        for first, second in zip(events, events[1:]):
            required, confidence = transition_buffer_minutes(first.location, second.location)
            available = int((second.start - first.end).total_seconds() // 60)
            if available < required:
                warnings.append(
                    {
                        "from_event": first.id,
                        "to_event": second.id,
                        "available_minutes": available,
                        "recommended_minutes": required,
                        "confidence": confidence,
                    }
                )
    return warnings


def build_calendar_tools(calendar: WeeklyCalendar) -> list[AgentTool]:
    """Create read-only Agent Squad tools bound to one immutable calendar."""

    def list_events(day: str = "", filter_by_date: str = "") -> str:
        selected_date = day or filter_by_date
        selected = (
            calendar.events_on(date.fromisoformat(selected_date))
            if selected_date
            else calendar.events
        )
        return json.dumps(
            [event.model_dump(mode="json") for event in selected],
            ensure_ascii=False,
        )

    def day_summary(day: str) -> str:
        selected_day = date.fromisoformat(day)
        events = calendar.events_on(selected_day)
        free = calendar.free_slots(selected_day)
        return json.dumps(
            {
                "events": [event.model_dump(mode="json") for event in events],
                "free_slots": [slot.model_dump(mode="json") for slot in free],
            },
            ensure_ascii=False,
        )

    def find_free_slots(day: str, minimum_minutes: int = 30) -> str:
        return json.dumps(
            [
                slot.model_dump(mode="json")
                for slot in calendar.free_slots(date.fromisoformat(day), minimum_minutes)
            ],
            ensure_ascii=False,
        )

    def check_conflict(event_id: str, new_start: str, new_end: str) -> str:
        start = datetime.fromisoformat(new_start)
        end = datetime.fromisoformat(new_end)
        conflicts = calendar.conflict_ids(start, end, exclude_event_id=event_id)
        return json.dumps({"conflict": bool(conflicts), "event_ids": conflicts})

    def travel_warnings() -> str:
        return json.dumps(analyze_transitions(calendar), ensure_ascii=False)

    def list_conflicts() -> str:
        return json.dumps(
            [
                {"first_event_id": first, "second_event_id": second}
                for first, second in calendar.conflict_pairs()
            ],
            ensure_ascii=False,
        )

    return [
        AgentTool(
            name="list_events",
            description="List calendar events. Optionally filter by ISO date.",
            properties={
                "day": {"type": "string", "description": "ISO date or empty string"},
                "filter_by_date": {
                    "type": "string",
                    "description": "Alias for day; ISO date or empty string",
                },
            },
            required=[],
            func=list_events,
        ),
        AgentTool(
            name="day_summary",
            description="Return events and free slots for one ISO date.",
            properties={"day": {"type": "string", "description": "ISO date"}},
            required=["day"],
            func=day_summary,
        ),
        AgentTool(
            name="find_free_slots",
            description="Find free slots during configured day hours.",
            properties={
                "day": {"type": "string", "description": "ISO date"},
                "minimum_minutes": {"type": "integer", "description": "Minimum slot length"},
            },
            required=["day"],
            func=find_free_slots,
        ),
        AgentTool(
            name="check_conflict",
            description="Check whether moving an event to a time interval would conflict.",
            properties={
                "event_id": {"type": "string", "description": "Existing event ID"},
                "new_start": {"type": "string", "description": "Timezone-aware ISO datetime"},
                "new_end": {"type": "string", "description": "Timezone-aware ISO datetime"},
            },
            required=["event_id", "new_start", "new_end"],
            func=check_conflict,
        ),
        AgentTool(
            name="list_conflicts",
            description="List all existing overlapping timed event pairs.",
            properties={},
            required=[],
            func=list_conflicts,
        ),
        AgentTool(
            name="travel_warnings",
            description="Return heuristic warnings for insufficient transition buffers.",
            properties={},
            required=[],
            func=travel_warnings,
        ),
    ]
