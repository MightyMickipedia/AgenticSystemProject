"""Programmatic, validated orchestration through Agent Squad."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from typing import Any, Optional

from agent_squad.agents import Agent, AgentOptions
from agent_squad.classifiers import Classifier, ClassifierResult
from agent_squad.orchestrator import AgentSquad
from agent_squad.types import ConversationMessage, ParticipantRole

from calendar_optimizer.agents.base import (
    LLAMA_MODEL,
    OllamaToolAgent,
    OllamaToolAgentOptions,
)
from calendar_optimizer.agents.hr_planner import build_hr_planner
from calendar_optimizer.agents.schedule_manager import build_schedule_manager
from calendar_optimizer.agents.traffic_optimizer import build_traffic_optimizer
from calendar_optimizer.domain.calendar import (
    OptimizationReport,
    OptimizationVariant,
    RejectedProposal,
    WeeklyCalendar,
)
from calendar_optimizer.tools.calendar_tools import analyze_transitions, build_calendar_tools

ORCHESTRATOR_PROMPT = """
Du koordinierst einen rein beratenden Kalenderoptimierer. Du erhältst drei validierte Varianten
sowie Warnungen zur menschlichen Machbarkeit und zu Ortswechseln. Wähle die ausgewogenste Variante:
Fokusblöcke, Pausen, Mahlzeiten, Belastung und Übergänge zählen gemeinsam.
Antworte ausschließlich als JSON:
{"recommended_variant": "exakter Variantenname", "notes": ["deutsche Begründung"]}.
Du darfst keine neuen Verschiebungen erfinden.
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    return json.loads(stripped)


def _message_text(message: ConversationMessage) -> str:
    return message.content[0].get("text", "") if message.content else ""


def _warnings_from_message(message: ConversationMessage) -> tuple[str, ...]:
    try:
        payload = _extract_json(_message_text(message))
        return tuple(str(item) for item in payload.get("warnings", []))
    except (json.JSONDecodeError, TypeError, ValueError):
        return (f"Agentenantwort konnte nicht strukturiert ausgewertet werden: {_message_text(message)}",)


class DeterministicOrchestratorClassifier(Classifier):
    """Always selects the only public entrypoint: the orchestrator."""

    async def process_request(
        self,
        input_text: str,
        chat_history: list[ConversationMessage],
    ) -> ClassifierResult:
        del input_text, chat_history
        selected = next(iter(self.agents.values()), None)
        return ClassifierResult(selected_agent=selected, confidence=1.0)


class CalendarOrchestratorAgent(Agent):
    """Coordinates specialist agents and rejects unsafe proposals."""

    def __init__(
        self,
        calendar: WeeklyCalendar,
        schedule_manager: OllamaToolAgent,
        hr_planner: OllamaToolAgent,
        traffic_optimizer: OllamaToolAgent,
        lead_agent: OllamaToolAgent,
    ):
        super().__init__(
            AgentOptions(
                name="Calendar Orchestrator",
                description="Koordiniert und validiert die Wochenoptimierung.",
                save_chat=False,
            )
        )
        self.calendar = calendar
        self.schedule_manager = schedule_manager
        self.hr_planner = hr_planner
        self.traffic_optimizer = traffic_optimizer
        self.lead_agent = lead_agent
        self.last_report: OptimizationReport | None = None

    def _parse_variants(
        self, response: ConversationMessage
    ) -> tuple[OptimizationVariant, ...]:
        payload = _extract_json(_message_text(response))
        return tuple(
            OptimizationVariant.model_validate(item)
            for item in payload.get("variants", [])
        )

    async def process_request(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
        chat_history: list[ConversationMessage],
        additional_params: Optional[dict[str, Any]] = None,
    ) -> ConversationMessage:
        del input_text, chat_history, additional_params
        task = (
            "Analysiere die Kalenderwoche ab "
            f"{self.calendar.week_start.isoformat()} ausgewogen und vollständig."
        )
        schedule_response, hr_response, traffic_response = await asyncio.gather(
            self.schedule_manager.process_request(task, user_id, session_id, []),
            self.hr_planner.process_request(task, user_id, session_id, []),
            self.traffic_optimizer.process_request(task, user_id, session_id, []),
        )

        try:
            variants = self._parse_variants(schedule_response)
        except (json.JSONDecodeError, TypeError, ValueError):
            variants = ()
        if not variants:
            variants = (
                OptimizationVariant(
                    name="Status quo",
                    summary="Keine valide Umplanungsvariante wurde erzeugt.",
                ),
            )

        valid_variants: list[OptimizationVariant] = []
        rejected: list[RejectedProposal] = []
        for variant in variants:
            valid, variant_rejected = self.calendar.validate_variant(variant)
            valid_variants.append(valid)
            rejected.extend(variant_rejected)

        deterministic_traffic = tuple(
            (
                f"Zwischen {item['from_event']} und {item['to_event']} stehen "
                f"{item['available_minutes']} statt empfohlener "
                f"{item['recommended_minutes']} Minuten zur Verfügung "
                f"(Konfidenz: {item['confidence']})."
            )
            for item in analyze_transitions(self.calendar)
        )
        hr_warnings = _warnings_from_message(hr_response)
        traffic_warnings = tuple(
            dict.fromkeys((*deterministic_traffic, *_warnings_from_message(traffic_response)))
        )

        selection_input = json.dumps(
            {
                "variants": [variant.model_dump(mode="json") for variant in valid_variants],
                "hr_warnings": hr_warnings,
                "traffic_warnings": traffic_warnings,
            },
            ensure_ascii=False,
        )
        notes: tuple[str, ...] = ()
        selected_name = valid_variants[0].name
        try:
            selection = await self.lead_agent.process_request(
                selection_input, user_id, session_id, []
            )
            selection_payload = _extract_json(_message_text(selection))
            selected_name = str(selection_payload.get("recommended_variant", selected_name))
            notes = tuple(str(item) for item in selection_payload.get("notes", []))
        except (json.JSONDecodeError, TypeError, ValueError, RuntimeError):
            notes = ("Die erste valide Variante wurde als deterministischer Fallback gewählt.",)

        recommended = next(
            (variant for variant in valid_variants if variant.name == selected_name),
            valid_variants[0],
        )
        alternatives = tuple(
            variant for variant in valid_variants if variant.name != recommended.name
        )
        report = OptimizationReport(
            week_start=self.calendar.week_start,
            generated_at=datetime.now(self.calendar.zone),
            recommended_variant=recommended,
            alternatives=alternatives,
            hr_warnings=hr_warnings,
            traffic_warnings=traffic_warnings,
            rejected_proposals=tuple(rejected),
            notes=notes,
        )
        self.last_report = report
        return ConversationMessage(
            role=ParticipantRole.ASSISTANT.value,
            content=[{"text": report.model_dump_json()}],
        )


def build_agent_squad(
    calendar: WeeklyCalendar,
    client: Any = None,
) -> tuple[AgentSquad, CalendarOrchestratorAgent]:
    """Build the local specialist team behind one Agent Squad entrypoint."""

    tools = build_calendar_tools(calendar)
    orchestrator = CalendarOrchestratorAgent(
        calendar=calendar,
        schedule_manager=build_schedule_manager(tools, client),
        hr_planner=build_hr_planner(tools, client),
        traffic_optimizer=build_traffic_optimizer(tools, client),
        lead_agent=OllamaToolAgent(
            OllamaToolAgentOptions(
                name="Lead Calendar Optimizer",
                description="Wählt die ausgewogenste validierte Kalenderoption.",
                model=LLAMA_MODEL,
                system_prompt=ORCHESTRATOR_PROMPT,
                tools=tools,
                client=client,
                response_format={"type": "json_object"},
                save_chat=False,
            )
        ),
    )
    squad = AgentSquad(
        classifier=DeterministicOrchestratorClassifier(),
        default_agent=orchestrator,
    )
    squad.add_agent(orchestrator)
    return squad, orchestrator
