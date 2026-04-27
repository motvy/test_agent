from typing import Any

from agent_app.tools.base import BaseTool, ToolResult


class TextStatsTool(BaseTool):
    name = "text_stats"
    description = "Считает количество символов, слов и строк в тексте."

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        text = arguments["text"]
        lines = text.splitlines()

        chars = len(text)
        words = len(text.split())
        lines = len(lines)
        
        return ToolResult(
            content=(
                f"Результат выполнения tool {self.name}: "
                f"characters={chars}, words={words}, lines={lines}.\n"
                "Используй это значение для ответа."
            ), 
            display=f"Символы: {chars}, слова: {words}, строки: {lines}"
        )

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Текст для анализа.",
                        }
                    },
                    "required": ["text"],
                },
            },
        }