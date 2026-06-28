"""Schedule permutation agent."""

from __future__ import annotations

from typing import Any

from agent_squad.utils import AgentTool

from calendar_optimizer.agents.base import (
    QWEN_MODEL,
    OllamaToolAgent,
    OllamaToolAgentOptions,
)

SYSTEM_PROMPT = """
You are the Schedule Manager of a purely advisory calendar optimizer.
Use only the read-only tools to understand the week.
Based on title, description, location and time, carefully estimate whether events can be moved.
All-day events must never be moved. Never change an event's duration.
Call list_conflicts. Every variant you produce must resolve all existing scheduling conflicts
and must not create any new conflicts.
Produce exactly three balanced variants and respond only as JSON:
{
  "variants": [
    {
      "name": "Short name",
      "summary": "English summary",
      "proposals": [
        {
          "event_id": "existing ID",
          "new_start": "ISO time with offset",
          "new_end": "ISO time with offset",
          "reason": "English reason",
          "flexibility": "fixed|likely_fixed|uncertain|likely_flexible|flexible",
          "confidence": 0.0
        }
      ]
    }
  ]
}
A variant may be empty if no sensible and plausible move exists.
""".strip()


def build_schedule_manager(tools: list[AgentTool], client: Any = None) -> OllamaToolAgent:
    return OllamaToolAgent(
        OllamaToolAgentOptions(
            name="Schedule Manager",
            description="Creates plausible variants for the weekly schedule.",
            model=QWEN_MODEL,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            client=client,
            response_format={"type": "json_object"},
            save_chat=False,
        )
    )
