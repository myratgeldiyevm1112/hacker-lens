"""
Central loguru configuration. Importing this module's `logger`
elsewhere keeps log formatting and level consistent across the
whole app, instead of each module configuring its own.
"""

import sys

from loguru import logger

from hackerlens.core.config import settings

logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    ),
)

__all__ = ["logger"]