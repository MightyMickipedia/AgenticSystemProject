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
Du bist der Schedule Manager eines rein beratenden Kalenderoptimierers.
Nutze ausschließlich die Read-only-Tools, um die Woche zu verstehen.
Schätze anhand von Titel, Beschreibung, Ort und Zeit vorsichtig ein, ob Termine verschiebbar sind.
Ganztägige Termine dürfen nie verschoben werden. Verändere nie die Termindauer.
Rufe list_conflicts auf. Jede erzeugte Variante muss sämtliche bestehenden Terminkonflikte
auflösen und darf keine neuen Konflikte erzeugen.
Erzeuge genau drei ausgewogene Varianten und antworte ausschließlich als JSON:
{
  "variants": [
    {
      "name": "Kurzer Name",
      "summary": "Deutsche Zusammenfassung",
      "proposals": [
        {
          "event_id": "bestehende ID",
          "new_start": "ISO-Zeit mit Offset",
          "new_end": "ISO-Zeit mit Offset",
          "reason": "deutsche Begründung",
          "flexibility": "fixed|likely_fixed|uncertain|likely_flexible|flexible",
          "confidence": 0.0
        }
      ]
    }
  ]
}
Jede Variante darf leer sein, wenn keine sinnvolle und plausible Verschiebung existiert.
""".strip()


def build_schedule_manager(tools: list[AgentTool], client: Any = None) -> OllamaToolAgent:
    return OllamaToolAgent(
        OllamaToolAgentOptions(
            name="Schedule Manager",
            description="Erstellt plausible Varianten für die Wochenplanung.",
            model=QWEN_MODEL,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            client=client,
            response_format={"type": "json_object"},
            save_chat=False,
        )
    )
