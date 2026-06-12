from __future__ import annotations

from datetime import date, datetime

import pytest

from calendar_optimizer.domain.calendar import (
    CalendarEvent,
    Flexibility,
    MoveProposal,
    OptimizationVariant,
    WeeklyCalendar,
)


def proposal(
    event_id: str,
    start: str,
    end: str,
) -> MoveProposal:
    return MoveProposal(
        event_id=event_id,
        new_start=datetime.fromisoformat(start),
        new_end=datetime.fromisoformat(end),
        reason="Test",
        flexibility=Flexibility.UNCERTAIN,
        confidence=0.5,
    )


def test_current_week_uses_local_monday() -> None:
    calendar = WeeklyCalendar.for_current_week(
        "Europe/Berlin",
        now=datetime.fromisoformat("2026-06-12T12:00:00+02:00"),
    )
    assert calendar.week_start == date(2026, 6, 8)
    assert calendar.start.isoformat() == "2026-06-08T00:00:00+02:00"


def test_week_start_must_be_monday() -> None:
    with pytest.raises(ValueError, match="Monday"):
        WeeklyCalendar(week_start=date(2026, 6, 9), timezone="Europe/Berlin")


def test_free_slots_ignore_all_day_events(calendar: WeeklyCalendar) -> None:
    slots = calendar.free_slots(date(2026, 6, 8))
    assert [(slot.start.hour, slot.end.hour, slot.end.minute) for slot in slots] == [
        (7, 10, 0),
        (12, 22, 0),
    ]
    assert calendar.free_slots(date(2026, 6, 9))[0].duration_minutes == 15 * 60


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        (
            proposal("missing", "2026-06-08T13:00:00+02:00", "2026-06-08T14:00:00+02:00"),
            "Unbekannter",
        ),
        (
            proposal("all-day", "2026-06-10T08:00:00+02:00", "2026-06-11T08:00:00+02:00"),
            "Ganztägige",
        ),
        (
            proposal("meeting", "2026-06-08T13:00:00+02:00", "2026-06-08T15:00:00+02:00"),
            "Termindauer",
        ),
        (
            proposal("meeting", "2026-06-08T11:30:00+02:00", "2026-06-08T12:30:00+02:00"),
            "kollidiert",
        ),
        (
            proposal("meeting", "2026-06-15T10:00:00+02:00", "2026-06-15T11:00:00+02:00"),
            "außerhalb",
        ),
        (
            proposal("meeting", "2026-06-08T22:00:00+02:00", "2026-06-08T23:00:00+02:00"),
            "Tagesfensters",
        ),
    ],
)
def test_invalid_proposals_are_rejected(
    calendar: WeeklyCalendar,
    candidate: MoveProposal,
    expected: str,
) -> None:
    assert expected in (calendar.validate_proposal(candidate) or "")


def test_variant_validation_applies_moves_sequentially(calendar: WeeklyCalendar) -> None:
    valid = proposal(
        "meeting",
        "2026-06-08T13:00:00+02:00",
        "2026-06-08T14:00:00+02:00",
    )
    now_conflicting = proposal(
        "online",
        "2026-06-08T13:30:00+02:00",
        "2026-06-08T14:20:00+02:00",
    )
    variant, rejected = calendar.validate_variant(
        OptimizationVariant(name="Test", summary="Test", proposals=(valid, now_conflicting))
    )
    assert variant.proposals == (valid,)
    assert len(rejected) == 1


def test_variant_rejects_duplicate_move(calendar: WeeklyCalendar) -> None:
    first = proposal(
        "meeting",
        "2026-06-08T13:00:00+02:00",
        "2026-06-08T14:00:00+02:00",
    )
    second = proposal(
        "meeting",
        "2026-06-08T15:00:00+02:00",
        "2026-06-08T16:00:00+02:00",
    )
    variant, rejected = calendar.validate_variant(
        OptimizationVariant(name="Test", summary="Test", proposals=(first, second))
    )
    assert variant.proposals == (first,)
    assert "nur einmal" in rejected[0].reason


def test_conflict_resolution_variant_is_guaranteed_conflict_free() -> None:
    calendar = WeeklyCalendar(
        week_start=date(2026, 6, 8),
        timezone="Europe/Berlin",
        events=(
            CalendarEvent(
                id="first",
                title="First",
                start=datetime.fromisoformat("2026-06-08T10:00:00+02:00"),
                end=datetime.fromisoformat("2026-06-08T11:00:00+02:00"),
            ),
            CalendarEvent(
                id="second",
                title="Second",
                start=datetime.fromisoformat("2026-06-08T10:30:00+02:00"),
                end=datetime.fromisoformat("2026-06-08T11:30:00+02:00"),
            ),
        ),
    )
    assert calendar.conflict_pairs() == (("first", "second"),)
    variant = calendar.build_conflict_resolution_variant()
    assert variant.proposals
    assert calendar.apply_variant(variant).conflict_pairs() == ()
