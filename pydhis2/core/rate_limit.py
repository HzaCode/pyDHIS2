"""Rate limiting module - Support for global/per-host/per-route rate limiting"""

import asyncio
import time
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque

from aiolimiter import AsyncLimiter

from pydhis2.core.errors import RateLimitExceeded


class RateLimiter:
    """Rate limiter"""
    
    def __init__(
        self,
        rate: float,  # Requests per second
        burst: Optional[int] = None,  # Burst limit
        capacity: Optional[int] = None  # Token bucket capacity
    ):
        self.rate = rate
        self.burst = burst or int(rate * 2)  # Default burst is 2x the rate
        self.capacity = capacity or self.burst
        
        # Implemented using aiolimiter
        self._limiter = AsyncLimiter(max_rate=rate, time_period=1.0)
        
        # Statistics
        self._requests_count = 0
        self._last_reset = time.time()
        self._blocked_count = 0
        self._total_wait_time = 0.0
    
    async def acquire(self, amount: int = 1) -> None:
        """Acquire a token"""
        start_time = time.time()
        
        try:
            await self._limiter.acquire(amount)
            self._requests_count += amount
        except Exception as e:
            self._blocked_count += 1
            wait_time = time.time() - start_time
            self._total_wait_time += wait_time
            
            raise RateLimitExceeded(
                retry_after=wait_time,
                current_rate=self.get_current_rate(),
                limit=self.rate
            ) from e
    
    def get_current_rate(self) -> float:
        """Get the current request rate"""
        now = time.time()
        elapsed = now - self._last_reset
        if elapsed > 0:
            return self._requests_count / elapsed
        return 0.0
    
    def get_stats(self) -> Dict[str, float]:
        """Get statistics"""
        return {
            'rate_limit': self.rate,
            'requests_count': self._requests_count,
            'blocked_count': self._blocked_count,
            'current_rate': self.get_current_rate(),
            'total_wait_time': self._total_wait_time,
        }
    
    def reset_stats(self) -> None:
        """Reset statistics"""
        self._requests_count = 0
        self._blocked_count = 0
        self._total_wait_time = 0.0
        self._last_reset = time.time()


class HostRateLimiter:
    """Host-based rate limiter"""
    
    def __init__(self, default_rate: float = 10.0):
        self.default_rate = default_rate
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = asyncio.Lock()
    
    async def get_limiter(self, host: str, rate: Optional[float] = None) -> RateLimiter:
        """Get or create a host limiter"""
        async with self._lock:
            if host not in self._limiters:
                limiter_rate = rate or self.default_rate
                self._limiters[host] = RateLimiter(limiter_rate)
            return self._limiters[host]
    
    async def acquire(self, host: str, amount: int = 1, rate: Optional[float] = None) -> None:
        """Acquire a token for a specific host"""
        limiter = await self.get_limiter(host, rate)
        await limiter.acquire(amount)
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all hosts"""
        return {host: limiter.get_stats() for host, limiter in self._limiters.items()}


class RouteRateLimiter:
    """Route-based rate limiter"""
    
    def __init__(self, default_rate: float = 10.0):
        self.default_rate = default_rate
        self._limiters: Dict[str, RateLimiter] = {}
        self._route_configs: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    def configure_route(self, route_pattern: str, rate: float) -> None:
        """Configure the rate limit for a specific route"""
        self._route_configs[route_pattern] = rate
    
    def _match_route(self, path: str) -> Optional[str]:
        """Match a route pattern"""
        # Simple prefix matching
        for pattern in self._route_configs:
            if path.startswith(pattern):
                return pattern
        return None
    
    async def get_limiter(self, path: str) -> RateLimiter:
        """Get or create a route limiter"""
        route_pattern = self._match_route(path)
        cache_key = route_pattern or 'default'
        
        async with self._lock:
            if cache_key not in self._limiters:
                if route_pattern and route_pattern in self._route_configs:
                    rate = self._route_configs[route_pattern]
                else:
                    rate = self.default_rate
                self._limiters[cache_key] = RateLimiter(rate)
            return self._limiters[cache_key]
    
    async def acquire(self, path: str, amount: int = 1) -> None:
        """Acquire a token for a specific route"""
        limiter = await self.get_limiter(path)
        await limiter.acquire(amount)


class GlobalRateLimiter:
    """Global rate limiting manager"""
    
    def __init__(
        self,
        global_rate: float = 10.0,
        per_host_rate: Optional[float] = None,
        enable_burst: bool = True
    ):
        self.global_rate = global_rate
        self.per_host_rate = per_host_rate or global_rate
        self.enable_burst = enable_burst
        
        # Global limiter
        self.global_limiter = RateLimiter(
            rate=global_rate,
            burst=int(global_rate * 2) if enable_burst else int(global_rate)
        )
        
        # Host-level limiter
        self.host_limiter = HostRateLimiter(self.per_host_rate)
        
        # Route-level limiter
        self.route_limiter = RouteRateLimiter(self.per_host_rate)
        
        # Sliding window statistics
        self._request_times: deque = deque()
        self._window_size = 60.0  # 60-second window
    
    def configure_route_limits(self, route_limits: Dict[str, float]) -> None:
        """Configure route-level limits"""
        for route, rate in route_limits.items():
            self.route_limiter.configure_route(route, rate)
    
    async def acquire(
        self,
        host: str,
        path: str,
        amount: int = 1,
        bypass_global: bool = False
    ) -> None:
        """Acquire a token at multiple levels"""
        # Update statistics
        now = time.time()
        self._request_times.append(now)
        
        # Clean up expired request times
        while self._request_times and self._request_times[0] < now - self._window_size:
            self._request_times.popleft()
        
        # 1. Global limit
        if not bypass_global:
            await self.global_limiter.acquire(amount)
        
        # 2. Host limit
        await self.host_limiter.acquire(host, amount)
        
        # 3. Route limit  
        await self.route_limiter.acquire(path, amount)
    
    def get_current_rps(self) -> float:
        """Get the current RPS"""
        now = time.time()
        # Calculate the number of requests in the window
        valid_requests = [t for t in self._request_times if t > now - self._window_size]
        return len(valid_requests) / self._window_size
    
    def get_comprehensive_stats(self) -> Dict[str, any]:
        """Get comprehensive statistics"""
        return {
            'global': self.global_limiter.get_stats(),
            'hosts': self.host_limiter.get_stats(),
            'current_rps': self.get_current_rps(),
            'window_requests': len(self._request_times),
            'configured_routes': list(self.route_limiter._route_configs.keys()),
        }


class AdaptiveRateLimiter(GlobalRateLimiter):
    """Adaptive rate limiter - automatically adjusts based on response"""
    
    def __init__(
        self,
        initial_rate: float = 10.0,
        min_rate: float = 1.0,
        max_rate: float = 50.0,
        adaptation_factor: float = 0.1
    ):
        super().__init__(initial_rate)
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.adaptation_factor = adaptation_factor
        self.current_rate = initial_rate
        
        # Response time statistics
        self._response_times: deque = deque(maxlen=100)
        self._error_count = 0
        self._success_count = 0
    
    async def record_response(
        self,
        response_time: float,
        status_code: int,
        was_rate_limited: bool = False
    ) -> None:
        """Record a response to be used for adaptive adjustment"""
        self._response_times.append(response_time)
        
        if was_rate_limited or status_code == 429:
            self._error_count += 1
            # Decrease the rate
            self.current_rate = max(
                self.min_rate,
                self.current_rate * (1 - self.adaptation_factor)
            )
        elif 200 <= status_code < 300:
            self._success_count += 1
            # If response time is good, slightly increase the rate
            avg_response_time = sum(self._response_times) / len(self._response_times)
            if avg_response_time < 1.0:  # Response time is less than 1 second
                self.current_rate = min(
                    self.max_rate,
                    self.current_rate * (1 + self.adaptation_factor * 0.5)
                )
        
        # Update the global limiter
        self.global_limiter.rate = self.current_rate
    
    def get_adaptation_stats(self) -> Dict[str, float]:
        """Get adaptive statistics"""
        total_requests = self._success_count + self._error_count
        return {
            'current_rate': self.current_rate,
            'success_rate': self._success_count / total_requests if total_requests > 0 else 0,
            'error_rate': self._error_count / total_requests if total_requests > 0 else 0,
            'avg_response_time': sum(self._response_times) / len(self._response_times) if self._response_times else 0,
            'total_requests': total_requests,
        }
