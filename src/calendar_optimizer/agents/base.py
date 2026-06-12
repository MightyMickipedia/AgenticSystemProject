"""Agent Squad compatible agent for Ollama's OpenAI-compatible API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from agent_squad.agents import Agent, AgentOptions
from agent_squad.types import ConversationMessage, ParticipantRole
from agent_squad.utils import AgentTool

from calendar_optimizer.agents.flow import flow, summarize_arguments

QWEN_MODEL = "qwen2.5:14b-instruct-q5_K_M"
LLAMA_MODEL = "llama3.1:8b"
ALLOWED_MODELS = frozenset((QWEN_MODEL, LLAMA_MODEL))


@dataclass
class OllamaToolAgentOptions(AgentOptions):
    """Configuration for a local Ollama-backed agent."""

    model: str = ""
    system_prompt: str = ""
    tools: list[AgentTool] = field(default_factory=list)
    client: Any = None
    base_url: str = "http://localhost:11434/v1"
    max_tool_rounds: int = 8
    temperature: float = 0.1
    response_format: dict[str, str] | None = None


class OllamaToolAgent(Agent):
    """Small Agent Squad adapter with local function-calling support."""

    def __init__(self, options: OllamaToolAgentOptions):
        super().__init__(options)
        if options.model not in ALLOWED_MODELS:
            raise ValueError(
                f"Model '{options.model}' ist nicht erlaubt. Erlaubt: {sorted(ALLOWED_MODELS)}"
            )
        if options.client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as error:
                raise RuntimeError("Die Abhängigkeit 'openai' ist nicht installiert.") from error
            self.client = AsyncOpenAI(base_url=options.base_url, api_key="ollama")
        else:
            self.client = options.client
        self.model = options.model
        self.system_prompt = options.system_prompt
        self.tools = options.tools
        self.max_tool_rounds = options.max_tool_rounds
        self.temperature = options.temperature
        self.response_format = options.response_format

    @staticmethod
    def _history_message(message: ConversationMessage) -> dict[str, str]:
        role = message.role.value if hasattr(message.role, "value") else str(message.role)
        text = message.content[0].get("text", "") if message.content else ""
        return {"role": role, "content": text}

    async def _execute_tool(self, name: str, arguments: str) -> str:
        flow(f"{self.name} -> Tool {name}: {summarize_arguments(arguments or '{}')}")
        tool = next((candidate for candidate in self.tools if candidate.name == name), None)
        if tool is None:
            flow(f"Tool {name} -> {self.name}: Tool nicht gefunden")
            return json.dumps({"error": f"Unbekanntes Tool: {name}"})
        try:
            values = json.loads(arguments or "{}")
            result = await tool.func(**values)
            flow(f"Tool {name} -> {self.name}: Ergebnis erhalten")
            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as error:  # Tool errors must be visible to the model.
            flow(f"Tool {name} -> {self.name}: Fehler: {error}")
            return json.dumps({"error": str(error)}, ensure_ascii=False)

    async def process_request(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
        chat_history: list[ConversationMessage],
        additional_params: Optional[dict[str, Any]] = None,
    ) -> ConversationMessage:
        del user_id, session_id, additional_params
        flow(f"{self.name} arbeitet mit {self.model}")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            *(self._history_message(message) for message in chat_history),
            {"role": "user", "content": input_text},
        ]

        for _ in range(self.max_tool_rounds + 1):
            request: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
            }
            if self.tools:
                request["tools"] = [tool.to_openai_format() for tool in self.tools]
                request["tool_choice"] = "auto"
            if self.response_format:
                request["response_format"] = self.response_format

            response = await self.client.chat.completions.create(**request)
            if not response.choices:
                raise RuntimeError(f"{self.name} lieferte keine Antwort.")
            message = response.choices[0].message
            tool_calls = message.tool_calls or []
            if not tool_calls:
                content = message.content or ""
                flow(f"{self.name} hat die Arbeit abgeschlossen")
                return ConversationMessage(
                    role=ParticipantRole.ASSISTANT.value,
                    content=[{"text": content}],
                )

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    call.model_dump(exclude_none=True) if hasattr(call, "model_dump") else call
                    for call in tool_calls
                ],
            }
            messages.append(assistant_message)
            for call in tool_calls:
                result = await self._execute_tool(
                    call.function.name,
                    call.function.arguments,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        raise RuntimeError(f"{self.name} überschritt das Tool-Aufruflimit.")
