"""Heuristic transition and travel feasibility agent."""

from __future__ import annotations

from typing import Any

from agent_squad.utils import AgentTool

from calendar_optimizer.agents.base import (
    LLAMA_MODEL,
    OllamaToolAgent,
    OllamaToolAgentOptions,
)

SYSTEM_PROMPT = """
You assess location changes and transition buffers of a calendar week.
Use the provided read-only tools and no external map services.
The heuristic is conservative: unknown location 15 minutes, physical/virtual 20 minutes,
different physical locations 30 minutes. Do not make any calendar changes.
Respond only as JSON: {"warnings": ["English warning", "..."]}.
""".strip()


def build_traffic_optimizer(tools: list[AgentTool], client: Any = None) -> OllamaToolAgent:
    return OllamaToolAgent(
        OllamaToolAgentOptions(
            name="Traffic Optimizer",
            description="Heuristically assesses transition and travel-time buffers.",
            model=LLAMA_MODEL,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            client=client,
            response_format={"type": "json_object"},
            save_chat=False,
        )
    )
