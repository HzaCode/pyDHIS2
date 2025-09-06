"""Core HTTP client - Async-first with connection pooling, retry, and rate limiting"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse
import logging

import aiohttp
from pydantic import BaseModel

from pydhis2.core.types import DHIS2Config, ExportFormat
from pydhis2.core.errors import (
    DHIS2HTTPError,
    TimeoutError as DHIS2TimeoutError,
    AuthenticationError,
    AllPagesFetchError,  # Added
    format_dhis2_error,
)
from pydhis2.core.auth import AuthManager, create_auth_provider
from pydhis2.core.rate_limit import GlobalRateLimiter
from pydhis2.core.retry import RetryManager, RetryConfig
from pydhis2.core.cache import HTTPCache, CachedSession
from pydhis2.endpoints.analytics import AnalyticsEndpoint
from pydhis2.endpoints.datavaluesets import DataValueSetsEndpoint
from pydhis2.endpoints.tracker import TrackerEndpoint
from pydhis2.endpoints.metadata import MetadataEndpoint


logger = logging.getLogger(__name__)


class ClientMetrics:
    """Client metrics collection"""
    
    def __init__(self):
        self.requests_total = 0
        self.requests_success = 0
        self.requests_failed = 0
        self.retries_total = 0
        self.backoff_seconds_sum = 0.0
        self.http_inflight = 0
        self.response_times: List[float] = []
        self.start_time = time.time()
    
    def record_request_start(self) -> None:
        """Record request start"""
        self.requests_total += 1
        self.http_inflight += 1
    
    def record_request_end(
        self,
        success: bool,
        response_time: float,
        retries: int = 0,
        backoff_time: float = 0.0
    ) -> None:
        """Record request end"""
        self.http_inflight -= 1
        self.response_times.append(response_time)
        
        if success:
            self.requests_success += 1
        else:
            self.requests_failed += 1
        
        self.retries_total += retries
        self.backoff_seconds_sum += backoff_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        uptime = time.time() - self.start_time
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        
        return {
            'uptime_seconds': uptime,
            'requests_total': self.requests_total,
            'requests_success': self.requests_success,
            'requests_failed': self.requests_failed,
            'success_rate': (
                self.requests_success / self.requests_total
                if self.requests_total > 0 else 0
            ),
            'retries_total': self.retries_total,
            'avg_retries_per_request': (
                self.retries_total / self.requests_total
                if self.requests_total > 0 else 0
            ),
            'backoff_seconds_sum': self.backoff_seconds_sum,
            'http_inflight': self.http_inflight,
            'avg_response_time': avg_response_time,
            'rps': self.requests_total / uptime if uptime > 0 else 0,
        }


class AsyncDHIS2Client:
    """Async DHIS2 client"""
    
    def __init__(self, config: DHIS2Config):
        self.config = config
        self.base_url = config.base_url
        
        # Internal state
        self._session: Optional[aiohttp.ClientSession] = None
        self._cached_session: Optional[CachedSession] = None
        self._closed = False
        
        # Component initialization
        self.metrics = ClientMetrics()
        self._init_auth()
        self._init_rate_limiter()
        self._init_retry_manager()
        self._init_cache()
        
        # Endpoints
        self.analytics: Optional[AnalyticsEndpoint] = None
        self.datavaluesets: Optional[DataValueSetsEndpoint] = None
        self.tracker: Optional[TrackerEndpoint] = None
        self.metadata: Optional[MetadataEndpoint] = None
    
    def _init_auth(self) -> None:
        """Initialize authentication"""
        if self.config.auth:
            # Simplified auth provider creation, assuming basic auth
            from .auth import BasicAuthProvider
            auth_provider = BasicAuthProvider(username=self.config.auth[0], password=self.config.auth[1])
            self.auth_manager = AuthManager(auth_provider)
        else:
            self.auth_manager = None
    
    def _init_rate_limiter(self) -> None:
        """Initialize rate limiter"""
        self.rate_limiter = GlobalRateLimiter(
            global_rate=self.config.rps,
            per_host_rate=self.config.rps
        )
        
        # Configure limits for specific routes (optional)
        route_limits = {
            '/api/analytics': self.config.rps * 0.8,  # Analytics is usually heavier
            '/api/dataValueSets': self.config.rps * 1.2,  # DataValueSets can be slightly faster
            '/api/tracker': self.config.rps,
        }
        self.rate_limiter.configure_route_limits(route_limits)
    
    def _init_retry_manager(self) -> None:
        """Initialize retry manager"""
        retry_config = RetryConfig(
            max_attempts=self.config.max_retries,
            base_delay=self.config.retry_base_delay,
            backoff_factor=self.config.retry_backoff_factor,
            retry_on_status=set(self.config.retry_on_status),
            jitter=True # A good default
        )
        self.retry_manager = RetryManager(config=retry_config)
    
    def _init_cache(self) -> None:
        """Initialize cache"""
        if self.config.enable_cache:
            self.cache = HTTPCache(ttl=self.config.cache_ttl)
        else:
            self.cache = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._create_session()
        self._init_endpoints()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _create_session(self) -> None:
        """Create HTTP session"""
        if self._session is not None:
            return
        
        # Timeout configuration
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        # Connector configuration
        connector = aiohttp.TCPConnector(
            limit=self.config.concurrency,
            limit_per_host=self.config.concurrency,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )
        
        # Session creation
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.config.user_agent,
                'Accept': 'application/json',
            }
        )
        
        # Enable compression
        if self.config.compression:
            self._session.headers['Accept-Encoding'] = 'gzip, deflate'
        
        # Initialize cached session
        if self.cache:
            self._cached_session = CachedSession(
                session=self._session,
                cache=self.cache,
                enable_cache=self.config.enable_cache
            )
    
    def _init_endpoints(self) -> None:
        """Initialize endpoints"""
        self.analytics = AnalyticsEndpoint(self)
        self.datavaluesets = DataValueSetsEndpoint(self)
        self.tracker = TrackerEndpoint(self)
        self.metadata = MetadataEndpoint(self)
    
    async def close(self) -> None:
        """Close the client"""
        if self._closed:
            return
        
        if self._session:
            await self._session.close()
            self._session = None
        
        self._closed = True
    
    def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session exists"""
        if self._session is None:
            raise RuntimeError("Client session not initialized. Use 'async with' context.")
        return self._session
    
    async def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare request headers"""
        final_headers = {}
        
        # Authentication headers
        if self.auth_manager:
            auth_headers = await self.auth_manager.get_auth_headers()
            final_headers.update(auth_headers)
        
        # User-provided headers
        if headers:
            final_headers.update(headers)
        
        return final_headers
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL"""
        if endpoint.startswith('http'):
            return endpoint
        
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        return urljoin(self.base_url + '/', endpoint.lstrip('/'))
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle response"""
        try:
            # Check status code
            if response.status == 401:
                raise AuthenticationError("Authentication failed")
            
            # Read response content
            if response.content_type.startswith('application/json'):
                data = await response.json()
            else:
                text = await response.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = {'text': text}
            
            # Check for DHIS2 errors
            if response.status >= 400:
                error_msg = format_dhis2_error(data)
                raise DHIS2HTTPError(
                    status=response.status,
                    url=str(response.url),
                    message=error_msg,
                    response_data=data
                )
            
            return data
        
        except aiohttp.ClientError as e:
            raise DHIS2HTTPError(
                status=response.status if hasattr(response, 'status') else 0,
                url=str(response.url) if hasattr(response, 'url') else 'unknown',
                message=f"Client error: {e}",
            ) from e
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an HTTP request (internal method with retry and rate limiting)"""
        session = self._ensure_session()
        url = self._build_url(endpoint)
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        path = parsed_url.path
        
        # Rate limiting
        await self.rate_limiter.acquire(host, path)
        
        # Prepare request
        final_headers = await self._prepare_headers(headers)
        
        # Statistics
        self.metrics.record_request_start()
        start_time = time.time()
        
        async def _execute_request():
            # This inner function performs a single request attempt
            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data if isinstance(data, dict) else None,
                    data=data if isinstance(data, str) else None,
                    headers=final_headers,
                    **kwargs
                ) as response:
                    # Raise for status to trigger retry for specific error codes
                    if response.status in self.retry_manager.config.retry_on_status:
                        response.raise_for_status()
                    return await self._handle_response(response)
            except aiohttp.ClientError as e:
                # Re-raise client errors so retry manager can catch them
                raise e

        try:
            # Execute request with the retry logic
            result = await self.retry_manager.execute_with_retry(_execute_request)
            
            # Record success
            response_time = time.time() - start_time
            self.metrics.record_request_end(
                success=True,
                response_time=response_time,
                retries=self.retry_manager.get_stats().get('total_retries', 0), # Simplified
            )
            
            return result
        
        except Exception as e:
            # Record failure
            response_time = time.time() - start_time
            self.metrics.record_request_end(
                success=False,
                response_time=response_time,
                retries=self.retry_manager.get_stats().get('total_retries', 0), # Simplified
            )
            
            # Log the final error after all retries
            logger.error(f"Request failed after multiple retries: {e}")
            raise
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """GET request"""
        return await self._make_request('GET', endpoint, params=params, headers=headers, **kwargs)
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """POST request"""
        return await self._make_request('POST', endpoint, params=params, data=data, headers=headers, **kwargs)
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """PUT request"""
        return await self._make_request('PUT', endpoint, params=params, data=data, headers=headers, **kwargs)
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """DELETE request"""
        return await self._make_request('DELETE', endpoint, params=params, headers=headers, **kwargs)
    
    async def get_paginated(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 200,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Get paginated data"""
        results = []
        page = 1
        total_pages = 0
        
        while True:
            # Build pagination parameters
            page_params = (params or {}).copy()
            page_params.update({
                'page': page,
                'pageSize': page_size,
                'paging': 'true'
            })
            
            # Get current page
            response = await self.get(endpoint, params=page_params, **kwargs)
            
            # Extract pagination information
            if 'pager' in response:
                pager = response['pager']
                total_pages = pager.get('pageCount', 1)
                
                # Extract data (usually under a different key)
                data_key = None
                for key in response:
                    if key != 'pager' and isinstance(response[key], list):
                        data_key = key
                        break
                
                if data_key:
                    results.extend(response[data_key])
                
                # Check if there are more pages
                if page >= total_pages:
                    break
                
                if max_pages and page >= max_pages:
                    break
                
            else:
                # No pagination info, assume this is the last page
                if isinstance(response, dict):
                    for key, value in response.items():
                        if isinstance(value, list):
                            results.extend(value)
                            break
                elif isinstance(response, list):
                    results.extend(response)
                break
            
            page += 1
        
        return results
    
    async def get_paginated_atomic(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 50,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get paginated data with all-or-nothing atomicity.
        If any page fails after all retries, it raises AllPagesFetchError.
        """
        all_results = []
        page = 1
        total_pages = 1 # Start with 1 to enter the loop

        while page <= total_pages:
            page_params = (params or {}).copy()
            page_params.update({
                'page': page,
                'pageSize': page_size,
                'paging': 'true'
            })
            
            try:
                response = await self.get(endpoint, params=page_params, **kwargs)
                
                # Logic to extract data and pager info from response
                pager = response.get('pager', {})
                total_pages = pager.get('pageCount', total_pages)
                
                data_key = next((key for key, value in response.items() if key != 'pager' and isinstance(value, list)), None)
                
                if data_key:
                    all_results.extend(response[data_key])
                elif not pager and isinstance(response, list): # Handle responses that are just a list
                    all_results.extend(response)
                
                if (max_pages and page >= max_pages) or page >= total_pages:
                    break

                page += 1

            except Exception as e:
                logger.error(f"Failed to fetch page {page} for endpoint {endpoint} after all retries. Aborting atomic fetch.")
                raise AllPagesFetchError(f"Failed to fetch page {page}/{total_pages} from {endpoint}") from e
        
        return all_results

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            'client': self.metrics.get_stats(),
            'rate_limiter': self.rate_limiter.get_comprehensive_stats(),
            'retry_manager': self.retry_manager.get_stats(),
        }


class SyncDHIS2Client:
    """Synchronous DHIS2 client adapter"""
    
    def __init__(self, config: DHIS2Config):
        self.config = config
        self._async_client: Optional[AsyncDHIS2Client] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def __enter__(self):
        """Sync context manager entry"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        self._async_client = AsyncDHIS2Client(self.config)
        self._loop.run_until_complete(self._async_client.__aenter__())
        
        # Create sync endpoint proxies
        self.analytics = SyncEndpointProxy(self._async_client.analytics, self._loop)
        self.datavaluesets = SyncEndpointProxy(self._async_client.datavaluesets, self._loop)
        self.tracker = SyncEndpointProxy(self._async_client.tracker, self._loop)
        self.metadata = SyncEndpointProxy(self._async_client.metadata, self._loop)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit"""
        if self._async_client and self._loop:
            self._loop.run_until_complete(self._async_client.__aexit__(exc_type, exc_val, exc_tb))
            self._loop.close()
    
    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Synchronous GET request"""
        if not self._async_client or not self._loop:
            raise RuntimeError("Client not initialized")
        return self._loop.run_until_complete(self._async_client.get(endpoint, **kwargs))
    
    def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Synchronous POST request"""
        if not self._async_client or not self._loop:
            raise RuntimeError("Client not initialized")
        return self._loop.run_until_complete(self._async_client.post(endpoint, **kwargs))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        if not self._async_client:
            raise RuntimeError("Client not initialized")
        return self._async_client.get_stats()


class SyncEndpointProxy:
    """Synchronous endpoint proxy"""
    
    def __init__(self, async_endpoint, loop: asyncio.AbstractEventLoop):
        self._async_endpoint = async_endpoint
        self._loop = loop
    
    def __getattr__(self, name):
        """Proxy async methods as synchronous methods"""
        attr = getattr(self._async_endpoint, name)
        if asyncio.iscoroutinefunction(attr):
            def sync_wrapper(*args, **kwargs):
                return self._loop.run_until_complete(attr(*args, **kwargs))
            return sync_wrapper
        return attr
