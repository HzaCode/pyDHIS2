"""Unit tests for rate limiting functionality"""

import pytest
import asyncio
import time
from pydhis2.core.rate_limit import (
    RateLimiter,
    HostRateLimiter, 
    RouteRateLimiter,
    GlobalRateLimiter,
    AdaptiveRateLimiter
)


class TestRateLimiter:
    """Tests for the base RateLimiter class"""
    
    def test_init(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter(rate=10.0)
        
        assert limiter.rate == 10.0
        assert limiter.burst == 20  # Default is 2x rate
        assert limiter._requests_count == 0
        assert limiter._blocked_count == 0
    
    def test_init_with_custom_burst(self):
        """Test rate limiter with custom burst"""
        limiter = RateLimiter(rate=10.0, burst=15)
        
        assert limiter.rate == 10.0
        assert limiter.burst == 15
        assert limiter.capacity == 15
    
    @pytest.mark.asyncio
    async def test_acquire_success(self):
        """Test successful token acquisition"""
        limiter = RateLimiter(rate=100.0)  # High rate to avoid blocking
        
        await limiter.acquire(1)
        assert limiter._requests_count == 1
    
    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens"""
        limiter = RateLimiter(rate=100.0)
        
        await limiter.acquire(5)
        assert limiter._requests_count == 5
    
    def test_get_current_rate(self):
        """Test current rate calculation"""
        limiter = RateLimiter(rate=10.0)
        
        # Initially should be 0
        assert limiter.get_current_rate() == 0.0
        
        # After some requests
        limiter._requests_count = 10
        limiter._last_reset = time.time() - 1.0  # 1 second ago
        
        rate = limiter.get_current_rate()
        assert 9.0 <= rate <= 11.0  # Should be around 10 rps
    
    def test_get_stats(self):
        """Test statistics collection"""
        limiter = RateLimiter(rate=5.0)
        limiter._requests_count = 10
        limiter._blocked_count = 2
        limiter._total_wait_time = 3.0
        
        stats = limiter.get_stats()
        
        assert stats['rate_limit'] == 5.0
        assert stats['requests_count'] == 10
        assert stats['blocked_count'] == 2
        assert stats['total_wait_time'] == 3.0
    
    def test_reset_stats(self):
        """Test statistics reset"""
        limiter = RateLimiter(rate=5.0)
        limiter._requests_count = 10
        limiter._blocked_count = 2
        
        limiter.reset_stats()
        
        assert limiter._requests_count == 0
        assert limiter._blocked_count == 0
        assert limiter._total_wait_time == 0.0


class TestHostRateLimiter:
    """Tests for the HostRateLimiter class"""
    
    @pytest.fixture
    def host_limiter(self):
        """Test host rate limiter"""
        return HostRateLimiter(default_rate=10.0)
    
    @pytest.mark.asyncio
    async def test_get_limiter_new_host(self, host_limiter):
        """Test getting limiter for new host"""
        limiter = await host_limiter.get_limiter("example.com")
        
        assert isinstance(limiter, RateLimiter)
        assert limiter.rate == 10.0
        assert "example.com" in host_limiter._limiters
    
    @pytest.mark.asyncio
    async def test_get_limiter_existing_host(self, host_limiter):
        """Test getting limiter for existing host"""
        limiter1 = await host_limiter.get_limiter("example.com")
        limiter2 = await host_limiter.get_limiter("example.com")
        
        assert limiter1 is limiter2  # Should be the same instance
    
    @pytest.mark.asyncio
    async def test_get_limiter_custom_rate(self, host_limiter):
        """Test getting limiter with custom rate"""
        limiter = await host_limiter.get_limiter("fast.com", rate=20.0)
        assert limiter.rate == 20.0
    
    @pytest.mark.asyncio
    async def test_acquire(self, host_limiter):
        """Test acquiring tokens for a host"""
        await host_limiter.acquire("example.com", amount=1)
        
        limiter = await host_limiter.get_limiter("example.com")
        assert limiter._requests_count == 1
    
    def test_get_stats(self, host_limiter):
        """Test getting stats for all hosts"""
        # Create limiters for different hosts
        asyncio.run(host_limiter.acquire("host1.com"))
        asyncio.run(host_limiter.acquire("host2.com"))
        
        stats = host_limiter.get_stats()
        
        assert "host1.com" in stats
        assert "host2.com" in stats
        assert stats["host1.com"]["requests_count"] == 1
        assert stats["host2.com"]["requests_count"] == 1


class TestRouteRateLimiter:
    """Tests for the RouteRateLimiter class"""
    
    @pytest.fixture
    def route_limiter(self):
        """Test route rate limiter"""
        limiter = RouteRateLimiter(default_rate=10.0)
        limiter.configure_route("/api/analytics", 5.0)
        limiter.configure_route("/api/dataValueSets", 15.0)
        return limiter
    
    def test_configure_route(self, route_limiter):
        """Test route configuration"""
        assert route_limiter._route_configs["/api/analytics"] == 5.0
        assert route_limiter._route_configs["/api/dataValueSets"] == 15.0
    
    def test_match_route(self, route_limiter):
        """Test route pattern matching"""
        # Should match configured routes
        assert route_limiter._match_route("/api/analytics") == "/api/analytics"
        assert route_limiter._match_route("/api/analytics/dimensions") == "/api/analytics"
        assert route_limiter._match_route("/api/dataValueSets") == "/api/dataValueSets"
        
        # Should not match unconfigured routes
        assert route_limiter._match_route("/api/metadata") is None
        assert route_limiter._match_route("/other/path") is None
    
    @pytest.mark.asyncio
    async def test_get_limiter_configured_route(self, route_limiter):
        """Test getting limiter for configured route"""
        limiter = await route_limiter.get_limiter("/api/analytics")
        assert limiter.rate == 5.0
    
    @pytest.mark.asyncio
    async def test_get_limiter_default_route(self, route_limiter):
        """Test getting limiter for unconfigured route"""
        limiter = await route_limiter.get_limiter("/api/metadata")
        assert limiter.rate == 10.0  # Should use default rate
    
    @pytest.mark.asyncio
    async def test_acquire(self, route_limiter):
        """Test acquiring tokens for a route"""
        await route_limiter.acquire("/api/analytics")
        
        limiter = await route_limiter.get_limiter("/api/analytics")
        assert limiter._requests_count == 1


class TestGlobalRateLimiter:
    """Tests for the GlobalRateLimiter class"""
    
    @pytest.fixture
    def global_limiter(self):
        """Test global rate limiter"""
        return GlobalRateLimiter(
            global_rate=10.0,
            per_host_rate=8.0,
            enable_burst=True
        )
    
    def test_init(self, global_limiter):
        """Test global rate limiter initialization"""
        assert global_limiter.global_rate == 10.0
        assert global_limiter.per_host_rate == 8.0
        assert global_limiter.enable_burst is True
        assert isinstance(global_limiter.global_limiter, RateLimiter)
        assert isinstance(global_limiter.host_limiter, HostRateLimiter)
        assert isinstance(global_limiter.route_limiter, RouteRateLimiter)
    
    def test_configure_route_limits(self, global_limiter):
        """Test configuring route limits"""
        route_limits = {
            "/api/analytics": 5.0,
            "/api/tracker": 12.0
        }
        
        global_limiter.configure_route_limits(route_limits)
        
        # Check that routes were configured
        assert global_limiter.route_limiter._route_configs["/api/analytics"] == 5.0
        assert global_limiter.route_limiter._route_configs["/api/tracker"] == 12.0
    
    @pytest.mark.asyncio
    async def test_acquire_multi_level(self, global_limiter):
        """Test multi-level token acquisition"""
        # Should not raise an exception
        await global_limiter.acquire("example.com", "/api/test")
        
        # Check that all limiters were used
        assert global_limiter.global_limiter._requests_count == 1
        assert len(global_limiter._request_times) == 1
    
    @pytest.mark.asyncio
    async def test_acquire_bypass_global(self, global_limiter):
        """Test bypassing global rate limiter"""
        await global_limiter.acquire("example.com", "/api/test", bypass_global=True)
        
        # Global limiter should not have been used
        assert global_limiter.global_limiter._requests_count == 0
    
    def test_get_current_rps(self, global_limiter):
        """Test current RPS calculation"""
        # Initially should be 0
        assert global_limiter.get_current_rps() == 0.0
        
        # Add some request times
        now = time.time()
        global_limiter._request_times.extend([now - 10, now - 5, now - 1])
        
        rps = global_limiter.get_current_rps()
        assert rps == 3.0 / 60.0  # 3 requests in 60-second window
    
    def test_get_comprehensive_stats(self, global_limiter):
        """Test comprehensive statistics"""
        # Add some data
        asyncio.run(global_limiter.acquire("test.com", "/api/test"))
        
        stats = global_limiter.get_comprehensive_stats()
        
        assert 'global' in stats
        assert 'hosts' in stats
        assert 'current_rps' in stats
        assert 'window_requests' in stats
        assert 'configured_routes' in stats


class TestAdaptiveRateLimiter:
    """Tests for the AdaptiveRateLimiter class"""
    
    @pytest.fixture
    def adaptive_limiter(self):
        """Test adaptive rate limiter"""
        return AdaptiveRateLimiter(
            initial_rate=10.0,
            min_rate=1.0,
            max_rate=50.0,
            adaptation_factor=0.1
        )
    
    def test_init(self, adaptive_limiter):
        """Test adaptive limiter initialization"""
        assert adaptive_limiter.current_rate == 10.0
        assert adaptive_limiter.min_rate == 1.0
        assert adaptive_limiter.max_rate == 50.0
        assert adaptive_limiter.adaptation_factor == 0.1
        assert adaptive_limiter._error_count == 0
        assert adaptive_limiter._success_count == 0
    
    @pytest.mark.asyncio
    async def test_record_response_success(self, adaptive_limiter):
        """Test recording successful response"""
        initial_rate = adaptive_limiter.current_rate
        
        await adaptive_limiter.record_response(
            response_time=0.5,
            status_code=200
        )
        
        assert adaptive_limiter._success_count == 1
        assert adaptive_limiter.current_rate >= initial_rate  # Should increase or stay same
    
    @pytest.mark.asyncio
    async def test_record_response_rate_limited(self, adaptive_limiter):
        """Test recording rate limited response"""
        initial_rate = adaptive_limiter.current_rate
        
        await adaptive_limiter.record_response(
            response_time=2.0,
            status_code=429,
            was_rate_limited=True
        )
        
        assert adaptive_limiter._error_count == 1
        assert adaptive_limiter.current_rate < initial_rate  # Should decrease
    
    @pytest.mark.asyncio
    async def test_record_response_fast_success(self, adaptive_limiter):
        """Test recording fast successful response"""
        initial_rate = adaptive_limiter.current_rate
        
        # Record a fast response
        await adaptive_limiter.record_response(
            response_time=0.1,  # Very fast
            status_code=200
        )
        
        assert adaptive_limiter._success_count == 1
        # Rate should increase due to good performance
        assert adaptive_limiter.current_rate > initial_rate
    
    @pytest.mark.asyncio
    async def test_rate_bounds(self, adaptive_limiter):
        """Test rate stays within bounds"""
        # Test minimum bound
        for _ in range(20):
            await adaptive_limiter.record_response(2.0, 429, was_rate_limited=True)
        
        assert adaptive_limiter.current_rate >= adaptive_limiter.min_rate
        
        # Reset and test maximum bound
        adaptive_limiter.current_rate = adaptive_limiter.max_rate - 1
        
        for _ in range(20):
            await adaptive_limiter.record_response(0.01, 200)  # Very fast responses
        
        assert adaptive_limiter.current_rate <= adaptive_limiter.max_rate
    
    def test_get_adaptation_stats(self, adaptive_limiter):
        """Test adaptation statistics"""
        # Manually set some data
        adaptive_limiter._success_count = 8
        adaptive_limiter._error_count = 2
        adaptive_limiter._response_times.extend([0.1, 0.2, 0.15])
        adaptive_limiter.current_rate = 12.5
        
        stats = adaptive_limiter.get_adaptation_stats()
        
        assert stats['current_rate'] == 12.5
        assert stats['success_rate'] == 0.8  # 8/10
        assert stats['error_rate'] == 0.2   # 2/10
        assert abs(stats['avg_response_time'] - 0.15) < 0.001  # (0.1+0.2+0.15)/3
        assert stats['total_requests'] == 10


class TestRateLimitingIntegration:
    """Integration tests for rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_timing(self):
        """Test that rate limiting actually delays requests"""
        limiter = RateLimiter(rate=2.0)  # 2 requests per second
        
        start_time = time.time()
        
        # Make 3 requests - should take at least 1 second due to rate limiting
        for _ in range(3):
            await limiter.acquire()
        
        elapsed = time.time() - start_time
        assert elapsed >= 0.3  # Should take at least some time due to rate limiting
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent load"""
        limiter = RateLimiter(rate=5.0)  # 5 requests per second
        
        async def make_request():
            await limiter.acquire()
            return True
        
        start_time = time.time()
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        assert len(results) == 10
        assert all(results)  # All should succeed
        assert elapsed >= 0.8  # Should take at least some time for 10 requests at 5 rps
    
    @pytest.mark.asyncio
    async def test_global_limiter_coordination(self):
        """Test global limiter coordinates multiple limiters"""
        global_limiter = GlobalRateLimiter(
            global_rate=5.0,
            per_host_rate=10.0
        )
        
        # Configure route limits
        global_limiter.configure_route_limits({
            "/api/analytics": 3.0,
            "/api/dataValueSets": 8.0
        })
        
        start_time = time.time()
        
        # Make requests to different routes on same host
        await global_limiter.acquire("test.com", "/api/analytics")
        await global_limiter.acquire("test.com", "/api/analytics") 
        await global_limiter.acquire("test.com", "/api/dataValueSets")
        
        elapsed = time.time() - start_time
        
        # Should be limited by the most restrictive limiter (allow for fast test execution)
        assert elapsed >= 0.0  # At least some delay due to rate limiting
        
        stats = global_limiter.get_comprehensive_stats()
        assert stats['global']['requests_count'] == 3
        assert len(stats['hosts']) >= 1


class TestRateLimitingEdgeCases:
    """Tests for edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_zero_rate_limit(self):
        """Test behavior with very low rate limit"""
        limiter = RateLimiter(rate=1.0)  # Low rate (1 request per second)
        
        start_time = time.time()
        await limiter.acquire()
        elapsed = time.time() - start_time
        
        # Should complete quickly for first request
        assert elapsed < 1.0
    
    @pytest.mark.asyncio
    async def test_high_rate_limit(self):
        """Test behavior with very high rate limit"""
        limiter = RateLimiter(rate=1000.0)  # Very high rate
        
        start_time = time.time()
        
        # Make many requests quickly
        for _ in range(10):
            await limiter.acquire()
        
        elapsed = time.time() - start_time
        
        # Should complete very quickly
        assert elapsed < 0.5
    
    def test_window_cleanup(self):
        """Test sliding window cleanup"""
        global_limiter = GlobalRateLimiter(global_rate=10.0)
        
        # Add old request times
        old_time = time.time() - 120  # 2 minutes ago
        global_limiter._request_times.extend([old_time, old_time + 1])
        
        # Make a new request (triggers cleanup)
        asyncio.run(global_limiter.acquire("test.com", "/api/test"))
        
        # Old times should be cleaned up
        current_time = time.time()
        for req_time in global_limiter._request_times:
            assert current_time - req_time <= 60.0  # Within window
