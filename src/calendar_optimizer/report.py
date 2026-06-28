"""Markdown report rendering."""

from __future__ import annotations

from datetime import datetime

from calendar_optimizer.domain.calendar import (
    MoveProposal,
    OptimizationReport,
    OptimizationVariant,
    WeeklyCalendar,
)


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _format_datetime(value: datetime) -> str:
    return value.strftime("%a, %d.%m.%Y %H:%M")


def _event_name(calendar: WeeklyCalendar, event_id: str) -> str:
    event = calendar.event_by_id(event_id)
    return event.title if event else event_id


def _proposal_row(calendar: WeeklyCalendar, proposal: MoveProposal) -> str:
    event = calendar.event_by_id(proposal.event_id)
    old = (
        f"{_format_datetime(event.start)}–{event.end.strftime('%H:%M')}"
        if event
        else "Unknown"
    )
    new = f"{_format_datetime(proposal.new_start)}–{proposal.new_end.strftime('%H:%M')}"
    title = event.title if event else proposal.event_id
    return (
        f"| {_escape(title)} | {_escape(old)} | {_escape(new)} | "
        f"{proposal.flexibility.value} ({proposal.confidence:.0%}) | "
        f"{_escape(proposal.reason)} |"
    )


def _variant_section(calendar: WeeklyCalendar, variant: OptimizationVariant) -> list[str]:
    lines = [f"### {_escape(variant.name)}", "", _escape(variant.summary), ""]
    if not variant.proposals:
        lines.append("No valid moves proposed.")
        return lines
    lines.extend(
        [
            "| Event | Current | Proposal | Flexibility | Reason |",
            "|---|---|---|---|---|",
            *(_proposal_row(calendar, proposal) for proposal in variant.proposals),
        ]
    )
    return lines


def render_markdown(calendar: WeeklyCalendar, report: OptimizationReport) -> str:
    """Render a human-readable, explicitly non-mutating optimization report."""

    original_conflicts = calendar.conflict_pairs()
    recommended_calendar = calendar.apply_variant(report.recommended_variant)
    remaining_conflicts = recommended_calendar.conflict_pairs()
    lines = [
        f"# Calendar optimization: week starting {report.week_start.isoformat()}",
        "",
        "> This report contains only non-binding suggestions. "
        "**No changes were made to the calendar.**",
        "",
        f"Generated: {_format_datetime(report.generated_at)} ({calendar.timezone})",
        "",
        "## Current calendar",
        "",
        "| Day | Time | Event | Location | Type |",
        "|---|---|---|---|---|",
    ]
    for event in calendar.events:
        time_value = (
            "all-day"
            if event.all_day
            else f"{event.start.strftime('%H:%M')}–{event.end.strftime('%H:%M')}"
        )
        lines.append(
            f"| {event.start.strftime('%a, %d.%m.')} | {time_value} | "
            f"{_escape(event.title)} | {_escape(event.location or '–')} | "
            f"{'all-day' if event.all_day else 'event'} |"
        )
    if not calendar.events:
        lines.append("| – | – | No events imported | – | – |")

    lines.extend(["", "## Recommendation", ""])
    lines.extend(_variant_section(calendar, report.recommended_variant))

    lines.extend(["", "## Scheduling conflicts", ""])
    if original_conflicts:
        lines.append(
            f"- {len(original_conflicts)} overlaps were detected in the current calendar."
        )
        lines.extend(
            f"- Conflict: {_escape(_event_name(calendar, first))} overlaps with "
            f"{_escape(_event_name(calendar, second))}."
            for first, second in original_conflicts
        )
    else:
        lines.append("- No overlaps were detected in the current calendar.")
    if remaining_conflicts:
        lines.append("- **Error: The recommendation still contains scheduling conflicts.**")
    else:
        lines.append("- The recommended variant is guaranteed free of scheduling overlaps.")

    lines.extend(["", "## Human feasibility", ""])
    lines.extend(
        f"- {_escape(warning)}" for warning in report.hr_warnings
    )
    if not report.hr_warnings:
        lines.append("- No concrete warnings.")

    lines.extend(["", "## Location changes and transitions", ""])
    lines.extend(
        f"- {_escape(warning)}" for warning in report.traffic_warnings
    )
    if not report.traffic_warnings:
        lines.append("- No concrete warnings.")

    lines.extend(["", "## Human recommendations", ""])
    lines.extend(
        f"- {_escape(recommendation)}" for recommendation in report.human_recommendations
    )
    if not report.human_recommendations:
        lines.append("- No additional recommendations.")

    lines.extend(["", "## Alternative variants", ""])
    if report.alternatives:
        for alternative in report.alternatives:
            lines.extend(_variant_section(calendar, alternative))
            lines.append("")
    else:
        lines.append("No alternative valid variants.")

    lines.extend(["", "## Rejected proposals", ""])
    if report.rejected_proposals:
        lines.extend(
            f"- `{item.proposal.event_id}`: {_escape(item.reason)}"
            for item in report.rejected_proposals
        )
    else:
        lines.append("- No proposals had to be rejected.")

    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {_escape(note)}" for note in report.notes)
    lines.append("- Flexibility was estimated automatically and may be wrong.")
    lines.append("- Travel times are based on conservative heuristics, not on map data.")
    lines.append("- Google access uses only `calendar.events.readonly`.")
    return "\n".join(lines) + "\n"
