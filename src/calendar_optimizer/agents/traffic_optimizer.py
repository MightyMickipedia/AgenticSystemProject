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
Du bewertest Ortswechsel und Übergangspuffer einer Kalenderwoche.
Nutze die bereitgestellten Read-only-Tools und keine externen Maps-Dienste.
Die Heuristik ist konservativ: unbekannter Ort 15 Minuten, physisch/virtuell 20 Minuten,
verschiedene physische Orte 30 Minuten. Nimm keine Kalenderänderungen vor.
Antworte ausschließlich als JSON: {"warnings": ["deutsche Warnung", "..."]}.
""".strip()


def build_traffic_optimizer(tools: list[AgentTool], client: Any = None) -> OllamaToolAgent:
    return OllamaToolAgent(
        OllamaToolAgentOptions(
            name="Traffic Optimizer",
            description="Bewertet Übergangs- und Reisezeitpuffer heuristisch.",
            model=LLAMA_MODEL,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            client=client,
            response_format={"type": "json_object"},
            save_chat=False,
        )
    )
