"""Test configuration and fixtures"""

import pytest
import asyncio
import sys
from typing import AsyncGenerator
from unittest.mock import AsyncMock

from pydhis2.core.types import DHIS2Config
from pydhis2.core.client import AsyncDHIS2Client

# Set event loop policy for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture
def mock_config() -> DHIS2Config:
    """Mock configuration"""
    return DHIS2Config(
        base_url="https://test.dhis2.org",
        auth=("test_user", "test_pass"),
        rps=10.0,
        concurrency=5,
        max_retries=3,
    )


@pytest.fixture
async def mock_client(mock_config: DHIS2Config) -> AsyncGenerator[AsyncDHIS2Client, None]:
    """Mock client"""
    client = AsyncDHIS2Client(mock_config)
    
    # Mock session
    client._session = AsyncMock()
    
    yield client
    
    await client.close()


@pytest.fixture
def sample_analytics_response() -> dict:
    """Sample Analytics response"""
    return {
        "headers": [
            {"name": "dx", "column": "Data", "type": "TEXT"},
            {"name": "pe", "column": "Period", "type": "TEXT"},
            {"name": "ou", "column": "Organisation unit", "type": "TEXT"},
            {"name": "value", "column": "Value", "type": "NUMBER"}
        ],
        "metaData": {
            "items": {},
            "dimensions": {}
        },
        "rows": [
            ["Abc123", "2023Q1", "Def456", "100"],
            ["Abc123", "2023Q2", "Def456", "150"],
            ["Abc123", "2023Q3", "Def456", "200"]
        ],
        "width": 4,
        "height": 3
    }


@pytest.fixture
def sample_datavaluesets_response() -> dict:
    """Sample DataValueSets response"""
    return {
        "dataValues": [
            {
                "dataElement": "Abc123",
                "period": "202301",
                "orgUnit": "Def456",
                "value": "100",
                "lastUpdated": "2023-01-15T10:30:00.000"
            },
            {
                "dataElement": "Abc123", 
                "period": "202302",
                "orgUnit": "Def456",
                "value": "150",
                "lastUpdated": "2023-02-15T10:30:00.000"
            }
        ]
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
