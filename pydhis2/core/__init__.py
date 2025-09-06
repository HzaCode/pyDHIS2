"""Core module - HTTP client, rate limiting, retry, authentication, and other infrastructure"""

# Export only base types and errors to avoid circular dependencies
from pydhis2.core.types import DHIS2Config
from pydhis2.core.errors import (
    DHIS2Error,
    DHIS2HTTPError,
    RateLimitExceeded,
    RetryExhausted,
    ImportConflictError,
)

__all__ = [
    "DHIS2Config",
    "DHIS2Error", 
    "DHIS2HTTPError",
    "RateLimitExceeded",
    "RetryExhausted",
    "ImportConflictError",
]
