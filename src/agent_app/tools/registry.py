from agent_app.tools.base import BaseTool, ToolResult
from agent_app.llm import ToolNotFoundError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as error:
            available = ", ".join(self._tools.keys())
            raise ToolNotFoundError(
                f"Неизвестный tool: {name}. Доступные tools: {available}"
            ) from error

    def has(self, name: str) -> bool:
        return name in self._tools

    def run(self, name: str, arguments: dict) -> ToolResult:
        tool = self.get(name)
        return tool.run(arguments)

    def openai_schemas(self) -> list[dict]:
        return [tool.openai_schema() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())


def create_tools() -> ToolRegistry:
    from agent_app.tools.basic import CurrentTimeTool, TextStatsTool

    registry = ToolRegistry()
    registry.register(CurrentTimeTool())
    registry.register(TextStatsTool())

    return registry