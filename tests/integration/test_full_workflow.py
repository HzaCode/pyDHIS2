"""Integration tests for full DHIS2 workflows"""

import pytest
import pandas as pd
from pydhis2.core.types import DHIS2Config, AnalyticsQuery
from pydhis2.core.client import AsyncDHIS2Client
from pydhis2.testing import (
    MockDHIS2Server,
    TestDataGenerator,
    BenchmarkRunner
)
from pydhis2.dqr.metrics import CompletenessMetrics, ConsistencyMetrics


@pytest.mark.integration
class TestAnalyticsWorkflow:
    """Test complete Analytics workflow"""
    
    @pytest.mark.asyncio
    async def test_analytics_pull_and_analysis(self):
        """Test pulling Analytics data and running DQR analysis"""
        # Setup test data
        generator = TestDataGenerator()
        org_units = generator.generate_org_units(5)
        data_elements = generator.generate_data_elements(3)
        periods = generator.generate_periods(months=6)
        
        # Start mock server
        mock_server = MockDHIS2Server(port=9001)
        analytics_response = generator.generate_analytics_response(
            data_elements, org_units, periods, null_rate=0.1
        )
        mock_server.configure_analytics_response(
            analytics_response["headers"],
            analytics_response["rows"]
        )
        
        async with mock_server as base_url:
            config = DHIS2Config(
                base_url=base_url,
                auth=("test", "test"),
                rps=10.0
            )
            
            async with AsyncDHIS2Client(config) as client:
                # 1. Pull Analytics data
                query = AnalyticsQuery(
                    dx=[de["id"] for de in data_elements],
                    ou=[ou["id"] for ou in org_units],
                    pe=periods
                )
                
                df = await client.analytics.to_pandas(query)
                
                assert isinstance(df, pd.DataFrame)
                assert not df.empty
                
                # 2. Run DQR analysis
                completeness_metrics = CompletenessMetrics()
                consistency_metrics = ConsistencyMetrics()
                
                completeness_results = completeness_metrics.calculate(df)
                consistency_results = consistency_metrics.calculate(df)
                
                assert len(completeness_results) >= 1
                assert len(consistency_results) >= 1
                
                # 3. Check that we can identify data quality issues
                all_results = completeness_results + consistency_results
                quality_score = sum(1 for r in all_results if r.status == "pass") / len(all_results)
                
                # Should get some meaningful quality assessment
                assert 0.0 <= quality_score <= 1.0


@pytest.mark.integration
class TestDataValueSetsWorkflow:
    """Test complete DataValueSets workflow"""
    
    @pytest.mark.asyncio
    async def test_datavaluesets_import_workflow(self):
        """Test importing DataValueSets and handling conflicts"""
        # Setup mock server
        mock_server = MockDHIS2Server(port=9002)
        
        # Configure successful import response
        mock_server.configure_import_response(
            imported=15,
            updated=3,
            ignored=0,
            conflicts=[
                {
                    "object": "CONFLICT1",
                    "property": "value",
                    "value": "invalid",
                    "message": "Invalid data value"
                }
            ]
        )
        
        async with mock_server as base_url:
            config = DHIS2Config(
                base_url=base_url,
                auth=("test", "test")
            )
            
            async with AsyncDHIS2Client(config) as client:
                # Create test data
                test_data = pd.DataFrame({
                    'dataElement': ['DE1', 'DE2'] * 10,
                    'period': ['202301'] * 20,
                    'orgUnit': ['OU1', 'OU2'] * 10,
                    'value': [100 + i for i in range(20)]
                })
                
                # Try to import (should raise conflict error)
                from pydhis2.core.errors import ImportConflictError
                
                with pytest.raises(ImportConflictError) as exc_info:
                    await client.datavaluesets.push(test_data)
                
                # Check conflict details
                assert len(exc_info.value.conflicts) == 1
                assert exc_info.value.conflicts[0]["message"] == "Invalid data value"


@pytest.mark.integration
class TestPerformanceBenchmarking:
    """Test performance benchmarking capabilities"""
    
    @pytest.mark.asyncio
    async def test_benchmark_analytics_performance(self):
        """Test benchmarking Analytics performance"""
        # Setup mock server with realistic delays
        generator = TestDataGenerator()
        org_units = generator.generate_org_units(3)
        data_elements = generator.generate_data_elements(2)
        
        mock_server = MockDHIS2Server(port=9004)
        analytics_response = generator.generate_analytics_response(
            data_elements, org_units, ["202301", "202302"]
        )
        mock_server.configure_analytics_response(
            analytics_response["headers"],
            analytics_response["rows"],
            delay=0.05  # 50ms delay per request
        )
        
        async with mock_server as base_url:
            config = DHIS2Config(
                base_url=base_url,
                auth=("test", "test"),
                rps=20.0
            )
            
            # Setup benchmark runner
            benchmark = BenchmarkRunner("analytics_performance")
            
            async def analytics_operation():
                async with AsyncDHIS2Client(config) as client:
                    query = AnalyticsQuery(
                        dx=data_elements[0]["id"],
                        ou=org_units[0]["id"],
                        pe="202301"
                    )
                    df = await client.analytics.to_pandas(query)
                    return len(df)
            
            # Run repeated tests
            result = await benchmark.run_repeated_test(
                analytics_operation,
                "analytics_query",
                repetitions=5
            )
            
            # Verify benchmark results
            assert result.success_count == 5
            assert result.failure_count == 0
            assert result.success_rate == 1.0
            assert result.avg_response_time > 0
            assert len(result.response_times) == 5
            
            # Performance should be consistent
            import statistics
            if len(result.response_times) > 1:
                cv = statistics.stdev(result.response_times) / result.avg_response_time
                assert cv < 1.0  # Coefficient of variation should be reasonable
    
    @pytest.mark.asyncio
    async def test_benchmark_concurrent_load(self):
        """Test benchmarking under concurrent load"""
        # Setup mock server
        generator = TestDataGenerator()
        org_units = generator.generate_org_units(1)
        data_elements = generator.generate_data_elements(1)
        
        mock_server = MockDHIS2Server(port=9005)
        analytics_response = generator.generate_analytics_response(
            data_elements, org_units, ["202301"]
        )
        mock_server.configure_analytics_response(
            analytics_response["headers"],
            analytics_response["rows"]
        )
        
        async with mock_server as base_url:
            config = DHIS2Config(
                base_url=base_url,
                auth=("test", "test"),
                rps=50.0,  # High rate limit for concurrent testing
                concurrency=10
            )
            
            benchmark = BenchmarkRunner("concurrent_analytics")
            
            async def single_analytics_request():
                async with AsyncDHIS2Client(config) as client:
                    query = AnalyticsQuery(
                        dx=data_elements[0]["id"],
                        ou=org_units[0]["id"],
                        pe="202301"
                    )
                    df = await client.analytics.to_pandas(query)
                    return len(df)
            
            # Run concurrent test
            result = await benchmark.run_concurrent_test(
                single_analytics_request,
                "concurrent_analytics_requests",
                concurrency=5,
                total_requests=20
            )
            
            # Should handle concurrent load well
            assert result.success_count == 20
            assert result.failure_count == 0
            assert result.success_rate == 1.0
            
            # Performance should be reasonable
            assert result.avg_response_time < 2.0  # Should complete within 2 seconds on average