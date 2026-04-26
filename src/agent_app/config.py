import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


DEFAULT_SYSTEM_PROMPT = """
Ты полезный ассистент с доступом к tools.
Если для ответа нужен инструмент, используй доступный tool.
После получения результата tool дай пользователю понятный финальный ответ.
""".strip()


@dataclass
class AppSettings:
    base_url: str = os.getenv("LLM_BASE_URL", "https://llm.webvalera96.ru/v1")
    api_key: str | None = os.getenv("LLM_API_KEY").strip() if os.getenv("LLM_API_KEY") else None
    api_key_header: str = os.getenv("LLM_API_KEY_HEADER", "x-litellm-api-key").strip()

    model: str | None = None

    temperature: float = 0.7
    max_tokens: int | None = None

    memory_size: int = 10
    max_tool_iterations: int = 3
    llm_timeout: float = 120.0

    show_steps: bool = True
    show_reasoning: bool = False

    system_prompt: str = DEFAULT_SYSTEM_PROMPT