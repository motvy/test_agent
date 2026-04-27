from datetime import datetime
from typing import Any

from agent_app.tools.base import BaseTool, ToolResult


class CurrentTimeTool(BaseTool):
    name = "current_time"
    description = "Возвращает текущее локальное время."

    def run(self, arguments: dict) -> ToolResult:
        now = datetime.now().isoformat()

        return ToolResult(
            content=(
                f"Результат выполнения tool {self.name}: {now}.\n"
                "Используй это значение для ответа."
            ), 
            display=f"Текущее время: {now}"
        )

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }