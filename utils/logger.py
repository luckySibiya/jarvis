"""Logging configuration for Jarvis."""

import logging
import sys


def setup_logger(level=logging.INFO) -> logging.Logger:
    """Configure and return the root Jarvis logger."""
    logger = logging.getLogger("jarvis")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the jarvis namespace."""
    return logging.getLogger(f"jarvis.{name}")
