"""Unit tests for retry functionality"""

import pytest
import asyncio
import aiohttp
from unittest.mock import MagicMock
from pydhis2.core.retry import (
    RetryConfig, 
    RetryManager, 
    ExponentialBackoffStrategy,
    LinearBackoffStrategy,
    FixedDelayStrategy,
    RetryAttempt
)
from pydhis2.core.errors import RetryExhausted


class TestRetryConfig:
    """Tests for the RetryConfig class"""
    
    def test_default_config(self):
        """Test default retry configuration"""
        config = RetryConfig()
        
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True
        assert 429 in config.retry_on_status
        assert 500 in config.retry_on_status
    
    def test_custom_config(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            retry_on_status={503, 504}
        )
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.retry_on_status == {503, 504}


class TestRetryStrategies:
    """Tests for retry strategy implementations"""
    
    def test_exponential_backoff_strategy(self):
        """Test exponential backoff calculation"""
        strategy = ExponentialBackoffStrategy()
        
        # Test without jitter (deterministic)
        wait_time = strategy.calculate_wait_time(
            attempt=1, base_delay=1.0, max_delay=60.0, 
            backoff_factor=2.0, jitter=False
        )
        assert wait_time == 1.0  # 1.0 * (2.0 ^ 0)
        
        wait_time = strategy.calculate_wait_time(
            attempt=2, base_delay=1.0, max_delay=60.0,
            backoff_factor=2.0, jitter=False
        )
        assert wait_time == 2.0  # 1.0 * (2.0 ^ 1)
        
        wait_time = strategy.calculate_wait_time(
            attempt=3, base_delay=1.0, max_delay=60.0,
            backoff_factor=2.0, jitter=False
        )
        assert wait_time == 4.0  # 1.0 * (2.0 ^ 2)
    
    def test_exponential_backoff_max_delay(self):
        """Test exponential backoff respects max delay"""
        strategy = ExponentialBackoffStrategy()
        
        wait_time = strategy.calculate_wait_time(
            attempt=10, base_delay=1.0, max_delay=5.0,
            backoff_factor=2.0, jitter=False
        )
        assert wait_time == 5.0  # Should be capped at max_delay
    
    def test_linear_backoff_strategy(self):
        """Test linear backoff calculation"""
        strategy = LinearBackoffStrategy()
        
        wait_time = strategy.calculate_wait_time(
            attempt=3, base_delay=1.0, max_delay=60.0,
            backoff_factor=2.0, jitter=False
        )
        assert wait_time == 3.0  # base_delay * attempt
    
    def test_fixed_delay_strategy(self):
        """Test fixed delay calculation"""
        strategy = FixedDelayStrategy()
        
        for attempt in [1, 2, 5, 10]:
            wait_time = strategy.calculate_wait_time(
                attempt=attempt, base_delay=2.0, max_delay=60.0,
                backoff_factor=2.0, jitter=False
            )
            assert wait_time == 2.0  # Always base_delay


class TestRetryManager:
    """Tests for the RetryManager class"""
    
    @pytest.fixture
    def retry_config(self):
        """Test retry configuration"""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
            retry_on_status={500, 503},
            retry_on_exceptions={aiohttp.ClientError, asyncio.TimeoutError, ConnectionError}
        )
    
    @pytest.fixture
    def retry_manager(self, retry_config):
        """Test retry manager"""
        return RetryManager(retry_config)
    
    def test_init(self, retry_manager):
        """Test retry manager initialization"""
        assert retry_manager.config.max_attempts == 3
        assert retry_manager.total_attempts == 0
        assert retry_manager.total_retries == 0
    
    def test_should_retry_exception(self, retry_manager):
        """Test should_retry with exceptions"""
        # Should retry on configured exception types
        assert retry_manager.should_retry(1, exception=aiohttp.ClientError())
        assert retry_manager.should_retry(1, exception=asyncio.TimeoutError())
        assert retry_manager.should_retry(1, exception=ConnectionError())
        
        # Should not retry on other exception types
        assert not retry_manager.should_retry(1, exception=ValueError())
        
        # Should not retry if max attempts reached
        assert not retry_manager.should_retry(3, exception=aiohttp.ClientError())
    
    def test_should_retry_status_code(self, retry_manager):
        """Test should_retry with HTTP status codes"""
        mock_response = MagicMock()
        
        # Should retry on configured status codes
        mock_response.status = 500
        assert retry_manager.should_retry(1, response=mock_response)
        
        mock_response.status = 503
        assert retry_manager.should_retry(1, response=mock_response)
        
        # Should not retry on other status codes
        mock_response.status = 200
        assert not retry_manager.should_retry(1, response=mock_response)
        
        mock_response.status = 404
        assert not retry_manager.should_retry(1, response=mock_response)
    
    def test_calculate_wait_time(self, retry_manager):
        """Test wait time calculation"""
        # Test with different strategies
        wait_time = retry_manager.calculate_wait_time(1, strategy='exponential')
        assert wait_time >= 0
        
        wait_time = retry_manager.calculate_wait_time(1, strategy='linear')
        assert wait_time >= 0
        
        wait_time = retry_manager.calculate_wait_time(1, strategy='fixed')
        assert wait_time >= 0
    
    def test_extract_retry_after(self, retry_manager):
        """Test Retry-After header extraction"""
        mock_response = MagicMock()
        
        # Test with valid Retry-After header
        mock_response.headers = {'Retry-After': '30'}
        retry_after = retry_manager.extract_retry_after(mock_response)
        assert retry_after == 30.0
        
        # Test without Retry-After header
        mock_response.headers = {}
        retry_after = retry_manager.extract_retry_after(mock_response)
        assert retry_after is None
        
        # Test with invalid value
        mock_response.headers = {'Retry-After': 'invalid'}
        retry_after = retry_manager.extract_retry_after(mock_response)
        assert retry_after is None
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, retry_manager):
        """Test successful execution without retries"""
        async def successful_func():
            return "success"
        
        result = await retry_manager.execute_with_retry(successful_func)
        assert result == "success"
        assert retry_manager.total_attempts == 1
        assert retry_manager.total_retries == 0
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_eventual_success(self, retry_manager):
        """Test execution that succeeds after retries"""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiohttp.ClientError("Temporary error")
            return "success"
        
        result = await retry_manager.execute_with_retry(flaky_func)
        assert result == "success"
        assert retry_manager.total_attempts == 3
        assert retry_manager.total_retries == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausted(self, retry_manager):
        """Test retry exhaustion"""
        async def always_fails():
            raise aiohttp.ClientError("Always fails")
        
        # Check that ClientError should be retried
        should_retry = retry_manager.should_retry(1, exception=aiohttp.ClientError("test"))
        assert should_retry, "ClientError should be retryable"
        
        with pytest.raises(RetryExhausted) as exc_info:
            await retry_manager.execute_with_retry(always_fails)
        
        assert exc_info.value.max_retries == 3
        assert retry_manager.total_attempts == 3
        assert retry_manager.total_retries == 2  # 3 attempts = 2 retries
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_non_retryable_error(self, retry_manager):
        """Test non-retryable errors are not retried"""
        async def non_retryable_error():
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            await retry_manager.execute_with_retry(non_retryable_error)
        
        # Should only attempt once
        assert retry_manager.total_attempts == 1
        assert retry_manager.total_retries == 0
    
    def test_get_stats(self, retry_manager):
        """Test statistics collection"""
        # Manually set some stats
        retry_manager.total_attempts = 10
        retry_manager.total_retries = 3
        retry_manager.total_wait_time = 5.0
        retry_manager.attempts_by_status = {500: 2, 503: 1}
        
        stats = retry_manager.get_stats()
        
        assert stats['total_attempts'] == 10
        assert stats['total_retries'] == 3
        assert stats['total_wait_time'] == 5.0
        assert stats['retry_rate'] == 0.3  # 3/10
        assert stats['avg_wait_time'] == 5.0/3  # 5.0/3
        assert stats['attempts_by_status'] == {500: 2, 503: 1}
    
    def test_reset_stats(self, retry_manager):
        """Test statistics reset"""
        # Set some stats
        retry_manager.total_attempts = 10
        retry_manager.total_retries = 3
        
        # Reset
        retry_manager.reset_stats()
        
        assert retry_manager.total_attempts == 0
        assert retry_manager.total_retries == 0
        assert retry_manager.total_wait_time == 0.0
        assert len(retry_manager.attempts_by_status) == 0


class TestRetryAttempt:
    """Tests for the RetryAttempt data class"""
    
    def test_duration_calculation(self):
        """Test duration property calculation"""
        attempt = RetryAttempt(
            attempt_number=1,
            start_time=100.0,
            end_time=102.5
        )
        
        assert attempt.duration == 2.5
    
    def test_duration_none_when_no_end_time(self):
        """Test duration is None when no end time"""
        attempt = RetryAttempt(
            attempt_number=1,
            start_time=100.0
        )
        
        assert attempt.duration is None
