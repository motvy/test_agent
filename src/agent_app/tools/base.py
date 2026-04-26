from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    content: str
    display: str | None = None


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, arguments: dict[str, Any]) -> ToolResult:
        ...

    @abstractmethod
    def openai_schema(self) -> dict[str, Any]:
        ...