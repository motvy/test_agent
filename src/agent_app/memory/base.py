from abc import ABC, abstractmethod
from agent_app.core.messages import Message


class BaseMemory(ABC):
    @abstractmethod
    async def add(self, message: Message) -> None:
        ...

    @abstractmethod
    async def get_context(self) -> list[Message]:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...