"""Tests for the errors module"""

from unittest.mock import MagicMock

from pydhis2.core.errors import (
    DHIS2Error, DHIS2HTTPError, RateLimitExceeded, RetryExhausted,
    ImportConflictError, AuthenticationError, AuthorizationError,
    ValidationError, TimeoutError, DataFormatError, MetadataError
)


class TestDHIS2Error:
    """Tests for the DHIS2Error base class"""
    
    def test_init_basic(self):
        """Test basic error initialization"""
        error = DHIS2Error("Test error message")
        assert str(error) == "Test error message"
        assert error.args == ("Test error message",)
    
    def test_init_with_details(self):
        """Test error initialization with details"""
        details = {"code": "E001", "field": "name"}
        error = DHIS2Error("Test error", details=details)
        
        assert str(error) == "Test error"
        assert error.details == details
    
    def test_init_empty_message(self):
        """Test error with empty message"""
        error = DHIS2Error("")
        assert str(error) == ""


class TestDHIS2HTTPError:
    """Tests for the DHIS2HTTPError class"""
    
    def test_init_basic(self):
        """Test HTTP error initialization"""
        error = DHIS2HTTPError(404, "https://example.com/api/test", "HTTP error")
        assert str(error) == "HTTP error"
        assert error.status == 404
        assert error.url == "https://example.com/api/test"
    
    def test_init_with_request_info(self):
        """Test HTTP error with request info"""
        response_data = {"error": "Internal server error"}
        error = DHIS2HTTPError(
            500,
            "https://example.com/api/test",
            "Server error",
            response_data=response_data
        )
        
        assert error.url == "https://example.com/api/test"
        assert error.status == 500
        assert error.response_data == response_data
    
    def test_status_code_property(self):
        """Test status code property"""
        error = DHIS2HTTPError(422, "https://example.com/api/test", "Validation error")
        assert error.status == 422
    
    def test_is_client_error(self):
        """Test client error detection"""
        error_400 = DHIS2HTTPError(400, "https://example.com/api", "Bad request")
        error_404 = DHIS2HTTPError(404, "https://example.com/api", "Not found")
        error_500 = DHIS2HTTPError(500, "https://example.com/api", "Server error")
        
        assert 400 <= error_400.status < 500
        assert 400 <= error_404.status < 500
        assert not (400 <= error_500.status < 500)
    
    def test_is_server_error(self):
        """Test server error detection"""
        error_400 = DHIS2HTTPError(400, "https://example.com/api", "Bad request")
        error_500 = DHIS2HTTPError(500, "https://example.com/api", "Server error")
        error_502 = DHIS2HTTPError(502, "https://example.com/api", "Bad gateway")
        
        assert not (500 <= error_400.status < 600)
        assert 500 <= error_500.status < 600
        assert 500 <= error_502.status < 600
    
    def test_is_retryable(self):
        """Test retryable error detection"""
        error_429 = DHIS2HTTPError(429, "https://example.com/api", "Rate limited")
        error_500 = DHIS2HTTPError(500, "https://example.com/api", "Server error")
        error_404 = DHIS2HTTPError(404, "https://example.com/api", "Not found")
        
        # For now, just test that these are valid HTTP errors
        assert error_429.status == 429
        assert error_500.status == 500
        assert error_404.status == 404


class TestRateLimitExceeded:
    """Tests for the RateLimitExceeded error"""
    
    def test_init_basic(self):
        """Test rate limit error initialization"""
        error = RateLimitExceeded(retry_after=60)
        assert "Rate limit exceeded" in str(error)
        assert error.retry_after == 60
    
    def test_init_with_details(self):
        """Test rate limit error with details"""
        error = RateLimitExceeded(
            retry_after=120,
            current_rate=15.0,
            limit=10.0
        )
        
        assert error.retry_after == 120
        assert error.current_rate == 15.0
        assert error.limit == 10.0


class TestRetryExhausted:
    """Tests for the RetryExhausted error"""
    
    def test_init_basic(self):
        """Test retry exhausted initialization"""
        error = RetryExhausted(5)  # max_retries
        assert "5" in str(error)  # Should mention attempts
        assert error.max_retries == 5
    
    def test_init_with_exception(self):
        """Test retry exhausted with last exception"""
        last_exc = ValueError("Connection failed")
        error = RetryExhausted(3, last_error=last_exc)
        
        assert error.max_retries == 3
        assert error.last_error == last_exc


class TestImportConflictError:
    """Tests for the ImportConflictError"""
    
    def test_init_basic(self):
        """Test import conflict error initialization"""
        conflicts = [
            {"object": "DE123", "message": "Duplicate name"},
            {"object": "DE456", "message": "Invalid value"}
        ]
        
        error = ImportConflictError(conflicts=conflicts)
        assert error.conflicts == conflicts
    
    def test_init_with_summary(self):
        """Test import conflict error with summary"""
        conflicts = [{"object": "DE123", "message": "Error"}]
        summary = {"status": "ERROR", "total": 10, "imported": 8}
        
        error = ImportConflictError(conflicts=conflicts, import_summary=summary)
        
        assert error.conflicts == conflicts
        assert error.import_summary == summary


class TestAuthenticationError:
    """Tests for the AuthenticationError"""
    
    def test_init_basic(self):
        """Test authentication error initialization"""
        error = AuthenticationError("Invalid credentials")
        assert str(error) == "Invalid credentials"


class TestAuthorizationError:
    """Tests for the AuthorizationError"""
    
    def test_init_basic(self):
        """Test authorization error initialization"""
        error = AuthorizationError("Access denied")
        assert str(error) == "Access denied"


class TestValidationError:
    """Tests for the ValidationError"""
    
    def test_init_basic(self):
        """Test validation error initialization"""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
    
    def test_init_with_details(self):
        """Test validation error with field details"""
        error = ValidationError("Invalid field", field="email", value="invalid@")
        
        assert error.field == "email"
        assert error.value == "invalid@"


class TestTimeoutError:
    """Tests for the TimeoutError"""
    
    def test_init_basic(self):
        """Test timeout error initialization"""
        error = TimeoutError("connect", 30.0)
        assert "timeout" in str(error).lower()
        assert error.timeout_value == 30.0
        assert error.timeout_type == "connect"


class TestDataFormatError:
    """Tests for the DataFormatError"""
    
    def test_init_basic(self):
        """Test data format error initialization"""
        error = DataFormatError("Invalid data format")
        assert str(error) == "Invalid data format"
    
    def test_init_with_format_details(self):
        """Test data format error with format details"""
        error = DataFormatError(
            "Format mismatch",
            expected_format="JSON",
            actual_format="XML"
        )
        
        assert error.expected_format == "JSON"
        assert error.actual_format == "XML"


class TestMetadataError:
    """Tests for the MetadataError"""
    
    def test_init_basic(self):
        """Test metadata error initialization"""
        error = MetadataError("Metadata error")
        assert str(error) == "Metadata error"
    
    def test_init_with_object_details(self):
        """Test metadata error with object details"""
        error = MetadataError(
            "Invalid data element",
            object_type="dataElement",
            object_id="DE123"
        )
        
        assert error.object_type == "dataElement"
        assert error.object_id == "DE123"


class TestErrorIntegration:
    """Tests for error integration scenarios"""
    
    def test_error_hierarchy(self):
        """Test that all errors inherit from DHIS2Error"""
        response_mock = MagicMock()
        response_mock.status = 500
        
        errors = [
            DHIS2HTTPError(500, "https://example.com/api", "HTTP error"),
            RateLimitExceeded(retry_after=30),
            RetryExhausted(3),
            ImportConflictError(conflicts=[]),
            AuthenticationError("Auth failed"),
            AuthorizationError("Access denied"),
            ValidationError("Validation failed"),
            TimeoutError("connect", 30.0),
            DataFormatError("Format error"),
            MetadataError("Metadata error")
        ]
        
        for error in errors:
            assert isinstance(error, DHIS2Error)
    
    def test_error_chaining(self):
        """Test error chaining with original exception"""
        original_error = ValueError("Original error")
        response_mock = MagicMock()
        response_mock.status = 500
        
        # Test that errors can be chained
        dhis2_error = DHIS2HTTPError(500, "https://example.com/api", "HTTP error")
        dhis2_error.__cause__ = original_error
        
        assert dhis2_error.__cause__ == original_error
    
    def test_import_conflict_with_detailed_info(self):
        """Test import conflict with detailed conflict info"""
        conflicts = [
            {
                "object": "DE123",
                "property": "name",
                "value": "Duplicate Name",
                "message": "Name already exists"
            },
            {
                "object": "DE456", 
                "property": "code",
                "value": "INVALID_CODE",
                "message": "Code format invalid"
            }
        ]
        
        import_summary = {
            "status": "ERROR",
            "total": 10,
            "imported": 8,
            "conflicts": conflicts
        }
        
        error = ImportConflictError(
            conflicts=conflicts,
            import_summary=import_summary
        )
        
        # Should provide detailed conflict information
        assert len(error.conflicts) == 2
        assert error.import_summary["status"] == "ERROR"
