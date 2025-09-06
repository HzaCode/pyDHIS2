"""Retry module - Exponential backoff, jitter, and retry strategies"""

import asyncio
import random
import time
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import aiohttp
from tenacity import (
    Retrying,
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    retry_if_result,
)

from pydhis2.core.errors import RetryExhausted, DHIS2HTTPError


@dataclass
class RetryAttempt:
    """Retry attempt record"""
    attempt_number: int
    start_time: float
    end_time: Optional[float] = None
    exception: Optional[Exception] = None
    response_status: Optional[int] = None
    wait_time: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Attempt duration"""
        if self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 5
    base_delay: float = 0.5  # Base delay (seconds)
    max_delay: float = 60.0  # Maximum delay (seconds)
    backoff_factor: float = 2.0  # Backoff factor
    jitter: bool = True  # Whether to enable jitter
    retry_on_status: Set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    retry_on_exceptions: Set[Type[Exception]] = field(default_factory=lambda: {
        aiohttp.ClientError,
        aiohttp.ClientResponseError,
        asyncio.TimeoutError,
        ConnectionError,
    })
    respect_retry_after: bool = True  # Whether to respect the Retry-After header
    max_retry_after: float = 300.0  # Maximum value for Retry-After


class RetryStrategy(ABC):
    """Retry strategy abstract base class"""
    
    @abstractmethod
    def calculate_wait_time(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        backoff_factor: float,
        jitter: bool = True
    ) -> float:
        """Calculate wait time"""
        pass


class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff strategy"""
    
    def calculate_wait_time(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        backoff_factor: float,
        jitter: bool = True
    ) -> float:
        """Calculate exponential backoff wait time"""
        # Exponential backoff: base_delay * (backoff_factor ^ (attempt - 1))
        wait_time = base_delay * (backoff_factor ** (attempt - 1))
        wait_time = min(wait_time, max_delay)
        
        if jitter:
            # Full jitter: random value between 0 and the calculated value
            wait_time = random.uniform(0, wait_time)
        
        return wait_time


class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff strategy"""
    
    def calculate_wait_time(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        backoff_factor: float,
        jitter: bool = True
    ) -> float:
        """Calculate linear backoff wait time"""
        wait_time = base_delay * attempt
        wait_time = min(wait_time, max_delay)
        
        if jitter:
            # Add ±25% jitter
            jitter_range = wait_time * 0.25
            wait_time += random.uniform(-jitter_range, jitter_range)
            wait_time = max(0, wait_time)
        
        return wait_time


class FixedDelayStrategy(RetryStrategy):
    """Fixed delay strategy"""
    
    def calculate_wait_time(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        backoff_factor: float,
        jitter: bool = True
    ) -> float:
        """Calculate fixed delay wait time"""
        wait_time = base_delay
        
        if jitter:
            # Add ±50% jitter
            jitter_range = wait_time * 0.5
            wait_time += random.uniform(-jitter_range, jitter_range)
            wait_time = max(0, wait_time)
        
        return wait_time


class RetryManager:
    """Retry manager"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.strategies = {
            'exponential': ExponentialBackoffStrategy(),
            'linear': LinearBackoffStrategy(),
            'fixed': FixedDelayStrategy(),
        }
        self.default_strategy = self.strategies['exponential']
        
        # Statistics
        self.total_attempts = 0
        self.total_retries = 0
        self.total_wait_time = 0.0
        self.attempts_by_status: Dict[int, int] = {}
    
    def should_retry(
        self,
        attempt: int,
        exception: Optional[Exception] = None,
        response: Optional[aiohttp.ClientResponse] = None
    ) -> bool:
        """Determine if a retry should be attempted"""
        if attempt >= self.config.max_attempts:
            return False
        
        # Check exception type
        if exception:
            return any(
                isinstance(exception, exc_type)
                for exc_type in self.config.retry_on_exceptions
            )
        
        # Check HTTP status code
        if response:
            return response.status in self.config.retry_on_status
        
        return False
    
    def extract_retry_after(self, response: Optional[aiohttp.ClientResponse]) -> Optional[float]:
        """Extract Retry-After header information"""
        if not response or not self.config.respect_retry_after:
            return None
        
        retry_after = response.headers.get('Retry-After')
        if not retry_after:
            return None
        
        try:
            # Try to parse as seconds
            seconds = float(retry_after)
            return min(seconds, self.config.max_retry_after)
        except ValueError:
            # Try to parse as HTTP date (simplified implementation, not currently supported)
            return None
    
    def calculate_wait_time(
        self,
        attempt: int,
        strategy: str = 'exponential',
        retry_after: Optional[float] = None
    ) -> float:
        """Calculate wait time"""
        if retry_after is not None:
            return retry_after
        
        strategy_impl = self.strategies.get(strategy, self.default_strategy)
        return strategy_impl.calculate_wait_time(
            attempt=attempt,
            base_delay=self.config.base_delay,
            max_delay=self.config.max_delay,
            backoff_factor=self.config.backoff_factor,
            jitter=self.config.jitter
        )
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        strategy: str = 'exponential',
        **kwargs
    ) -> Any:
        """Execute a function with retry when needed"""
        attempts: List[RetryAttempt] = []
        
        for attempt in range(1, self.config.max_attempts + 1):
            self.total_attempts += 1
            attempt_record = RetryAttempt(
                attempt_number=attempt,
                start_time=time.time()
            )
            attempts.append(attempt_record)
            
            try:
                result = await func(*args, **kwargs)
                attempt_record.end_time = time.time()
                
                # Check if the result requires a retry
                if hasattr(result, 'status'):
                    attempt_record.response_status = result.status
                    self.attempts_by_status[result.status] = (
                        self.attempts_by_status.get(result.status, 0) + 1
                    )
                    
                    if not self.should_retry(attempt, response=result):
                        return result
                else:
                    return result
                
            except Exception as e:
                attempt_record.end_time = time.time()
                attempt_record.exception = e
                
                # If it's the last attempt, raise the RetryExhausted exception
                if attempt == self.config.max_attempts:
                    raise RetryExhausted(
                        max_retries=self.config.max_attempts,
                        last_error=e,
                        attempt_details=[
                            {
                                'attempt': a.attempt_number,
                                'duration': a.duration,
                                'exception': str(a.exception) if a.exception else None,
                                'status': a.response_status,
                                'wait_time': a.wait_time,
                            }
                            for a in attempts
                        ]
                    ) from e
                
                # Check if we should retry
                if not self.should_retry(attempt, exception=e):
                    raise
            
            # Calculate wait time
            retry_after = None
            if 'result' in locals() and hasattr(result, 'headers'):
                retry_after = self.extract_retry_after(result)
            
            wait_time = self.calculate_wait_time(attempt, strategy, retry_after)
            attempt_record.wait_time = wait_time
            self.total_wait_time += wait_time
            self.total_retries += 1
            
            # Wait
            await asyncio.sleep(wait_time)
        
        # Should not get here
        raise RetryExhausted(
            max_retries=self.config.max_attempts,
            attempt_details=[
                {
                    'attempt': a.attempt_number,
                    'duration': a.duration,
                    'exception': str(a.exception) if a.exception else None,
                    'status': a.response_status,
                    'wait_time': a.wait_time,
                }
                for a in attempts
            ]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retry statistics"""
        return {
            'total_attempts': self.total_attempts,
            'total_retries': self.total_retries,
            'total_wait_time': self.total_wait_time,
            'retry_rate': self.total_retries / self.total_attempts if self.total_attempts > 0 else 0,
            'avg_wait_time': self.total_wait_time / self.total_retries if self.total_retries > 0 else 0,
            'attempts_by_status': self.attempts_by_status,
        }
    
    def reset_stats(self) -> None:
        """Reset statistics"""
        self.total_attempts = 0
        self.total_retries = 0
        self.total_wait_time = 0.0
        self.attempts_by_status.clear()


# Predefined retry configurations
DEFAULT_RETRY_CONFIG = RetryConfig()

AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=10,
    base_delay=0.1,
    max_delay=30.0,
    backoff_factor=1.5,
)

CONSERVATIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=120.0,
    backoff_factor=3.0,
)

LMIC_OPTIMIZED_CONFIG = RetryConfig(
    max_attempts=8,
    base_delay=1.0,
    max_delay=180.0,
    backoff_factor=2.5,
    respect_retry_after=True,
    max_retry_after=600.0,  # Longer wait time for weak networks
)


def create_tenacity_retrying(config: RetryConfig, strategy: str = 'exponential') -> AsyncRetrying:
    """Create a retry configuration using the tenacity library"""
    if strategy == 'exponential':
        wait_strategy = wait_exponential(
            multiplier=config.base_delay,
            max=config.max_delay,
        )
    elif strategy == 'fixed':
        wait_strategy = wait_fixed(config.base_delay)
    else:
        wait_strategy = wait_exponential(
            multiplier=config.base_delay,
            max=config.max_delay,
        )
    
    return AsyncRetrying(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(tuple(config.retry_on_exceptions)),
        reraise=True,
    )
