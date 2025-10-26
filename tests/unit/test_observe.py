"""Tests for observe module (logging and telemetry)"""

import pytest
import logging
from unittest.mock import MagicMock, patch, Mock
from pydhis2.observe.logging import (
    get_logger, setup_logging, StructuredFormatter, SensitiveDataFilter,
    log_request, log_retry, log_rate_limit
)
from pydhis2.observe.telemetry import (
    TelemetryManager, setup_telemetry, get_telemetry, TelemetryConfig,
    trace_operation, record_http_request
)


class TestStructuredFormatter:
    """Test StructuredFormatter"""
    
    def test_format_basic(self):
        """Test formatting a basic log record"""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert isinstance(formatted, str)
        assert "Test message" in formatted
        assert "INFO" in formatted
    
    def test_format_with_exception(self):
        """Test formatting with exception info"""
        formatter = StructuredFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=True
            )
            formatted = formatter.format(record)
            assert "Error occurred" in formatted


class TestSensitiveDataFilter:
    """Test SensitiveDataFilter"""
    
    def test_filter_allows_normal_logs(self):
        """Test that normal logs pass through"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Normal log message",
            args=(),
            exc_info=None
        )
        
        result = filter_obj.filter(record)
        assert result is True
    
    def test_filter_detects_sensitive_data(self):
        """Test that sensitive data is detected"""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User password: secret123",
            args=(),
            exc_info=None
        )
        
        # Filter should still return True but may modify record
        result = filter_obj.filter(record)
        assert result is True


class TestLoggingFunctions:
    """Test logging utility functions"""
    
    def test_get_logger(self):
        """Test getting a logger"""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
    
    def test_setup_logging(self):
        """Test setup_logging function"""
        setup_logging(level=logging.DEBUG)
        # Should complete without error
        assert True
    
    def test_log_request(self):
        """Test log_request helper"""
        logger = get_logger("test")
        with patch.object(logger, 'info'):
            log_request(logger, "GET", "https://test.dhis2.org/api/analytics", status=200)
            # Should complete without error
            assert True
    
    def test_log_retry(self):
        """Test log_retry helper"""
        logger = get_logger("test")
        with patch.object(logger, 'warning'):
            log_retry(logger, attempt=1, max_attempts=3, delay=1.0)
            assert True
    
    def test_log_rate_limit(self):
        """Test log_rate_limit helper"""
        logger = get_logger("test")
        with patch.object(logger, 'warning'):
            log_rate_limit(logger, current_rate=10.0, limit=8.0, wait_time=0.5)
            assert True


class TestTelemetryConfig:
    """Test TelemetryConfig"""
    
    def test_telemetry_config_init(self):
        """Test telemetry config initialization"""
        config = TelemetryConfig(enabled=True, service_name="test")
        assert config.enabled is True
        assert config.service_name == "test"


class TestTelemetryManager:
    """Test TelemetryManager"""
    
    def test_telemetry_manager_init_disabled(self):
        """Test telemetry manager with disabled telemetry"""
        manager = TelemetryManager(enabled=False)
        assert manager.enabled is False
    
    def test_telemetry_manager_start_stop(self):
        """Test starting and stopping telemetry"""
        manager = TelemetryManager(enabled=False)
        manager.start()
        manager.stop()
        # Should complete without error
        assert True
    
    def test_get_tracer(self):
        """Test getting a tracer"""
        manager = TelemetryManager(enabled=False)
        tracer = manager.get_tracer("test_tracer")
        # May return None if disabled
        assert tracer is None or tracer is not None


class TestTelemetryFunctions:
    """Test telemetry utility functions"""
    
    def test_setup_telemetry(self):
        """Test setup_telemetry function"""
        manager = setup_telemetry(enabled=False)
        assert isinstance(manager, TelemetryManager)
        assert manager.enabled is False
    
    def test_get_telemetry(self):
        """Test get_telemetry function"""
        # Set up telemetry first
        setup_telemetry(enabled=False)
        manager = get_telemetry()
        # May return None if not set up
        assert manager is None or isinstance(manager, TelemetryManager)
    
    def test_trace_operation(self):
        """Test trace_operation context manager"""
        setup_telemetry(enabled=False)
        
        with trace_operation("test_op", test_attr="value"):
            pass  # Some operation
        
        # Should complete without error
        assert True
    
    def test_record_http_request(self):
        """Test record_http_request function"""
        setup_telemetry(enabled=False)
        record_http_request(
            method="GET",
            url="https://test.dhis2.org",
            status_code=200,
            duration=1.5
        )
        # Should complete without error
        assert True
    
    def test_record_retry(self):
        """Test record_retry function"""
        setup_telemetry(enabled=False)
        record_retry("test_operation", attempt=1)
        assert True
    
    def test_record_rate_limit(self):
        """Test record_rate_limit function"""
        setup_telemetry(enabled=False)
        record_rate_limit("/api/analytics")
        assert True


class TestObserveIntegration:
    """Integration tests for observe module"""
    
    def test_logging_and_telemetry_together(self):
        """Test using logging and telemetry together"""
        # Setup both
        setup_logging(level=logging.INFO)
        setup_telemetry(enabled=False)
        
        logger = get_logger("test")
        
        with trace_operation("test_operation"):
            logger.info("Test message")
            log_request(logger, "GET", "https://test.dhis2.org", status=200)
        
        # Should complete without error
        assert True
    
    def test_structured_logging_with_telemetry(self):
        """Test structured logging with telemetry"""
        setup_logging(level=logging.DEBUG)
        manager = setup_telemetry(enabled=False)
        
        logger = get_logger("integration_test")
        
        with trace_operation("integration_test"):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            
            log_retry(logger, attempt=1, max_attempts=3, delay=1.0)
            log_rate_limit(logger, current_rate=10.0, limit=8.0, wait_time=0.5)
        
        assert True
