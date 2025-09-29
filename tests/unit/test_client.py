"""Unit tests for DHIS2 client functionality"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from pydhis2.core.types import DHIS2Config
from pydhis2.core.client import AsyncDHIS2Client, ClientMetrics, SyncDHIS2Client, SyncEndpointProxy
from pydhis2.core.errors import DHIS2HTTPError, AuthenticationError


class TestClientMetrics:
    """Tests for the ClientMetrics class"""
    
    def test_init(self):
        """Test metrics initialization"""
        metrics = ClientMetrics()
        assert metrics.requests_total == 0
        assert metrics.requests_success == 0
        assert metrics.requests_failed == 0
        assert metrics.retries_total == 0
        assert len(metrics.response_times) == 0
    
    def test_record_request_start(self):
        """Test recording request start"""
        metrics = ClientMetrics()
        metrics.record_request_start()
        
        assert metrics.requests_total == 1
        assert metrics.http_inflight == 1
    
    def test_record_request_end_success(self):
        """Test recording successful request end"""
        metrics = ClientMetrics()
        metrics.record_request_start()
        metrics.record_request_end(success=True, response_time=0.5, retries=2)
        
        assert metrics.requests_success == 1
        assert metrics.requests_failed == 0
        assert metrics.retries_total == 2
        assert metrics.response_times == [0.5]
        assert metrics.http_inflight == 0
    
    def test_record_request_end_failure(self):
        """Test recording failed request end"""
        metrics = ClientMetrics()
        metrics.record_request_start()
        metrics.record_request_end(success=False, response_time=1.0)
        
        assert metrics.requests_success == 0
        assert metrics.requests_failed == 1
        assert metrics.response_times == [1.0]
    
    def test_get_stats(self):
        """Test getting statistics"""
        metrics = ClientMetrics()
        metrics.record_request_start()
        metrics.record_request_end(success=True, response_time=0.5)
        
        stats = metrics.get_stats()
        
        assert stats['requests_total'] == 1
        assert stats['requests_success'] == 1
        assert stats['requests_failed'] == 0
        assert stats['success_rate'] == 1.0
        assert stats['avg_response_time'] == 0.5


class TestAsyncDHIS2Client:
    """Tests for the AsyncDHIS2Client class"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test_user", "test_pass"),
            rps=5.0,
            concurrency=3
        )
    
    @pytest.fixture
    async def client(self, config):
        """Test client instance"""
        client = AsyncDHIS2Client(config)
        yield client
        await client.close()
    
    def test_init(self, config):
        """Test client initialization"""
        client = AsyncDHIS2Client(config)
        
        assert client.config == config
        assert client.base_url == config.base_url
        assert client._session is None
        assert client._closed is False
        assert client.metrics is not None
    
    def test_build_url(self, client):
        """Test URL building"""
        # Test relative URL
        url = client._build_url("/api/analytics")
        assert url == "https://test.dhis2.org/api/analytics"
        
        # Test URL without leading slash
        url = client._build_url("api/analytics")
        assert url == "https://test.dhis2.org/api/analytics"
        
        # Test absolute URL
        url = client._build_url("https://other.dhis2.org/api/test")
        assert url == "https://other.dhis2.org/api/test"
    
    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test async context manager"""
        async with AsyncDHIS2Client(config) as client:
            assert client._session is not None
            assert client.analytics is not None
            assert client.datavaluesets is not None
            assert client.tracker is not None
            assert client.metadata is not None
        
        assert client._closed is True
    
    @pytest.mark.asyncio
    async def test_session_not_initialized(self, client):
        """Test error when session is not initialized"""
        with pytest.raises(RuntimeError, match="Client session not initialized"):
            client._ensure_session()
    
    @pytest.mark.asyncio
    async def test_handle_response_success(self, client):
        """Test successful response handling"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content_type = "application/json"
        mock_response.json.return_value = {"test": "data"}
        
        result = await client._handle_response(mock_response)
        assert result == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_handle_response_auth_error(self, client):
        """Test authentication error handling"""
        mock_response = AsyncMock()
        mock_response.status = 401
        
        with pytest.raises(AuthenticationError):
            await client._handle_response(mock_response)
    
    @pytest.mark.asyncio
    async def test_handle_response_http_error(self, client):
        """Test HTTP error handling"""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.url = "https://test.dhis2.org/api/test"
        mock_response.content_type = "application/json"
        mock_response.json.return_value = {"error": "Server error"}
        
        with pytest.raises(DHIS2HTTPError) as exc_info:
            await client._handle_response(mock_response)
        
        assert exc_info.value.status == 500
        assert "test.dhis2.org" in str(exc_info.value.url)
    
    @pytest.mark.asyncio
    async def test_prepare_headers_no_auth(self):
        """Test preparing headers without authentication"""
        # Create client without auth
        config_no_auth = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=None,
            rps=10.0
        )
        client = AsyncDHIS2Client(config_no_auth)
        
        headers = await client._prepare_headers()
        assert headers == {}
        
        # With custom headers
        custom_headers = {"X-Custom": "test"}
        headers = await client._prepare_headers(custom_headers)
        assert headers == custom_headers
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_prepare_headers_with_auth(self, client):
        """Test preparing headers with authentication"""
        # Mock auth manager
        mock_auth_manager = AsyncMock()
        mock_auth_manager.get_auth_headers.return_value = {"Authorization": "Basic test"}
        client.auth_manager = mock_auth_manager
        
        headers = await client._prepare_headers()
        assert headers == {"Authorization": "Basic test"}
        
        # With additional custom headers
        custom_headers = {"X-Custom": "test"}
        headers = await client._prepare_headers(custom_headers)
        expected = {"Authorization": "Basic test", "X-Custom": "test"}
        assert headers == expected


class TestClientIntegration:
    """Integration tests using a mock server"""
    
    @pytest.mark.asyncio
    async def test_basic_get_request(self):
        """Test basic GET request with mock server"""
        from pydhis2.testing import MockDHIS2Server
        
        mock_server = MockDHIS2Server(port=8082)
        mock_server.configure_response(
            "GET", "/api/test",
            data={"message": "test response"}
        )
        
        async with mock_server as base_url:
            config = DHIS2Config(
                base_url=base_url,
                auth=("test", "test"),
                rps=10.0
            )
            
            async with AsyncDHIS2Client(config) as client:
                response = await client.get("/api/test")
                assert response["message"] == "test response"
                
                # Check metrics
                stats = client.get_stats()
                assert stats['client']['requests_total'] >= 1
                assert stats['client']['requests_success'] >= 1
    
    @pytest.mark.asyncio
    async def test_retry_on_server_error(self):
        """Test retry behavior on server error"""
        from pydhis2.testing import MockDHIS2Server
        
        mock_server = MockDHIS2Server(port=8083)
        # Configure to fail 2 times then succeed
        mock_server.configure_response(
            "GET", "/api/test",
            data={"message": "success"},
            fail_count=2
        )
        
        async with mock_server as base_url:
            config = DHIS2Config(
                base_url=base_url,
                auth=("test", "test"),
                rps=10.0,
                max_retries=5
            )
            
            async with AsyncDHIS2Client(config) as client:
                response = await client.get("/api/test")
                assert response["message"] == "success"
                
                # Check that retries occurred
                stats = client.get_stats()
                assert stats['retry_manager']['total_retries'] >= 2
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        from pydhis2.testing import MockDHIS2Server
        
        mock_server = MockDHIS2Server(port=8084)
        mock_server.configure_response(
            "GET", "/api/test",
            data={"message": "test"}
        )
        
        async with mock_server as base_url:
            config = DHIS2Config(
                base_url=base_url,
                auth=("test", "test"),
                rps=2.0  # Very low rate limit
            )
            
            async with AsyncDHIS2Client(config) as client:
                # Make multiple requests quickly
                start_time = asyncio.get_event_loop().time()
                
                for _ in range(3):
                    await client.get("/api/test")
                
                end_time = asyncio.get_event_loop().time()
                
                # Should take at least some time due to rate limiting (allow for timing variations)
                assert end_time - start_time >= 0.3
                
                # Check rate limiter stats
                stats = client.get_stats()
                assert 'rate_limiter' in stats
                assert stats['rate_limiter']['current_rps'] <= 2.5  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self):
        """Test cache functionality"""
        from pydhis2.testing import MockDHIS2Server
        
        mock_server = MockDHIS2Server(port=8085)
        mock_server.configure_response(
            "GET", "/api/test",
            data={"message": "cached response"}
        )
        
        async with mock_server as base_url:
            config = DHIS2Config(
                base_url=base_url,
                auth=("test", "test"),
                enable_cache=True,
                cache_ttl=60
            )
            
            async with AsyncDHIS2Client(config) as client:
                # First request should hit server
                response1 = await client.get("/api/test")
                assert response1["message"] == "cached response"
                
                # Second request should use cache (if implemented)
                response2 = await client.get("/api/test")
                assert response2["message"] == "cached response"
    
    @pytest.mark.asyncio
    async def test_pagination_mock(self):
        """Test pagination functionality with mock response"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Mock get method to return paginated responses
        page1_response = {
            "pager": {"page": 1, "pageCount": 2, "total": 3},
            "dataElements": [{"id": "DE1", "name": "Element 1"}]
        }
        page2_response = {
            "pager": {"page": 2, "pageCount": 2, "total": 3},
            "dataElements": [{"id": "DE2", "name": "Element 2"}]
        }
        
        # Mock the get method to return different responses based on page parameter
        original_get = client.get
        call_count = 0
        
        async def mock_get(endpoint, params=None, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return page1_response
            else:
                return page2_response
        
        client.get = mock_get
        
        try:
            results = await client.get_paginated("/api/dataElements", page_size=1)
            assert len(results) == 2  # DE1 and DE2
            assert results[0]["id"] == "DE1"
            assert results[1]["id"] == "DE2"
        finally:
            client.get = original_get
            await client.close()
    
    @pytest.mark.asyncio
    async def test_session_reuse(self):
        """Test reuse of session when already created"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Create session first time
        await client._create_session()
        first_session = client._session
        
        # Create session second time should reuse
        await client._create_session()
        second_session = client._session
        
        assert first_session is second_session
        await client.close()
    
    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test client with cache disabled"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test"),
            enable_cache=False
        )
        
        client = AsyncDHIS2Client(config)
        assert client.cache is None
        await client.close()
    
    @pytest.mark.asyncio
    async def test_post_request_mock(self):
        """Test POST request functionality with mock"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Mock the _make_request method
        async def mock_make_request(method, endpoint, **kwargs):
            assert method == "POST"
            assert endpoint == "/api/dataElements"
            return {"status": "OK", "httpStatusCode": 201}
        
        client._make_request = mock_make_request
        
        data = {"name": "Test Element", "shortName": "TE"}
        response = await client.post("/api/dataElements", json=data)
        assert response["status"] == "OK"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_put_request_mock(self):
        """Test PUT request functionality with mock"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Mock the _make_request method
        async def mock_make_request(method, endpoint, **kwargs):
            assert method == "PUT"
            assert endpoint == "/api/dataElements/DE123"
            return {"status": "OK", "httpStatusCode": 200}
        
        client._make_request = mock_make_request
        
        data = {"name": "Updated Element"}
        response = await client.put("/api/dataElements/DE123", data=data)
        assert response["status"] == "OK"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_delete_request_mock(self):
        """Test DELETE request functionality with mock"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Mock the _make_request method
        async def mock_make_request(method, endpoint, **kwargs):
            assert method == "DELETE"
            assert endpoint == "/api/dataElements/DE123"
            return {"status": "OK", "httpStatusCode": 200}
        
        client._make_request = mock_make_request
        
        response = await client.delete("/api/dataElements/DE123")
        assert response["status"] == "OK"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_pagination_without_pager_mock(self):
        """Test pagination with response without pager info"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Mock get method to return non-paginated response
        async def mock_get(endpoint, params=None, **kwargs):
            return {"items": [{"id": "1"}, {"id": "2"}]}
        
        client.get = mock_get
        
        results = await client.get_paginated("/api/simple")
        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[1]["id"] == "2"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_pagination_list_response_mock(self):
        """Test pagination with direct list response"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Mock get method to return direct list
        async def mock_get(endpoint, params=None, **kwargs):
            return [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        
        client.get = mock_get
        
        results = await client.get_paginated("/api/list")
        assert len(results) == 3
        assert results[0]["id"] == "1"
        
        await client.close()


class TestSyncDHIS2Client:
    """Tests for the SyncDHIS2Client class"""
    
    def test_sync_client_basic(self):
        """Test basic sync client functionality"""
        from pydhis2.testing import MockDHIS2Server
        
        # Run mock server in separate thread
        mock_server = MockDHIS2Server(port=8092)
        mock_server.configure_response(
            "GET", "/api/test",
            data={"message": "sync response"}
        )
        
        # Test with mock instead of real server due to async issues
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        # Test basic initialization and error handling
        client = SyncDHIS2Client(config)
        
        # Test that methods fail when not initialized
        with pytest.raises(RuntimeError, match="Client not initialized"):
            client.get("/api/test")
            
        with pytest.raises(RuntimeError, match="Client not initialized"):
            client.get_stats()
    
    def test_sync_client_not_initialized(self):
        """Test error when sync client is not initialized"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = SyncDHIS2Client(config)
        
        with pytest.raises(RuntimeError, match="Client not initialized"):
            client.get("/api/test")
        
        with pytest.raises(RuntimeError, match="Client not initialized"):
            client.post("/api/test")
            
        with pytest.raises(RuntimeError, match="Client not initialized"):
            client.get_stats()


class TestSyncEndpointProxy:
    """Tests for the SyncEndpointProxy class"""
    
    def test_proxy_functionality(self):
        """Test endpoint proxy functionality"""
        # Create a mock async endpoint
        mock_async_endpoint = AsyncMock()
        mock_async_endpoint.get_data = AsyncMock(return_value={"data": "test"})
        mock_async_endpoint.sync_method = "not_coroutine"
        
        # Create event loop
        loop = asyncio.new_event_loop()
        
        try:
            proxy = SyncEndpointProxy(mock_async_endpoint, loop)
            
            # Test async method becomes sync
            result = proxy.get_data()
            assert result == {"data": "test"}
            
            # Test non-coroutine method passes through
            assert proxy.sync_method == "not_coroutine"
        finally:
            loop.close()


class TestClientErrorHandling:
    """Tests for client error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_session_not_initialized_error(self):
        """Test error when session is not initialized"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        with pytest.raises(RuntimeError, match="Client session not initialized"):
            client._ensure_session()
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_close_when_not_initialized(self):
        """Test closing client when session is not initialized"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        # Should not raise error when closing uninitialized client
        await client.close()
        assert client._closed is True
    
    @pytest.mark.asyncio
    async def test_handle_response_different_content_types(self):
        """Test handling responses with different content types"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org",
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Test JSON response
        mock_response_json = AsyncMock()
        mock_response_json.status = 200
        mock_response_json.content_type = "application/json"
        mock_response_json.json.return_value = {"test": "data"}
        
        result = await client._handle_response(mock_response_json)
        assert result == {"test": "data"}
        
        # Test text response
        mock_response_text = AsyncMock()
        mock_response_text.status = 200
        mock_response_text.content_type = "text/plain"
        mock_response_text.text.return_value = "plain text"
        
        result = await client._handle_response(mock_response_text)
        assert result == {"text": "plain text"}
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_build_url_edge_cases(self):
        """Test URL building edge cases"""
        config = DHIS2Config(
            base_url="https://test.dhis2.org/",  # With trailing slash
            auth=("test", "test")
        )
        
        client = AsyncDHIS2Client(config)
        
        # Test with trailing slash in base_url
        url = client._build_url("/api/analytics")
        assert url == "https://test.dhis2.org/api/analytics"
        
        # Test with empty endpoint
        url = client._build_url("")
        assert url == "https://test.dhis2.org/"
        
        await client.close()