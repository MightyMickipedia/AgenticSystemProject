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
You assess the human feasibility of a calendar week.
Using the read-only tools, check in particular breaks, meals, mental and physical load,
overly long back-to-back series and unrealistic clustering. Do not make any calendar changes.
Respond only as JSON: {"warnings": ["English warning", "..."]}.
Name only concrete warnings that can be derived from the calendar.
""".strip()


def build_hr_planner(tools: list[AgentTool], client: Any = None) -> OllamaToolAgent:
    return OllamaToolAgent(
        OllamaToolAgentOptions(
            name="HR Planner",
            description="Assesses breaks, workload and human feasibility.",
            model=LLAMA_MODEL,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            client=client,
            response_format={"type": "json_object"},
            save_chat=False,
        )
    )
