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
from calendar_optimizer.agents.flow import flow
from calendar_optimizer.agents.hr_planner import build_hr_planner
from calendar_optimizer.agents.schedule_manager import build_schedule_manager
from calendar_optimizer.agents.traffic_optimizer import build_traffic_optimizer
from calendar_optimizer.domain.calendar import (
    CalendarEvent,
    OptimizationReport,
    OptimizationVariant,
    RejectedProposal,
    WeeklyCalendar,
)
from calendar_optimizer.tools.calendar_tools import analyze_transitions, build_calendar_tools

ORCHESTRATOR_PROMPT = """
You coordinate a purely advisory calendar optimizer. You receive three validated variants
along with warnings about human feasibility and location changes. Choose the most balanced variant:
focus blocks, breaks, meals, workload and transitions all count together.
Respond only as JSON:
{
  "recommended_variant": "exact variant name",
  "notes": ["English reasoning"]
}.
You must not invent any new moves.
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    return json.loads(stripped)


def _message_text(message: ConversationMessage) -> str:
    return message.content[0].get("text", "") if message.content else ""


def _string_list_from_payload(
    payload: dict[str, Any],
    keys: tuple[str, ...],
) -> tuple[str, ...]:
    raw: list[Any] = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            raw.extend(value)
    return tuple(text for text in (str(item).strip() for item in raw) if text)


def _warnings_from_message(message: ConversationMessage) -> tuple[str, ...]:
    try:
        payload = _extract_json(_message_text(message))
    except (json.JSONDecodeError, TypeError, ValueError):
        return (f"Agent response could not be parsed into structured form: {_message_text(message)}",)
    # Smaller local models occasionally label the list with a domain-specific
    # key instead of the requested "warnings", so accept the common variants
    # and drop empty/whitespace entries.
    return _string_list_from_payload(
        payload,
        ("warnings", "hr_warnings", "traffic_warnings"),
    )


WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _event_label(calendar: WeeklyCalendar, event: CalendarEvent) -> str:
    start = event.start.astimezone(calendar.zone)
    end = event.end.astimezone(calendar.zone)
    day = WEEKDAY_NAMES[start.weekday()]
    return f"'{event.title}' ({day}, {start:%H:%M}-{end:%H:%M})"


def _humanize_event_ids(calendar: WeeklyCalendar, text: str) -> str:
    humanized = text
    events = sorted(calendar.events, key=lambda event: len(event.id), reverse=True)
    for event in events:
        if not event.id:
            continue
        humanized = re.sub(
            rf"(?<![\w-]){re.escape(event.id)}(?![\w-])",
            _event_label(calendar, event),
            humanized,
        )
    return humanized


def _format_transition_warning(
    calendar: WeeklyCalendar,
    item: dict[str, Any],
) -> str:
    first = calendar.event_by_id(str(item["from_event"]))
    second = calendar.event_by_id(str(item["to_event"]))
    available = int(item["available_minutes"])
    required = int(item["recommended_minutes"])
    confidence = str(item["confidence"])
    if first is None or second is None:
        return (
            f"Between {item['from_event']} and {item['to_event']} there are "
            f"{available} instead of the recommended {required} minutes available "
            f"(confidence: {confidence})."
        )

    first_label = _event_label(calendar, first)
    second_label = _event_label(calendar, second)
    if available < 0:
        return (
            f"{first_label} overlaps with {second_label} by {abs(available)} minutes. "
            "This is a scheduling conflict, so one of the events should move before "
            "travel time is considered."
        )
    if available == 0:
        buffer_text = "no buffer"
    else:
        buffer_text = f"only {available} minutes"

    location_text = ""
    if first.location or second.location:
        location_text = (
            f" Locations: {first.location or 'not specified'} -> "
            f"{second.location or 'not specified'}."
        )
    return (
        f"There is {buffer_text} between {first_label} and {second_label}; "
        f"aim for about {required} minutes of transition time.{location_text} "
        f"Confidence: {confidence}."
    )


def _build_human_recommendations(
    calendar: WeeklyCalendar,
    recommended: OptimizationVariant,
    hr_warnings: tuple[str, ...],
    transition_issues: tuple[dict[str, Any], ...],
) -> tuple[str, ...]:
    recommendations: list[str] = []
    move_count = len(recommended.proposals)
    if move_count:
        plural = "" if move_count == 1 else "s"
        recommendations.append(
            f"Use '{recommended.name}' as the starting plan. It proposes "
            f"{move_count} calendar move{plural}; confirm them with the affected people "
            "before making real calendar changes."
        )
    else:
        recommendations.append(
            f"Keep '{recommended.name}' for now; no validated move is safer than forcing "
            "a weak change."
        )

    for first_id, second_id in calendar.conflict_pairs():
        first = calendar.event_by_id(first_id)
        second = calendar.event_by_id(second_id)
        if first is None or second is None:
            continue
        overlap_start = max(first.start, second.start)
        overlap_end = min(first.end, second.end)
        overlap_minutes = int((overlap_end - overlap_start).total_seconds() // 60)
        recommendations.append(
            f"Resolve the overlap between {_event_label(calendar, first)} and "
            f"{_event_label(calendar, second)}. They conflict for {overlap_minutes} "
            "minutes, so keep the higher-priority event in place and move the other one."
        )

    for item in transition_issues:
        if int(item["available_minutes"]) < 0:
            continue
        first = calendar.event_by_id(str(item["from_event"]))
        second = calendar.event_by_id(str(item["to_event"]))
        if first is None or second is None:
            continue
        available = int(item["available_minutes"])
        required = int(item["recommended_minutes"])
        deficit = required - available
        if available == 0:
            current_buffer = "no usable buffer"
        else:
            current_buffer = f"{available} minutes of buffer"
        recommendations.append(
            f"Add about {deficit} more minutes between {_event_label(calendar, first)} "
            f"and {_event_label(calendar, second)}. Right now there is {current_buffer}, "
            f"but this transition needs about {required} minutes."
        )

    for warning in hr_warnings:
        recommendations.append(
            "Review this human-feasibility risk before applying the plan: "
            f"{_humanize_event_ids(calendar, warning)}"
        )

    if len(recommendations) == 1:
        recommendations.append(
            "No feasibility or travel risks were flagged, so the recommendation can be "
            "treated as low-friction if priorities stay unchanged."
        )

    return tuple(dict.fromkeys(recommendations))


class DeterministicOrchestratorClassifier(Classifier):
    """Always selects the only public entrypoint: the orchestrator."""

    async def process_request(
        self,
        input_text: str,
        chat_history: list[ConversationMessage],
    ) -> ClassifierResult:
        del input_text, chat_history
        selected = next(iter(self.agents.values()), None)
        if selected:
            flow(f"Agent Squad -> {selected.name}: request routed")
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
                description="Coordinates and validates the weekly optimization.",
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
        flow(f"{self.name} is working")

        # Fast path: an empty week needs no LLM calls. Running the specialists
        # here only wastes minutes and invites contradictory hallucinated
        # warnings, so return a deterministic "nothing to do" report instead.
        if not self.calendar.events:
            flow(f"{self.name}: No events this week – no optimization needed")
            empty_variant = OptimizationVariant(
                name="Status quo",
                summary="No events in this calendar week.",
            )
            report = OptimizationReport(
                week_start=self.calendar.week_start,
                generated_at=datetime.now(self.calendar.zone),
                recommended_variant=empty_variant,
                alternatives=(),
                hr_warnings=("No events in this calendar week.",),
                traffic_warnings=(),
                human_recommendations=(
                    "No action is needed for this week because there are no imported events.",
                ),
                rejected_proposals=(),
                notes=(
                    "The selected week contains no events; no models were "
                    "called.",
                ),
            )
            self.last_report = report
            flow(f"{self.name} finished its work")
            return ConversationMessage(
                role=ParticipantRole.ASSISTANT.value,
                content=[{"text": report.model_dump_json()}],
            )

        task = (
            "Analyze the calendar week starting "
            f"{self.calendar.week_start.isoformat()} in a balanced and complete way."
        )
        flow(
            f"{self.name} -> Schedule Manager, HR Planner, Traffic Optimizer: "
            "analyze the week in parallel"
        )
        schedule_response, hr_response, traffic_response = await asyncio.gather(
            self.schedule_manager.process_request(task, user_id, session_id, []),
            self.hr_planner.process_request(task, user_id, session_id, []),
            self.traffic_optimizer.process_request(task, user_id, session_id, []),
        )
        flow(f"Schedule Manager, HR Planner, Traffic Optimizer -> {self.name}: results received")

        try:
            variants = self._parse_variants(schedule_response)
        except (json.JSONDecodeError, TypeError, ValueError):
            variants = ()
        if not variants:
            variants = (
                OptimizationVariant(
                    name="Status quo",
                    summary="No valid rescheduling variant was produced.",
                ),
            )

        valid_variants: list[OptimizationVariant] = []
        rejected: list[RejectedProposal] = []
        discarded_conflicting_variants: list[str] = []
        for variant in variants:
            valid, variant_rejected = self.calendar.validate_variant(variant)
            rejected.extend(variant_rejected)
            resulting_calendar = self.calendar.apply_variant(valid)
            if resulting_calendar.conflict_pairs():
                discarded_conflicting_variants.append(valid.name)
                flow(
                    f"{self.name}: variant '{valid.name}' discarded, "
                    "because scheduling conflicts remain"
                )
                continue
            valid_variants.append(valid)

        used_conflict_fallback = False
        if not valid_variants:
            flow(
                f"{self.name}: agents produced no conflict-free variant; "
                "generating deterministic conflict-resolution variants"
            )
            fallback_variants = self.calendar.build_conflict_resolution_variants()
            if not fallback_variants:
                fallback_variants = (self.calendar.build_conflict_resolution_variant(),)
            if any(
                self.calendar.apply_variant(variant).conflict_pairs()
                for variant in fallback_variants
            ):
                raise RuntimeError("A conflict-free recommendation could not be guaranteed.")
            valid_variants.extend(fallback_variants)
            used_conflict_fallback = True
        flow(
            f"{self.name}: {len(valid_variants)} variants validated, "
            f"{len(rejected)} proposals discarded"
        )

        transition_issues = tuple(analyze_transitions(self.calendar))
        deterministic_traffic = tuple(
            _format_transition_warning(self.calendar, item)
            for item in transition_issues
        )
        hr_warnings = tuple(
            dict.fromkeys(
                _humanize_event_ids(self.calendar, warning)
                for warning in _warnings_from_message(hr_response)
            )
        )
        traffic_warnings = tuple(
            dict.fromkeys(
                (
                    *deterministic_traffic,
                    *(
                        _humanize_event_ids(self.calendar, warning)
                        for warning in _warnings_from_message(traffic_response)
                    ),
                )
            )
        )

        selection_input = json.dumps(
            {
                "variants": [variant.model_dump(mode="json") for variant in valid_variants],
                "hr_warnings": hr_warnings,
                "traffic_warnings": traffic_warnings,
            },
            ensure_ascii=False,
        )
        system_notes: list[str] = []
        if discarded_conflicting_variants:
            system_notes.append(
                "Variants with remaining scheduling conflicts were discarded: "
                + ", ".join(discarded_conflicting_variants)
                + "."
            )
        if used_conflict_fallback:
            system_notes.append(
                "The recommendation was generated deterministically because no agent variant "
                "resolved all existing conflicts."
            )
        notes: tuple[str, ...] = ()
        selected_name = valid_variants[0].name
        try:
            flow(f"{self.name} -> {self.lead_agent.name}: select the best variant")
            selection = await self.lead_agent.process_request(
                selection_input, user_id, session_id, []
            )
            flow(f"{self.lead_agent.name} -> {self.name}: selection received")
            selection_payload = _extract_json(_message_text(selection))
            selected_name = str(selection_payload.get("recommended_variant", selected_name))
            notes = tuple(
                (*system_notes, *(str(item) for item in selection_payload.get("notes", [])))
            )
        except (json.JSONDecodeError, TypeError, ValueError, RuntimeError):
            notes = tuple(
                (*system_notes, "The first valid variant was chosen as a deterministic fallback.")
            )

        recommended = next(
            (variant for variant in valid_variants if variant.name == selected_name),
            valid_variants[0],
        )
        if self.calendar.apply_variant(recommended).conflict_pairs():
            raise RuntimeError("A conflict-free recommendation could not be guaranteed.")
        alternatives = tuple(
            variant for variant in valid_variants if variant.name != recommended.name
        )
        human_recommendations = _build_human_recommendations(
            self.calendar,
            recommended,
            hr_warnings,
            transition_issues,
        )
        report = OptimizationReport(
            week_start=self.calendar.week_start,
            generated_at=datetime.now(self.calendar.zone),
            recommended_variant=recommended,
            alternatives=alternatives,
            hr_warnings=hr_warnings,
            traffic_warnings=traffic_warnings,
            human_recommendations=human_recommendations,
            rejected_proposals=tuple(rejected),
            notes=notes,
        )
        self.last_report = report
        flow(f"{self.name}: recommendation '{recommended.name}' selected")
        flow(f"{self.name} finished its work")
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
                description="Selects the most balanced validated calendar option.",
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
