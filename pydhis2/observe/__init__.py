"""Observability module - Logging and metrics"""

from pydhis2.observe.logging import get_logger, setup_logging

__all__ = [
    "setup_logging",
    "get_logger",
]
