# LLM Agent App

Приложение-агент для работы с LLM API.

Проект демонстрирует:
- асинхронную работу с LLM через `httpx`;
- поддержку OpenAI-style `tool_calls`;
- оперативную память диалога;
- CLI-интерфейс;
- логирование;
- обработку ошибок;
- расширяемую архитектуру;

## Возможности

- выбор модели;
- чат с LLM с отображением истории диалога;
- отображение steps выполнения агента;
- поддержка reasoning, если модель его возвращает;
- tools:
  - `current_time`;
  - `text_stats`;
- логирование;
- обработка ошибок;

## Архитектура

```text
src/agent_app/
  core/                       # ядро агента
    agent.py                  # основной агент
    steps.py                  # структура шагов
    messages.py               # структура сообщений
  interfaces/                 # интерфейсы
    base.py                   # базовый интерфейс
    cli.py                    # CLI-интерфейс
  llm/                        # работа с LLM
    base.py                   # базовый интерфейс LLM-клиента
    openai_compatible.py      № реализация OpenAI-совместимого клиента
    exceptions.py             # ошибки LLM
  memory/                     # память диалога
    base.py                   # базовый интерфейс памяти
    inrecent_messages.py      # простая реализация (последнии n сообщений)
  tools/                      # инструменты агента
    basic/                    # простые примеры инструментов (для демо)
    base.py                   # базовый класс инструмента
    registry.py               # реестр инструментов
  config.py                   # конфигурация (env, настройки LLM и приложения)
  logging_config.py           # настройка логгера
  main.py                     # точка входа (запуск CLI)
```

Архитектура спроектирована с учетом расширяемости через наследование от base-классов.

Возможные расширения:
- новые LLM-клиенты (llm)
- новые интерфейсы (interfaces)
- новые инструменты (tools)
- альтернативные реализации памяти (memory)


## Запуск

### 1. Настройка `.env`

Создайте файл `.env` в корне проекта:

```env
LLM_BASE_URL=https://your-llm-endpoint/v1
LLM_API_KEY=your-api-key
LLM_API_KEY_HEADER=x-litellm-api-key
```

### 2. Запуск через Docker

Сборка:

```bash
docker build -t llm-agent-cli .
```

Запуск:

```bash
docker run -it --env-file .env llm-agent-cli
```

### 3. Запуск через uv

1. Установить uv (если не установлен):

```bash
pip install uv
```

2. Установить зависимости (из lock-файла):

```bash
uv sync
```

3. Запуск приложения:

```bash
uv run python -m agent_app.main
```
