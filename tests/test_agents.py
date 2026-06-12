from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from agent_squad.types import ConversationMessage
from agent_squad.utils import AgentTool

from calendar_optimizer.agents.base import (
    LLAMA_MODEL,
    OllamaToolAgent,
    OllamaToolAgentOptions,
)
from calendar_optimizer.agents.orchestrator import build_agent_squad
from calendar_optimizer.domain.calendar import CalendarEvent, WeeklyCalendar


def completion(content: str = "", tool_calls: list[Any] | None = None) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=tool_calls or [])
            )
        ]
    )


class FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: str):
        self.id = call_id
        self.function = SimpleNamespace(name=name, arguments=arguments)

    def model_dump(self, exclude_none: bool = True) -> dict[str, Any]:
        del exclude_none
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.function.name,
                "arguments": self.function.arguments,
            },
        }


class QueueCompletions:
    def __init__(self, responses: list[Any]):
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        return self.responses.pop(0)


class QueueClient:
    def __init__(self, responses: list[Any]):
        self.chat = SimpleNamespace(completions=QueueCompletions(responses))


class RoutedCompletions:
    async def create(self, **kwargs: Any) -> Any:
        system = kwargs["messages"][0]["content"]
        if "Schedule Manager" in system:
            payload = {
                "variants": [
                    {
                        "name": "Ausgewogen",
                        "summary": "Ein Fokusblock wird verschoben.",
                        "proposals": [
                            {
                                "event_id": "meeting",
                                "new_start": "2026-06-08T13:00:00+02:00",
                                "new_end": "2026-06-08T14:00:00+02:00",
                                "reason": "Mehr Fokus am Vormittag",
                                "flexibility": "uncertain",
                                "confidence": 0.6,
                            }
                        ],
                    },
                    {"name": "Ruhig", "summary": "Status quo", "proposals": []},
                    {
                        "name": "Ungültig",
                        "summary": "Kollision",
                        "proposals": [
                            {
                                "event_id": "meeting",
                                "new_start": "2026-06-08T11:30:00+02:00",
                                "new_end": "2026-06-08T12:30:00+02:00",
                                "reason": "Kollidiert",
                                "flexibility": "uncertain",
                                "confidence": 0.4,
                            }
                        ],
                    },
                ]
            }
        elif "menschliche Machbarkeit" in system:
            payload = {"warnings": ["Mittagspause prüfen."]}
        elif "Ortswechsel" in system:
            payload = {"warnings": ["Übergang zwischen Präsenz und Online ist knapp."]}
        else:
            payload = {
                "recommended_variant": "Ausgewogen",
                "notes": ["Ausgewogene Variante gewählt."],
            }
        return completion(json.dumps(payload, ensure_ascii=False))


class RoutedClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=RoutedCompletions())


def build_agent(client: Any, tools: list[AgentTool] | None = None, model: str = LLAMA_MODEL):
    return OllamaToolAgent(
        OllamaToolAgentOptions(
            name="Test Agent",
            description="Test",
            model=model,
            system_prompt="Test",
            tools=tools or [],
            client=client,
        )
    )


def test_foreign_model_is_rejected() -> None:
    with pytest.raises(ValueError, match="nicht erlaubt"):
        build_agent(QueueClient([]), model="foreign-model")


def test_ollama_agent_executes_tool_call(capsys: pytest.CaptureFixture[str]) -> None:
    def echo(value: str) -> str:
        return value

    tool = AgentTool(name="echo", func=echo)
    client = QueueClient(
        [
            completion(tool_calls=[FakeToolCall("call-1", "echo", '{"value":"ok"}')]),
            completion('{"result":"ok"}'),
        ]
    )
    response = asyncio.run(
        build_agent(client, [tool]).process_request("Test", "u", "s", [])
    )
    assert isinstance(response, ConversationMessage)
    assert response.content[0]["text"] == '{"result":"ok"}'
    messages = client.chat.completions.requests[1]["messages"]
    assert messages[-1] == {"role": "tool", "tool_call_id": "call-1", "content": "ok"}
    output = capsys.readouterr().out
    assert "[FLOW] Test Agent arbeitet mit llama3.1:8b" in output
    assert "[FLOW] Test Agent -> Tool echo:" in output
    assert "[FLOW] Tool echo -> Test Agent: Ergebnis erhalten" in output
    assert "[FLOW] Test Agent hat die Arbeit abgeschlossen" in output


def test_full_agent_squad_flow_validates_proposals(
    calendar: WeeklyCalendar,
    capsys: pytest.CaptureFixture[str],
) -> None:
    squad, orchestrator = build_agent_squad(calendar, client=RoutedClient())
    response = asyncio.run(squad.route_request("Optimiere", "user", "session"))
    assert response.metadata.agent_name == "Calendar Orchestrator"
    assert orchestrator.last_report is not None
    assert orchestrator.last_report.recommended_variant.name == "Ausgewogen"
    assert len(orchestrator.last_report.rejected_proposals) == 1
    assert orchestrator.last_report.hr_warnings == ("Mittagspause prüfen.",)
    output = capsys.readouterr().out
    assert "[FLOW] Agent Squad -> Calendar Orchestrator: Anfrage geroutet" in output
    assert "Woche parallel analysieren" in output
    assert "Schedule Manager, HR Planner, Traffic Optimizer -> Calendar Orchestrator" in output
    assert "1 Vorschläge verworfen" in output
    assert "Empfehlung 'Ausgewogen' gewählt" in output


def test_orchestrator_falls_back_to_conflict_free_variant() -> None:
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
    squad, orchestrator = build_agent_squad(calendar, client=RoutedClient())
    asyncio.run(squad.route_request("Optimiere", "user", "conflict-session"))
    assert orchestrator.last_report is not None
    recommendation = orchestrator.last_report.recommended_variant
    assert recommendation.name == "Garantierte Konfliktauflösung"
    assert calendar.apply_variant(recommendation).conflict_pairs() == ()
