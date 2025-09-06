"""Network condition simulator for testing weak network scenarios"""

import asyncio
import random
import time
from typing import Optional, Callable, Any, List, Dict
from dataclasses import dataclass
import aiohttp
import pandas as pd

from pydhis2.testing.data_generator import TestDataGenerator


@dataclass
class NetworkCondition:
    """Network condition configuration"""
    name: str
    latency_ms: int = 50  # Average latency in milliseconds
    jitter_ms: int = 10   # Latency jitter
    packet_loss_rate: float = 0.0  # Packet loss rate (0.0 - 1.0)
    bandwidth_kbps: Optional[int] = None  # Bandwidth limit in kbps
    timeout_rate: float = 0.0  # Rate of request timeouts (0.0 - 1.0)


class NetworkSimulator:
    """Simulate various network conditions for testing"""
    
    # Predefined network conditions
    NORMAL = NetworkCondition(
        name="normal",
        latency_ms=20,
        jitter_ms=5,
        packet_loss_rate=0.0,
        timeout_rate=0.0
    )
    
    SLOW_3G = NetworkCondition(
        name="slow_3g",
        latency_ms=200,
        jitter_ms=50,
        packet_loss_rate=0.01,
        bandwidth_kbps=400,
        timeout_rate=0.02
    )
    
    WEAK_NETWORK = NetworkCondition(
        name="weak_network", 
        latency_ms=400,
        jitter_ms=100,
        packet_loss_rate=0.03,
        bandwidth_kbps=200,
        timeout_rate=0.05
    )
    
    VERY_WEAK = NetworkCondition(
        name="very_weak",
        latency_ms=800,
        jitter_ms=200,
        packet_loss_rate=0.08,
        bandwidth_kbps=100,
        timeout_rate=0.10
    )
    
    def __init__(self, condition: NetworkCondition = None):
        self.condition = condition or self.NORMAL
        self.original_connector_init = None
        self.original_request = None
    
    async def simulate_latency(self) -> None:
        """Simulate network latency"""
        if self.condition.latency_ms > 0:
            # Add base latency plus jitter
            base_latency = self.condition.latency_ms / 1000.0
            jitter = random.uniform(
                -self.condition.jitter_ms / 1000.0,
                self.condition.jitter_ms / 1000.0
            )
            total_latency = max(0, base_latency + jitter)
            
            if total_latency > 0:
                await asyncio.sleep(total_latency)
    
    def should_drop_packet(self) -> bool:
        """Determine if packet should be dropped (simulating packet loss)"""
        return random.random() < self.condition.packet_loss_rate
    
    def should_timeout(self) -> bool:
        """Determine if request should timeout"""
        return random.random() < self.condition.timeout_rate
    
    async def simulate_bandwidth_limit(self, data_size: int) -> None:
        """Simulate bandwidth limitations"""
        if self.condition.bandwidth_kbps and data_size > 0:
            # Calculate transfer time based on bandwidth
            transfer_time = (data_size * 8) / (self.condition.bandwidth_kbps * 1000)
            if transfer_time > 0:
                await asyncio.sleep(transfer_time)
    
    def wrap_session(self, session: aiohttp.ClientSession) -> 'SimulatedSession':
        """Wrap an aiohttp session with network simulation"""
        return SimulatedSession(session, self)


class SimulatedSession:
    """Wrapper for aiohttp.ClientSession that simulates network conditions"""
    
    def __init__(self, session: aiohttp.ClientSession, simulator: NetworkSimulator):
        self.session = session
        self.simulator = simulator
    
    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a request with network simulation"""
        # Simulate latency before request
        await self.simulator.simulate_latency()
        
        # Check for packet loss
        if self.simulator.should_drop_packet():
            raise aiohttp.ClientConnectionError("Simulated packet loss")
        
        # Check for timeout
        if self.simulator.should_timeout():
            raise asyncio.TimeoutError("Simulated network timeout")
        
        # Make the actual request
        start_time = time.time()
        response = await self.session.request(method, url, **kwargs)
        
        # Simulate bandwidth limitations based on response size
        if hasattr(response, 'content_length') and response.content_length:
            await self.simulator.simulate_bandwidth_limit(response.content_length)
        
        return response
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """GET request with simulation"""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """POST request with simulation"""
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """PUT request with simulation"""
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """DELETE request with simulation"""
        return await self.request('DELETE', url, **kwargs)
    
    async def close(self) -> None:
        """Close the underlying session"""
        await self.session.close()


class BenchmarkDataGenerator:
    """Generate data specifically for benchmark testing"""
    
    def __init__(self, seed: int = 42):
        self.generator = TestDataGenerator(seed)
    
    def generate_large_dataset(
        self,
        org_unit_count: int = 100,
        data_element_count: int = 20,
        period_count: int = 12,
        records_per_combination: int = 1
    ) -> pd.DataFrame:
        """Generate a large dataset for performance testing"""
        org_units = self.generator.generate_org_units(org_unit_count)
        data_elements = self.generator.generate_data_elements(data_element_count)
        periods = self.generator.generate_periods(months=period_count)
        
        data_values = []
        
        for de in data_elements:
            for period in periods:
                for ou in org_units:
                    for _ in range(records_per_combination):
                        value = random.randint(1, 1000)
                        
                        data_values.append({
                            'dataElement': de['id'],
                            'period': period,
                            'orgUnit': ou['id'],
                            'value': value,
                            'lastUpdated': datetime.now().isoformat(),
                            'created': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
                        })
        
        return pd.DataFrame(data_values)
    
    def generate_conflicted_dataset(
        self,
        base_data: pd.DataFrame,
        conflict_rate: float = 0.05
    ) -> pd.DataFrame:
        """Generate a dataset with intentional conflicts for testing"""
        conflicted_data = base_data.copy()
        
        # Randomly select records to make conflicting
        conflict_count = int(len(conflicted_data) * conflict_rate)
        conflict_indices = random.sample(range(len(conflicted_data)), conflict_count)
        
        for idx in conflict_indices:
            # Create conflicts by duplicating records with different values
            conflicted_row = conflicted_data.iloc[idx].copy()
            conflicted_row['value'] = 'INVALID_VALUE'  # This will cause conflicts
            conflicted_data = pd.concat([conflicted_data, conflicted_row.to_frame().T], ignore_index=True)
        
        return conflicted_data
    
    def generate_performance_test_scenarios(self) -> List[Dict[str, Any]]:
        """Generate different scenarios for performance testing"""
        scenarios = [
            {
                "name": "small_dataset",
                "description": "Small dataset for basic functionality",
                "org_units": 5,
                "data_elements": 3,
                "periods": 6,
                "expected_records": 5 * 3 * 6
            },
            {
                "name": "medium_dataset", 
                "description": "Medium dataset for typical workload",
                "org_units": 50,
                "data_elements": 10,
                "periods": 12,
                "expected_records": 50 * 10 * 12
            },
            {
                "name": "large_dataset",
                "description": "Large dataset for stress testing", 
                "org_units": 200,
                "data_elements": 25,
                "periods": 24,
                "expected_records": 200 * 25 * 24
            }
        ]
        
        return scenarios
