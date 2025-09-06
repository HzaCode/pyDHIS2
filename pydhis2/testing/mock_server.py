"""Mock DHIS2 server for testing"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from aiohttp import web
import logging

logger = logging.getLogger(__name__)


@dataclass
class MockResponse:
    """Mock response configuration"""
    status: int = 200
    data: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    delay: float = 0.0  # Simulated response delay in seconds
    fail_count: int = 0  # Number of times to fail before succeeding


class MockDHIS2Server:
    """Mock DHIS2 server for testing client behavior"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Response configurations
        self.responses: Dict[str, MockResponse] = {}
        self.request_log: List[Dict[str, Any]] = []
        
        # Setup default routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup default API routes"""
        self.app.router.add_route("*", "/api/{path:.*}", self._handle_api_request)
        self.app.router.add_route("GET", "/api/me", self._handle_me)
        self.app.router.add_route("GET", "/api/system/info", self._handle_system_info)
    
    async def _handle_api_request(self, request: web.Request) -> web.Response:
        """Handle generic API requests"""
        path = request.match_info.get('path', '')
        method = request.method
        full_path = f"/{method.lower()}/api/{path}"
        
        # Log the request
        self.request_log.append({
            'method': method,
            'path': f"/api/{path}",
            'query': dict(request.query),
            'headers': dict(request.headers),
            'timestamp': asyncio.get_event_loop().time()
        })
        
        # Check if we have a configured response
        mock_response = self.responses.get(full_path)
        if not mock_response:
            # Default response
            mock_response = MockResponse(
                status=200,
                data={"message": f"Mock response for {full_path}"}
            )
        
        # Simulate delay
        if mock_response.delay > 0:
            await asyncio.sleep(mock_response.delay)
        
        # Handle failure simulation
        if mock_response.fail_count > 0:
            mock_response.fail_count -= 1
            return web.Response(
                status=500,
                text=json.dumps({"error": "Simulated server error"}),
                headers={'Content-Type': 'application/json'}
            )
        
        # Return configured response
        headers = mock_response.headers or {'Content-Type': 'application/json'}
        response_data = mock_response.data or {}
        
        return web.Response(
            status=mock_response.status,
            text=json.dumps(response_data, ensure_ascii=False),
            headers=headers
        )
    
    async def _handle_me(self, request: web.Request) -> web.Response:
        """Handle /api/me endpoint"""
        return web.json_response({
            "id": "test_user_id",
            "name": "Test User",
            "username": "test_user",
            "email": "test@example.com",
            "authorities": ["F_DATAVALUE_ADD", "F_ANALYTICS_READ"]
        })
    
    async def _handle_system_info(self, request: web.Request) -> web.Response:
        """Handle /api/system/info endpoint"""
        return web.json_response({
            "version": "2.41.0",
            "buildTime": "2024-01-01T00:00:00.000",
            "serverTimeZoneId": "UTC",
            "contextPath": ""
        })
    
    def configure_response(
        self,
        method: str,
        path: str,
        status: int = 200,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        delay: float = 0.0,
        fail_count: int = 0
    ) -> None:
        """Configure a mock response for a specific endpoint"""
        full_path = f"/{method.lower()}{path}"
        self.responses[full_path] = MockResponse(
            status=status,
            data=data,
            headers=headers,
            delay=delay,
            fail_count=fail_count
        )
    
    def configure_endpoint(
        self,
        method: str,
        path: str,
        data: Dict[str, Any],
        status: int = 200,
        delay: float = 0.0,
        fail_count: int = 0
    ) -> None:
        """Configure endpoint response (alias for configure_response)"""
        self.configure_response(method, path, status, data, delay=delay, fail_count=fail_count)
    
    def configure_analytics_response(
        self,
        headers: List[Dict[str, str]],
        rows: List[List[str]],
        delay: float = 0.0
    ) -> None:
        """Configure Analytics endpoint response"""
        self.configure_response(
            "GET",
            "/api/analytics",
            data={
                "headers": headers,
                "rows": rows,
                "metaData": {"items": {}, "dimensions": {}},
                "width": len(headers),
                "height": len(rows)
            },
            delay=delay
        )
    
    def configure_datavaluesets_response(
        self,
        data_values: List[Dict[str, str]],
        delay: float = 0.0
    ) -> None:
        """Configure DataValueSets endpoint response"""
        self.configure_response(
            "GET",
            "/api/dataValueSets",
            data={"dataValues": data_values},
            delay=delay
        )
    
    def configure_import_response(
        self,
        imported: int = 0,
        updated: int = 0,
        ignored: int = 0,
        conflicts: Optional[List[Dict[str, Any]]] = None,
        delay: float = 0.0
    ) -> None:
        """Configure import response"""
        conflicts = conflicts or []
        total = imported + updated + ignored + len(conflicts)
        
        self.configure_response(
            "POST",
            "/api/dataValueSets",
            data={
                "status": "SUCCESS" if not conflicts else "WARNING",
                "imported": imported,
                "updated": updated,
                "ignored": ignored,
                "total": total,
                "conflicts": conflicts
            },
            delay=delay
        )
    
    async def start(self) -> str:
        """Start the mock server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        base_url = f"http://{self.host}:{self.port}"
        logger.info(f"Mock DHIS2 server started at {base_url}")
        return base_url
    
    async def stop(self) -> None:
        """Stop the mock server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Mock DHIS2 server stopped")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return await self.start()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
    
    def get_request_log(self) -> List[Dict[str, Any]]:
        """Get logged requests"""
        return self.request_log.copy()
    
    def clear_request_log(self) -> None:
        """Clear request log"""
        self.request_log.clear()
    
    def get_request_count(self, method: str = None, path: str = None) -> int:
        """Get count of requests matching criteria"""
        filtered_requests = self.request_log
        
        if method:
            filtered_requests = [r for r in filtered_requests if r['method'].upper() == method.upper()]
        
        if path:
            filtered_requests = [r for r in filtered_requests if r['path'] == path]
        
        return len(filtered_requests)
