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


def _proposal_row(calendar: WeeklyCalendar, proposal: MoveProposal) -> str:
    event = calendar.event_by_id(proposal.event_id)
    old = (
        f"{_format_datetime(event.start)}–{event.end.strftime('%H:%M')}"
        if event
        else "Unbekannt"
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
        lines.append("Keine validen Verschiebungen vorgeschlagen.")
        return lines
    lines.extend(
        [
            "| Termin | Bisher | Vorschlag | Verschiebbarkeit | Begründung |",
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
        f"# Kalenderoptimierung: Woche ab {report.week_start.isoformat()}",
        "",
        "> Dieser Report enthält ausschließlich unverbindliche Vorschläge. "
        "**Es wurden keine Änderungen am Kalender vorgenommen.**",
        "",
        f"Erstellt: {_format_datetime(report.generated_at)} ({calendar.timezone})",
        "",
        "## Ist-Kalender",
        "",
        "| Tag | Zeit | Termin | Ort | Typ |",
        "|---|---|---|---|---|",
    ]
    for event in calendar.events:
        time_value = (
            "ganztägig"
            if event.all_day
            else f"{event.start.strftime('%H:%M')}–{event.end.strftime('%H:%M')}"
        )
        lines.append(
            f"| {event.start.strftime('%a, %d.%m.')} | {time_value} | "
            f"{_escape(event.title)} | {_escape(event.location or '–')} | "
            f"{'ganztägig' if event.all_day else 'Termin'} |"
        )
    if not calendar.events:
        lines.append("| – | – | Keine Termine importiert | – | – |")

    lines.extend(["", "## Empfehlung", ""])
    lines.extend(_variant_section(calendar, report.recommended_variant))

    lines.extend(["", "## Terminkonflikte", ""])
    if original_conflicts:
        lines.append(
            f"- Im Ist-Kalender wurden {len(original_conflicts)} Überschneidungen erkannt."
        )
        lines.extend(
            f"- Konflikt: `{first}` überschneidet sich mit `{second}`."
            for first, second in original_conflicts
        )
    else:
        lines.append("- Im Ist-Kalender wurden keine Überschneidungen erkannt.")
    if remaining_conflicts:
        lines.append("- **Fehler: Die Empfehlung enthält weiterhin Terminkonflikte.**")
    else:
        lines.append("- Die empfohlene Variante ist garantiert frei von Terminüberschneidungen.")

    lines.extend(["", "## Menschliche Machbarkeit", ""])
    lines.extend(
        f"- {_escape(warning)}" for warning in report.hr_warnings
    )
    if not report.hr_warnings:
        lines.append("- Keine konkreten Warnungen.")

    lines.extend(["", "## Ortswechsel und Übergänge", ""])
    lines.extend(
        f"- {_escape(warning)}" for warning in report.traffic_warnings
    )
    if not report.traffic_warnings:
        lines.append("- Keine konkreten Warnungen.")

    lines.extend(["", "## Alternative Varianten", ""])
    if report.alternatives:
        for alternative in report.alternatives:
            lines.extend(_variant_section(calendar, alternative))
            lines.append("")
    else:
        lines.append("Keine alternativen validen Varianten.")

    lines.extend(["", "## Verworfene Vorschläge", ""])
    if report.rejected_proposals:
        lines.extend(
            f"- `{item.proposal.event_id}`: {_escape(item.reason)}"
            for item in report.rejected_proposals
        )
    else:
        lines.append("- Keine Vorschläge mussten verworfen werden.")

    lines.extend(["", "## Hinweise", ""])
    lines.extend(f"- {_escape(note)}" for note in report.notes)
    lines.append("- Verschiebbarkeit wurde automatisch geschätzt und kann falsch sein.")
    lines.append("- Reisezeiten basieren auf konservativen Heuristiken, nicht auf Kartendaten.")
    lines.append("- Der Google-Zugriff verwendet ausschließlich `calendar.events.readonly`.")
    return "\n".join(lines) + "\n"
