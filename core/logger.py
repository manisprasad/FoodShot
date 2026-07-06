import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and route them to Loguru.
    """

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    logger.remove()

    logger.add(
        sys.stdout,
        enqueue=True,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for _log in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "aiogram"]:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False
