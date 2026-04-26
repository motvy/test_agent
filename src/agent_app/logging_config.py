from loguru import logger


def setup_logging() -> None:
    logger.remove()

    logger.add(
        "logs/agent.log",
        level="DEBUG",
        rotation="1 MB",
        retention=5,
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level} | "
            "{name}:{function}:{line} | {message}"
        ),
    )