"""
Structured logging configuration using loguru.

Provides consistent log formatting across all modules.
"""

import sys

from loguru import logger

from configs.settings import get_settings


def setup_logging() -> None:
    """Configure loguru logger for the application."""
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Console handler with color
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=not settings.is_production,
    )

    # File handler for persistent logs
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="gz",
        enqueue=True,  # Thread-safe
    )

    # Separate error log
    logger.add(
        "logs/errors_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        compression="gz",
        enqueue=True,
    )

    logger.info(f"Logging configured | level={settings.log_level} | env={settings.app_env}")


def get_logger(name: str):
    """Get a contextualized logger for a specific module."""
    return logger.bind(module=name)
