class LLMError(Exception):
    """Base exception for LLM client errors."""
    message = "Произошла ошибка при работе с LLM."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail)

    def user_message(self) -> str:
        if self.detail:
            return f"{self.message} {self.detail}"
        return self.message


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    message = "Модель не ответила вовремя."


class LLMConnectionError(LLMError):
    """LLM API connection failed."""
    message = "Не удалось подключиться к LLM API."


class LLMResponseError(LLMError):
    """LLM API returned an invalid or error response."""

    message = "LLM API вернул ошибку."


class LLMConfigurationError(LLMError):
    """LLM client is not configured correctly."""
    message = "Ошибка конфигурации LLM."


class LLMCancelledError(LLMError):
    """LLM request cancelled."""
    message = "Запрос был отменён."