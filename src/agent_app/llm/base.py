from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from agent_app.core.messages import Message, ToolCall


@dataclass
class LLMResponse:
    content: str
    reasoning: str | None
    tool_calls: list[ToolCall]
    finish_reason: str | None
    raw: dict[str, Any]


class BaseLLMClient(ABC):
    @abstractmethod
    async def list_models(self) -> list[str]:
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        temperature: float,
        max_tokens: int | None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        ...
