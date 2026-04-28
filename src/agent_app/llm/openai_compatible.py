import asyncio
import json
from json import JSONDecodeError
from typing import Any

from loguru import logger

import httpx

from agent_app.core.messages import Message, ToolCall
from agent_app.llm.base import BaseLLMClient, LLMResponse
from agent_app.llm.exceptions import LLMConfigurationError, LLMConnectionError, LLMResponseError, LLMTimeoutError, LLMCancelledError


class OpenAICompatibleClient(BaseLLMClient):
    def __init__(
        self,
        base_url: str,
        model: str | None = None,
        api_key: str | None = None,
        api_key_header: str = "Authorization",
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._api_key_header = api_key_header
        self._timeout = httpx.Timeout(timeout, connect=10.0, read=timeout, write=10.0, pool=10.0)

    @property
    def model(self) -> str | None:
        return self._model

    @model.setter
    def model(self, value: str | None):
        self._model = value

    async def list_models(self) -> list[str]:
        logger.info("Requesting models list")

        data = await self._request_json("GET", f"{self._base_url}/models")
        models = [item["id"] for item in data.get("data", [])]

        logger.info("Models loaded: count={}", len(models))
        logger.debug("Available models: {}", models)

        return models

    async def chat(self, messages: list[Message], temperature: float, max_tokens: int | None, tools: list[dict] | None = None) -> LLMResponse:
        if self._model is None:
            raise LLMConfigurationError("Модель не выбрана.")

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [self._message_to_dict(message) for message in messages],
            "temperature": temperature,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        
        logger.info("Sending chat completion request: model={}, messages={}, tools={}", self._model, len(messages), bool(tools))

        raw = await self._request_json("POST", f"{self._base_url}/chat/completions", json=payload)
        response = self._parse_response(raw)

        logger.info("Chat completion received: finish_reason={}, tool_calls={}, content_length={}", response.finish_reason, len(response.tool_calls), len(response.content))

        return response

    def _headers(self) -> dict[str, str]:
        if self._api_key is None:
            return {}

        return {
            self._api_key_header.strip(): self._api_key.strip(),
        }

    async def _request_json(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        logger.info("Sending request: method={}, url={}", method, url)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method=method, url=url, headers=self._headers(), **kwargs)
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException as error:
            raise LLMTimeoutError from error
        except httpx.ConnectError as error:
            raise LLMConnectionError from error
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            text = error.response.text
            raise LLMResponseError(f"{status_code}: {text[:300]}") from error
        except JSONDecodeError as error:
            raise LLMResponseError from error
        except httpx.HTTPError as error:
            raise LLMResponseError from error
        except (asyncio.CancelledError, KeyboardInterrupt) as error:
            raise LLMCancelledError from error

    def _parse_response(self, raw: dict[str, Any]) -> LLMResponse:
        choice = raw["choices"][0]
        message = choice["message"]

        content = message.get("content") or ""
        reasoning = message.get("reasoning") or message.get("reasoning_content")

        tool_calls = self._parse_tool_calls(message.get("tool_calls") or [])

        return LLMResponse(content=content, reasoning=reasoning, tool_calls=tool_calls, finish_reason=choice.get("finish_reason"), raw=raw)

    def _parse_tool_calls(self, raw_tool_calls: list[dict[str, Any]]) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []

        for raw_call in raw_tool_calls:
            function = raw_call["function"]
            raw_arguments = function.get("arguments") or "{}"

            arguments = json.loads(raw_arguments)

            tool_calls.append(ToolCall(id=raw_call["id"], name=function["name"], arguments=arguments))

        return tool_calls

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        result: dict[str, Any] = {"role": message.role, "content": message.content}

        if message.name is not None:
            result["name"] = message.name

        if message.tool_call_id is not None:
            result["tool_call_id"] = message.tool_call_id

        if message.tool_calls is not None:
            result["tool_calls"] = [self._tool_call_to_dict(tool_call) for tool_call in message.tool_calls]

        return result

    def _tool_call_to_dict(self, tool_call: ToolCall) -> dict[str, Any]:
        return {
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.name,
                "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
            },
        }