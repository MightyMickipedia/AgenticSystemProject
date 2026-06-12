"""Command-line entrypoint for the read-only calendar optimizer."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from calendar_optimizer.agents.orchestrator import build_agent_squad
from calendar_optimizer.domain.calendar import WeeklyCalendar
from calendar_optimizer.integrations.google_calendar import (
    load_google_calendar,
    load_json_calendar,
)
from calendar_optimizer.integrations.snapshot import (
    load_calendar_snapshot,
    save_calendar_snapshot,
)
from calendar_optimizer.report import render_markdown

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parse_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Erwartetes Zeitformat: HH:MM") from error


def _parse_week_start(value: str | None, timezone: str) -> date:
    if value:
        selected = date.fromisoformat(value)
        if selected.weekday() != 0:
            raise ValueError("--week-start muss ein Montag sein.")
        return selected
    today = datetime.now(ZoneInfo(timezone)).date()
    return today - timedelta(days=today.weekday())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Optimiert eine Kalenderwoche beratend mit lokalen Ollama-Agenten."
    )
    parser.add_argument("--source", choices=("google", "json", "snapshot"), default="google")
    parser.add_argument("--input-json", type=Path)
    parser.add_argument("--calendar-id", default="primary")
    parser.add_argument("--week-start", help="Montag im ISO-Format, z. B. 2026-06-08")
    parser.add_argument(
        "--timezone",
        default=os.environ.get("CALENDAR_TIMEZONE", "Europe/Berlin"),
        help="IANA-Zeitzone; Standard: CALENDAR_TIMEZONE oder Europe/Berlin",
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=PROJECT_ROOT / "credentials.json",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=PROJECT_ROOT / ".secrets" / "google-token.json",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=PROJECT_ROOT / "snapshots" / "latest.json",
    )
    parser.add_argument("--day-start", type=_parse_time, default=time(7, 0))
    parser.add_argument("--day-end", type=_parse_time, default=time(22, 0))
    parser.add_argument("--output", type=Path)
    return parser


def load_calendar_source(args: argparse.Namespace, week_start: date) -> WeeklyCalendar:
    """Load the configured source and use a snapshot when Google import fails."""

    print(f"[FLOW] Kalenderquelle '{args.source}' wird geladen", flush=True)
    if args.source == "json":
        if args.input_json is None:
            raise ValueError("--input-json ist für --source json erforderlich.")
        return load_json_calendar(
            args.input_json,
            week_start,
            args.timezone,
            args.day_start,
            args.day_end,
        )
    if args.source == "snapshot":
        calendar = load_calendar_snapshot(args.snapshot)
        print(f"[FLOW] Kalender-Snapshot geladen: {args.snapshot}", flush=True)
        return calendar

    try:
        calendar = load_google_calendar(
            calendar_id=args.calendar_id,
            week_start=week_start,
            timezone=args.timezone,
            credentials_path=args.credentials,
            token_path=args.token,
            day_start=args.day_start,
            day_end=args.day_end,
        )
    except Exception as error:
        if not args.snapshot.exists():
            raise RuntimeError(
                f"Google-Import fehlgeschlagen und kein Snapshot vorhanden: {error}"
            ) from error
        print(f"[FLOW] Google-Import fehlgeschlagen: {error}", flush=True)
        print(
            f"[FLOW] Authentifizierungs-Fallback -> Snapshot: {args.snapshot}",
            flush=True,
        )
        return load_calendar_snapshot(args.snapshot)

    if args.snapshot.exists():
        print(
            f"[FLOW] Bestehender Kalender-Snapshot bleibt unverändert: {args.snapshot}",
            flush=True,
        )
    else:
        save_calendar_snapshot(calendar, args.snapshot)
        print(f"[FLOW] Kalender-Snapshot einmalig gespeichert: {args.snapshot}", flush=True)
    return calendar


async def optimize(args: argparse.Namespace) -> Path:
    requested_week_start = _parse_week_start(args.week_start, args.timezone)
    calendar = load_calendar_source(args, requested_week_start)

    week_start = calendar.week_start
    print(
        f"[FLOW] Kalender geladen: {len(calendar.events)} Termine, "
        f"Woche ab {calendar.week_start.isoformat()}",
        flush=True,
    )
    squad, orchestrator = build_agent_squad(calendar)
    await squad.route_request(
        user_input="Optimiere diese Kalenderwoche ausgewogen.",
        user_id="local-user",
        session_id=f"week-{week_start.isoformat()}",
    )
    if orchestrator.last_report is None:
        raise RuntimeError(
            "Die Optimierung ist fehlgeschlagen. Prüfe, ob Ollama läuft und beide Modelle vorhanden sind."
        )

    output = args.output or PROJECT_ROOT / "reports" / f"week-{week_start.isoformat()}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_markdown(calendar, orchestrator.last_report),
        encoding="utf-8",
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = asyncio.run(optimize(args))
    except Exception as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    print(f"Report erstellt: {output.resolve()}")
    print("Es wurden keine Änderungen am Kalender vorgenommen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
