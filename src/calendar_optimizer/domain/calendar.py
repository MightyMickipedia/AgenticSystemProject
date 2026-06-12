"""Immutable, timezone-aware calendar domain models."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Iterable
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FrozenModel(BaseModel):
    """Base model for immutable domain values."""

    model_config = ConfigDict(frozen=True)


class Flexibility(StrEnum):
    """Agent-estimated likelihood that an event can be moved."""

    FIXED = "fixed"
    LIKELY_FIXED = "likely_fixed"
    UNCERTAIN = "uncertain"
    LIKELY_FLEXIBLE = "likely_flexible"
    FLEXIBLE = "flexible"


class CalendarEvent(FrozenModel):
    """An event imported from a read-only calendar source."""

    id: str
    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    location: str = ""
    description: str = ""
    calendar_id: str = "primary"
    recurring_event_id: str | None = None
    html_link: str | None = None

    @field_validator("start", "end")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event datetimes must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_positive_duration(self) -> CalendarEvent:
        if self.end <= self.start:
            raise ValueError("event end must be after start")
        return self

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


class TimeSlot(FrozenModel):
    """A free interval within configured working hours."""

    start: datetime
    end: datetime

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


class MoveProposal(FrozenModel):
    """A non-binding proposal to move an existing event."""

    event_id: str
    new_start: datetime
    new_end: datetime
    reason: str
    flexibility: Flexibility = Flexibility.UNCERTAIN
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("new_start", "new_end")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("proposal datetimes must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_positive_duration(self) -> MoveProposal:
        if self.new_end <= self.new_start:
            raise ValueError("proposal end must be after start")
        return self


class RejectedProposal(FrozenModel):
    proposal: MoveProposal
    reason: str


class OptimizationVariant(FrozenModel):
    name: str
    summary: str
    proposals: tuple[MoveProposal, ...] = ()


class OptimizationReport(FrozenModel):
    week_start: date
    generated_at: datetime
    recommended_variant: OptimizationVariant
    alternatives: tuple[OptimizationVariant, ...] = ()
    hr_warnings: tuple[str, ...] = ()
    traffic_warnings: tuple[str, ...] = ()
    rejected_proposals: tuple[RejectedProposal, ...] = ()
    notes: tuple[str, ...] = ()


class WeeklyCalendar(FrozenModel):
    """Internal representation of one calendar week."""

    week_start: date
    timezone: str
    events: tuple[CalendarEvent, ...] = ()
    day_start: time = time(7, 0)
    day_end: time = time(22, 0)

    @model_validator(mode="after")
    def validate_calendar(self) -> WeeklyCalendar:
        if self.week_start.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        if self.day_end <= self.day_start:
            raise ValueError("day_end must be after day_start")
        ZoneInfo(self.timezone)
        return self

    @classmethod
    def for_current_week(
        cls,
        timezone: str,
        events: Iterable[CalendarEvent] = (),
        day_start: time = time(7, 0),
        day_end: time = time(22, 0),
        now: datetime | None = None,
    ) -> WeeklyCalendar:
        zone = ZoneInfo(timezone)
        local_now = (now or datetime.now(zone)).astimezone(zone)
        monday = local_now.date() - timedelta(days=local_now.weekday())
        return cls(
            week_start=monday,
            timezone=timezone,
            events=tuple(sorted(events, key=lambda event: event.start)),
            day_start=day_start,
            day_end=day_end,
        )

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def start(self) -> datetime:
        return datetime.combine(self.week_start, time.min, self.zone)

    @property
    def end(self) -> datetime:
        return self.start + timedelta(days=7)

    def event_by_id(self, event_id: str) -> CalendarEvent | None:
        return next((event for event in self.events if event.id == event_id), None)

    def events_on(self, day: date) -> tuple[CalendarEvent, ...]:
        day_start = datetime.combine(day, time.min, self.zone)
        day_end = day_start + timedelta(days=1)
        return tuple(
            event
            for event in self.events
            if event.start < day_end and event.end > day_start
        )

    def free_slots(self, day: date, minimum_minutes: int = 30) -> tuple[TimeSlot, ...]:
        return self.free_slots_excluding(day, minimum_minutes)

    def free_slots_excluding(
        self,
        day: date,
        minimum_minutes: int = 30,
        exclude_event_id: str | None = None,
    ) -> tuple[TimeSlot, ...]:
        window_start = datetime.combine(day, self.day_start, self.zone)
        window_end = datetime.combine(day, self.day_end, self.zone)
        busy = sorted(
            (
                max(event.start.astimezone(self.zone), window_start),
                min(event.end.astimezone(self.zone), window_end),
            )
            for event in self.events_on(day)
            if event.id != exclude_event_id
            and not event.all_day
            and event.start < window_end
            and event.end > window_start
        )

        slots: list[TimeSlot] = []
        cursor = window_start
        for start, end in busy:
            if start > cursor and (start - cursor) >= timedelta(minutes=minimum_minutes):
                slots.append(TimeSlot(start=cursor, end=start))
            cursor = max(cursor, end)
        if window_end > cursor and (window_end - cursor) >= timedelta(minutes=minimum_minutes):
            slots.append(TimeSlot(start=cursor, end=window_end))
        return tuple(slots)

    def conflict_pairs(self) -> tuple[tuple[str, str], ...]:
        """Return every overlapping pair of timed events exactly once."""

        timed_events = sorted(
            (event for event in self.events if not event.all_day),
            key=lambda event: event.start,
        )
        conflicts: list[tuple[str, str]] = []
        for index, first in enumerate(timed_events):
            for second in timed_events[index + 1 :]:
                if second.start >= first.end:
                    break
                if first.start < second.end:
                    conflicts.append((first.id, second.id))
        return tuple(conflicts)

    def conflict_ids(
        self,
        start: datetime,
        end: datetime,
        exclude_event_id: str | None = None,
    ) -> tuple[str, ...]:
        return tuple(
            event.id
            for event in self.events
            if event.id != exclude_event_id
            and not event.all_day
            and event.start < end
            and event.end > start
        )

    def validate_proposal(self, proposal: MoveProposal) -> str | None:
        event = self.event_by_id(proposal.event_id)
        if event is None:
            return "Unbekannter Termin."
        if event.all_day:
            return "Ganztägige Termine werden nicht verschoben."
        if (proposal.new_end - proposal.new_start) != (event.end - event.start):
            return "Die Termindauer darf nicht verändert werden."
        if proposal.new_start < self.start or proposal.new_end > self.end:
            return "Der Vorschlag liegt außerhalb der betrachteten Woche."
        local_start = proposal.new_start.astimezone(self.zone)
        local_end = proposal.new_end.astimezone(self.zone)
        if (
            local_start.date() != local_end.date()
            or local_start.time() < self.day_start
            or local_end.time() > self.day_end
        ):
            return "Der Vorschlag liegt außerhalb des konfigurierten Tagesfensters."
        conflicts = self.conflict_ids(
            proposal.new_start,
            proposal.new_end,
            exclude_event_id=proposal.event_id,
        )
        if conflicts:
            return f"Der Vorschlag kollidiert mit: {', '.join(conflicts)}."
        return None

    def with_move(self, proposal: MoveProposal) -> WeeklyCalendar:
        error = self.validate_proposal(proposal)
        if error:
            raise ValueError(error)
        moved = tuple(
            event.model_copy(
                update={"start": proposal.new_start, "end": proposal.new_end}
            )
            if event.id == proposal.event_id
            else event
            for event in self.events
        )
        return self.model_copy(update={"events": tuple(sorted(moved, key=lambda item: item.start))})

    def apply_variant(self, variant: OptimizationVariant) -> WeeklyCalendar:
        """Apply already validated advisory moves to an immutable copy."""

        calendar = self
        for proposal in variant.proposals:
            calendar = calendar.with_move(proposal)
        return calendar

    def build_conflict_resolution_variant(self) -> OptimizationVariant:
        """Deterministically propose moves until no timed event overlaps remain."""

        calendar = self
        proposals: list[MoveProposal] = []
        max_moves = len(self.events)
        while calendar.conflict_pairs():
            if len(proposals) >= max_moves:
                raise RuntimeError("Bestehende Terminkonflikte konnten nicht aufgelöst werden.")

            first_id, second_id = calendar.conflict_pairs()[0]
            event = calendar.event_by_id(second_id)
            if event is None:
                raise RuntimeError("Konflikt referenziert einen unbekannten Termin.")

            duration = event.duration_minutes
            candidates: list[TimeSlot] = []
            for day_offset in range(7):
                day = self.week_start + timedelta(days=day_offset)
                candidates.extend(
                    calendar.free_slots_excluding(
                        day,
                        minimum_minutes=duration,
                        exclude_event_id=event.id,
                    )
                )
            candidates.sort(
                key=lambda slot: abs((slot.start - event.start).total_seconds())
            )
            if not candidates:
                raise RuntimeError(
                    f"Kein konfliktfreier Zeitslot für Termin '{event.title}' verfügbar."
                )

            slot = candidates[0]
            proposal = MoveProposal(
                event_id=event.id,
                new_start=slot.start,
                new_end=slot.start + timedelta(minutes=duration),
                reason=f"Bestehenden Terminkonflikt mit {first_id} auflösen.",
                flexibility=Flexibility.UNCERTAIN,
                confidence=0.5,
            )
            calendar = calendar.with_move(proposal)
            proposals.append(proposal)

        return OptimizationVariant(
            name="Garantierte Konfliktauflösung",
            summary="Deterministisch erzeugte Variante, die alle bestehenden Überschneidungen auflöst.",
            proposals=tuple(proposals),
        )

    def validate_variant(
        self, variant: OptimizationVariant
    ) -> tuple[OptimizationVariant, tuple[RejectedProposal, ...]]:
        calendar = self
        accepted: list[MoveProposal] = []
        rejected: list[RejectedProposal] = []
        moved_event_ids: set[str] = set()
        for proposal in variant.proposals:
            if proposal.event_id in moved_event_ids:
                rejected.append(
                    RejectedProposal(
                        proposal=proposal,
                        reason="Ein Termin darf pro Variante nur einmal verschoben werden.",
                    )
                )
                continue
            error = calendar.validate_proposal(proposal)
            if error:
                rejected.append(RejectedProposal(proposal=proposal, reason=error))
                continue
            accepted.append(proposal)
            moved_event_ids.add(proposal.event_id)
            calendar = calendar.with_move(proposal)
        return (
            variant.model_copy(update={"proposals": tuple(accepted)}),
            tuple(rejected),
        )
