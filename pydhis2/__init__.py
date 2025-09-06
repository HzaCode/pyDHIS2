"""
pydhis2 - Reproducible DHIS2 Python SDK for LMIC scenarios

An async-first DHIS2 Python SDK with built-in rate limiting and retry mechanisms, featuring:
- One-click conversion to Pandas/Arrow formats
- Built-in WHO-DQR data quality metrics
- CLI + Cookiecutter template support
- Optimized for weak network environments
"""

# Lazy import to avoid circular dependencies
def get_client():
    from pydhis2.core.client import AsyncDHIS2Client, SyncDHIS2Client
    return AsyncDHIS2Client, SyncDHIS2Client

# Core types can be imported directly
from pydhis2.core.types import DHIS2Config
from pydhis2.core.errors import (
    DHIS2Error,
    DHIS2HTTPError,
    RateLimitExceeded,
    RetryExhausted,
    ImportConflictError,
)

__version__ = "0.1.0"
__author__ = "pydhis2 contributors"

__all__ = [
    "get_client",
    "DHIS2Config",
    "DHIS2Error",
    "DHIS2HTTPError",
    "RateLimitExceeded",
    "RetryExhausted",
    "ImportConflictError",
]
