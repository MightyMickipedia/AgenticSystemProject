"""Human feasibility agent."""

from __future__ import annotations

from typing import Any

from agent_squad.utils import AgentTool

from calendar_optimizer.agents.base import (
    LLAMA_MODEL,
    OllamaToolAgent,
    OllamaToolAgentOptions,
)

SYSTEM_PROMPT = """
Du bewertest die menschliche Machbarkeit einer Kalenderwoche.
Prüfe mit den Read-only-Tools insbesondere Pausen, Mahlzeiten, mentale und körperliche Belastung,
zu lange Terminserien und unrealistische Häufungen. Nimm keine Kalenderänderungen vor.
Antworte ausschließlich als JSON: {"warnings": ["deutsche Warnung", "..."]}.
Nenne nur konkrete, aus dem Kalender ableitbare Warnungen.
""".strip()


def build_hr_planner(tools: list[AgentTool], client: Any = None) -> OllamaToolAgent:
    return OllamaToolAgent(
        OllamaToolAgentOptions(
            name="HR Planner",
            description="Bewertet Pausen, Belastung und menschliche Machbarkeit.",
            model=LLAMA_MODEL,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            client=client,
            response_format={"type": "json_object"},
            save_chat=False,
        )
    )
