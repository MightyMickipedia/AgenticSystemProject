"""Local Ollama agents and Agent Squad orchestration."""

from calendar_optimizer.agents.base import (
    ALLOWED_MODELS,
    LLAMA_MODEL,
    QWEN_MODEL,
    OllamaToolAgent,
    OllamaToolAgentOptions,
)
from calendar_optimizer.agents.orchestrator import (
    CalendarOrchestratorAgent,
    build_agent_squad,
)

__all__ = [
    "ALLOWED_MODELS",
    "CalendarOrchestratorAgent",
    "LLAMA_MODEL",
    "OllamaToolAgent",
    "OllamaToolAgentOptions",
    "QWEN_MODEL",
    "build_agent_squad",
]
