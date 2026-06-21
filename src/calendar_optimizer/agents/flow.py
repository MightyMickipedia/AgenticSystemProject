"""Concise console tracing for the agent workflow."""

from __future__ import annotations

import contextvars
from typing import Callable

_flow_handlers: contextvars.ContextVar[list[Callable[[str], None]]] = contextvars.ContextVar(
    "_flow_handlers", default=[]
)


def flow(message: str) -> None:
    """Print one immediately visible workflow event."""

    print(f"[FLOW] {message}", flush=True)
    for handler in _flow_handlers.get():
        handler(message)


def add_flow_handler(handler: Callable[[str], None]) -> None:
    handlers = _flow_handlers.get()
    _flow_handlers.set([*handlers, handler])


def remove_flow_handler(handler: Callable[[str], None]) -> None:
    handlers = _flow_handlers.get()
    _flow_handlers.set([h for h in handlers if h is not handler])


def summarize_arguments(arguments: str, maximum: int = 120) -> str:
    """Keep tool-call arguments readable without flooding the console."""

    compact = " ".join(arguments.split())
    if len(compact) <= maximum:
        return compact
    return f"{compact[:maximum - 3]}..."
