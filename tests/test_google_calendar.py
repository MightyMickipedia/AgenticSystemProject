from __future__ import annotations

from datetime import date
from typing import Any

from calendar_optimizer.integrations.google_calendar import (
    SCOPES,
    fetch_google_events,
    google_event_to_domain,
)


class FakeRequest:
    def __init__(self, response: dict[str, Any]):
        self.response = response

    def execute(self) -> dict[str, Any]:
        return self.response


class FakeEvents:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def list(self, **kwargs: Any) -> FakeRequest:
        self.calls.append(kwargs)
        if kwargs["pageToken"] is None:
            return FakeRequest(
                {
                    "items": [
                        {
                            "id": "one",
                            "summary": "One",
                            "start": {"dateTime": "2026-06-08T10:00:00+02:00"},
                            "end": {"dateTime": "2026-06-08T11:00:00+02:00"},
                        },
                        {
                            "id": "cancelled",
                            "status": "cancelled",
                            "start": {"date": "2026-06-09"},
                            "end": {"date": "2026-06-10"},
                        },
                        {
                            "id": "declined",
                            "attendees": [{"self": True, "responseStatus": "declined"}],
                            "start": {"date": "2026-06-09"},
                            "end": {"date": "2026-06-10"},
                        },
                    ],
                    "nextPageToken": "page-two",
                }
            )
        return FakeRequest(
            {
                "items": [
                    {
                        "id": "two",
                        "summary": "Two",
                        "start": {"date": "2026-06-10"},
                        "end": {"date": "2026-06-11"},
                    }
                ]
            }
        )


class FakeService:
    def __init__(self) -> None:
        self.resource = FakeEvents()

    def events(self) -> FakeEvents:
        return self.resource


def test_google_scope_is_read_only() -> None:
    assert SCOPES == ("https://www.googleapis.com/auth/calendar.events.readonly",)


def test_all_day_google_event_mapping() -> None:
    event = google_event_to_domain(
        {
            "id": "deadline",
            "summary": "Deadline",
            "start": {"date": "2026-06-10"},
            "end": {"date": "2026-06-11"},
        },
        "Europe/Berlin",
    )
    assert event.all_day is True
    assert event.start.isoformat() == "2026-06-10T00:00:00+02:00"


def test_google_fetch_expands_recurring_events_and_paginates() -> None:
    service = FakeService()
    events = fetch_google_events(
        service,
        calendar_id="primary",
        week_start=date(2026, 6, 8),
        timezone="Europe/Berlin",
    )
    assert [event.id for event in events] == ["one", "two"]
    assert len(service.resource.calls) == 2
    assert service.resource.calls[0]["singleEvents"] is True
    assert service.resource.calls[0]["orderBy"] == "startTime"
    assert service.resource.calls[0]["timeMin"].startswith("2026-06-08T00:00:00")
    assert service.resource.calls[0]["timeMax"].startswith("2026-06-15T00:00:00")
