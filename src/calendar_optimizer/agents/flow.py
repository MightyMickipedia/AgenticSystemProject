"""Concise console tracing for the agent workflow."""

from __future__ import annotations


def flow(message: str) -> None:
    """Print one immediately visible workflow event."""

    print(f"[FLOW] {message}", flush=True)


def summarize_arguments(arguments: str, maximum: int = 120) -> str:
    """Keep tool-call arguments readable without flooding the console."""

    compact = " ".join(arguments.split())
    if len(compact) <= maximum:
        return compact
    return f"{compact[:maximum - 3]}..."
