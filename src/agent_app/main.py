import asyncio

from loguru import logger

from agent_app.config import AppSettings
from agent_app.core import Agent
from agent_app.interfaces import CLIInterface
from agent_app.llm import OpenAICompatibleClient
from agent_app.logging_config import setup_logging
from agent_app.memory import RecentMessagesMemory
from agent_app.tools import create_tools


async def main() -> None:
    setup_logging()

    logger.info("Application started")

    settings = AppSettings()

    llm_client = OpenAICompatibleClient(
        base_url=settings.base_url,
        model=settings.model,
        api_key=settings.api_key,
        api_key_header=settings.api_key_header,
        timeout=settings.llm_timeout,
    )

    memory = RecentMessagesMemory(max_messages=settings.memory_size)
    tools = create_tools()

    agent = Agent(
        llm_client=llm_client,
        memory=memory,
        tools=tools,
        system_prompt=settings.system_prompt,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        max_tool_iterations=settings.max_tool_iterations,
    )

    cli = CLIInterface(settings=settings, agent=agent, llm_client=llm_client, memory=memory, tools=tools)

    await cli.run()
    logger.info("Application finished")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        logger.info("Application interrupted by user")
    except Exception as error:
        logger.exception("Unhandled application error")
        print("\nПроизошла непредвиденная ошибка. Подробности в логах.")
