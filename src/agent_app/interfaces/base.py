from abc import ABC, abstractmethod
from agent_app.core.steps import AgentResult


class BaseInterface(ABC):
    @abstractmethod
    async def run(self) -> None:
        ...
