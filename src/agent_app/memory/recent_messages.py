from collections import deque

from agent_app.core.messages import Message
from agent_app.memory.base import BaseMemory


class RecentMessagesMemory(BaseMemory):
    def __init__(self, max_messages: int):
        self.max_messages = max_messages
        self._messages = deque(maxlen=max_messages)

    async def add(self, message: Message) -> None:
        self._messages.append(message)

    async def get_context(self) -> list[Message]:
        return list(self._messages)

    async def clear(self) -> None:
        self._messages.clear()

    async def size(self) -> int:
        return len(self._messages)