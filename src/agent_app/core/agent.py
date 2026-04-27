from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from agent_app.core.messages import Message
from agent_app.core.steps import AgentResult, Step
from agent_app.llm import BaseLLMClient, LLMResponse, LLMError, ToolNotFoundError
from agent_app.memory import BaseMemory
from agent_app.tools import ToolRegistry


StepCallback = Callable[[Step], Awaitable[None]]


class Agent:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        memory: BaseMemory,
        tools: ToolRegistry,
        system_prompt: str,
        temperature: float,
        max_tokens: int | None,
        max_tool_iterations: int,
    ) -> None:
        self.llm_client = llm_client
        self.memory = memory
        self.tools = tools
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_tool_iterations = max_tool_iterations

    async def run(self, user_input: str, on_step: StepCallback | None = None) -> AgentResult:
        steps: list[Step] = []

        await self.memory.add(Message(role="user", content=user_input))

        await self._add_step(steps=steps, name="user_message_received", message="Получен запрос пользователя", meta={"content": user_input}, on_step=on_step)

        messages = [Message(role="system", content=self.system_prompt), *await self.memory.get_context()]

        response = await self._call_llm(messages=messages, steps=steps, on_step=on_step, use_tools=True)

        for iteration in range(self.max_tool_iterations):
            if not response.tool_calls:
                break

            response = await self._handle_tool_calls(messages=messages, response=response, iteration=iteration + 1, steps=steps, on_step=on_step)

        if response.tool_calls:
            await self._add_step(
                steps=steps,
                name="max_tool_iterations_reached",
                message="Достигнут лимит итераций tools",
                meta={"max_tool_iterations": self.max_tool_iterations},
                on_step=on_step,
            )

        await self.memory.add(Message(role="assistant", content=response.content))

        await self._add_step(steps=steps, name="assistant_answer_ready", message="Финальный ответ получен", meta={"answer": response.content}, on_step=on_step)

        return AgentResult(answer=response.content, reasoning=response.reasoning, steps=steps)

    async def _call_llm(self, messages: list[Message], steps: list[Step], on_step: StepCallback | None, use_tools: bool = True) -> LLMResponse:
        tools = self.tools.openai_schemas() if use_tools else None

        await self._add_step(
            steps=steps,
            name="llm_request_started",
            message="Отправка запроса в LLM",
            meta={
                "messages_count": len(messages),
                "tools": self.tools.names() if use_tools else [],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            on_step=on_step,
        )

        try:
            response = await self.llm_client.chat(messages=messages, temperature=self.temperature, max_tokens=self.max_tokens, tools=tools)
        except LLMError as error:
            error_text = f"[Ошибка] {error.user_message()}"
            await self._add_step(steps=steps, name="llm_error", message=error_text, on_step=on_step)
            await self.memory.add(Message(role="assistant", content=error_text))
            raise

        await self._add_step(
            steps=steps,
            name="llm_response_received",
            message="Получен ответ от LLM",
            meta={
                "finish_reason": response.finish_reason,
                "has_reasoning": response.reasoning is not None,
                "tool_calls_count": len(response.tool_calls),
                "content": response.content,
            },
            on_step=on_step,
        )

        return response

    async def _handle_tool_calls(self, messages: list[Message], response: LLMResponse, iteration: int, steps: list[Step], on_step: StepCallback | None) -> LLMResponse:
        await self._add_step(
            steps=steps,
            name="tool_calls_received",
            message="Модель запросила вызов tools",
            meta={
                "iteration": iteration,
                "tools": [tool_call.name for tool_call in response.tool_calls],
            },
            on_step=on_step,
        )

        messages.append(Message(role="assistant", content=response.content, tool_calls=response.tool_calls))

        has_tool_error = False

        for tool_call in response.tool_calls:
            try:
                tool_result = self.tools.run(name=tool_call.name, arguments=tool_call.arguments)

                tool_content = tool_result.content

                await self._add_step(
                    steps=steps,
                    name="tool_executed",
                    message=f"Выполнен tool: {tool_call.name}",
                    meta={
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "arguments": tool_call.arguments,
                        "result": tool_content,
                    },
                    on_step=on_step,
                )

            except ToolNotFoundError as error:
                has_tool_error = True
                tool_content = error.user_message()

                await self._add_step(
                    steps=steps,
                    name="tool_error",
                    message=tool_content,
                    meta={
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "arguments": tool_call.arguments,
                    },
                    on_step=on_step,
                )

            messages.append(Message(role="tool", name=tool_call.name, tool_call_id=tool_call.id, content=tool_content))

        response = await self._call_llm(messages=messages, steps=steps, on_step=on_step, use_tools=has_tool_error)

        if not response.content:
            response.content = self._build_answer_from_last_tool_result(messages)

        return response

    def _build_answer_from_last_tool_result(self, messages: list[Message]) -> str:
        tool_messages = [m for m in messages if m.role == "tool"]

        if not tool_messages:
            return "Модель вернула пустой ответ."

        last = tool_messages[-1]

        display = getattr(last, "meta", {}).get("display")

        if display:
            return display

        return last.content

    async def _add_step(self, steps: list[Step], name: str, message: str, meta: dict[str, Any] | None = None, on_step: StepCallback | None = None) -> None:
        step = Step(name=name, message=message, meta=meta or {})
        steps.append(step)

        logger.debug("Agent step: name={}, message={}, meta={}", step.name, step.message, step.meta)

        if on_step is not None:
            await on_step(step)