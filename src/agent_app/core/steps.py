from dataclasses import dataclass, field
from typing import Any


@dataclass
class Step:
    name: str
    message: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    answer: str
    reasoning: str | None
    steps: list[Step]