"""Demo test showing how to use pydhis2 testing utilities"""

import asyncio
import logging
from pydhis2.core.types import DHIS2Config
from pydhis2.core.client import AsyncDHIS2Client
from pydhis2.testing import (
    MockDHIS2Server, 
    TestDataGenerator, 
    BenchmarkRunner,
    NetworkSimulator
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_mock_server():
    """Demonstrate mock server usage"""
    print("\n=== Mock Server Demo ===")
    
    # Create test data
    generator = TestDataGenerator()
    org_units = generator.generate_org_units(5)
    data_elements = generator.generate_data_elements(3)
    periods = generator.generate_periods(months=6)
    
    # Start mock server
    mock_server = MockDHIS2Server(port=8081)
    
    # Configure responses
    analytics_response = generator.generate_analytics_response(
        data_elements, org_units, periods
    )
    mock_server.configure_analytics_response(
        analytics_response["headers"],
        analytics_response["rows"]
    )
    
    async with mock_server as base_url:
        # Create client pointing to mock server
        config = DHIS2Config(
            base_url=base_url,
            auth=("test_user", "test_pass"),
            rps=10.0
        )
        
        async with AsyncDHIS2Client(config) as client:
            # Test basic connectivity
            me_data = await client.get("/api/me")
            print(f"✅ Connected as: {me_data.get('name')}")
            
            # Test Analytics
            analytics_data = await client.get("/api/analytics", params={
                "dimension": ["dx:test", "pe:2023Q1", "ou:test"]
            })
            print(f"✅ Analytics: {len(analytics_data.get('rows', []))} rows")
            
            # Check request log
            requests = mock_server.get_request_log()
            print(f"📊 Server received {len(requests)} requests")


async def demo_network_simulation():
    """Demonstrate network condition simulation"""
    print("\n=== Network Simulation Demo ===")
    
    # Test different network conditions
    conditions = [
        NetworkSimulator.NORMAL,
        NetworkSimulator.SLOW_3G,
        NetworkSimulator.WEAK_NETWORK
    ]
    
    for condition in conditions:
        print(f"\n🌐 Testing {condition.name} network...")
        print(f"   Latency: {condition.latency_ms}ms")
        print(f"   Packet loss: {condition.packet_loss_rate:.1%}")
        
        # Simulate some network operations
        simulator = NetworkSimulator(condition)
        
        start_time = asyncio.get_event_loop().time()
        for _ in range(3):
            await simulator.simulate_latency()
            if simulator.should_drop_packet():
                print("   📉 Packet dropped!")
        
        elapsed = asyncio.get_event_loop().time() - start_time
        print(f"   ⏱️  Total time: {elapsed:.3f}s")


async def demo_benchmark_runner():
    """Demonstrate benchmark runner usage"""
    print("\n=== Benchmark Runner Demo ===")
    
    runner = BenchmarkRunner("pydhis2_demo")
    
    async def sample_operation():
        """Sample async operation to benchmark"""
        await asyncio.sleep(random.uniform(0.01, 0.05))  # Simulate work
        if random.random() < 0.1:  # 10% failure rate
            raise Exception("Simulated error")
    
    # Run repeated test
    await runner.run_repeated_test(
        sample_operation,
        "sample_async_operation",
        repetitions=20
    )
    
    # Run concurrent test  
    await runner.run_concurrent_test(
        sample_operation,
        "concurrent_sample_operation",
        concurrency=5,
        total_requests=50
    )
    
    # Print results
    runner.print_summary()


async def main():
    """Run all demos"""
    print("🚀 pydhis2 Testing Utilities Demo")
    print("=" * 50)
    
    try:
        await demo_mock_server()
        await demo_network_simulation()
        await demo_benchmark_runner()
        
        print("\n🎉 All demos completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import random
    asyncio.run(main())
