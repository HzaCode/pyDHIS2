"""Unit tests for DQR metrics functionality"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pydhis2.dqr.metrics import (
    MetricResult,
    CompletenessMetrics,
    ConsistencyMetrics,
    TimelinessMetrics,
    load_dqr_config
)


class TestMetricResult:
    """Tests for the MetricResult data class"""
    
    def test_init(self):
        """Test metric result initialization"""
        result = MetricResult(
            metric_name="test_metric",
            value=0.85,
            status="pass",
            threshold=0.80,
            message="Test message"
        )
        
        assert result.metric_name == "test_metric"
        assert result.value == 0.85
        assert result.status == "pass"
        assert result.threshold == 0.80
        assert result.message == "Test message"
        assert result.details == {}  # Should be initialized as empty dict
    
    def test_init_with_details(self):
        """Test metric result with details"""
        details = {"count": 100, "errors": 5}
        result = MetricResult(
            metric_name="test",
            value=0.95,
            status="pass",
            details=details
        )
        
        assert result.details == details


class TestCompletenessMetrics:
    """Tests for the CompletenessMetrics class"""
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing"""
        data = {
            'dataElement': ['DE1', 'DE1', 'DE2', 'DE2', 'DE1', 'DE2'],
            'orgUnit': ['OU1', 'OU2', 'OU1', 'OU2', 'OU3', 'OU3'],
            'period': ['202301', '202301', '202301', '202301', '202302', '202302'],
            'value': [100, 150, 200, None, 120, 180]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture
    def completeness_metrics(self):
        """Completeness metrics instance"""
        return CompletenessMetrics()
    
    def test_init(self, completeness_metrics):
        """Test completeness metrics initialization"""
        assert completeness_metrics.thresholds['reporting_completeness_pass'] == 0.90
        assert completeness_metrics.thresholds['data_element_completeness_pass'] == 0.90
    
    def test_calculate_empty_data(self, completeness_metrics):
        """Test calculation with empty data"""
        empty_df = pd.DataFrame()
        results = completeness_metrics.calculate(empty_df)
        
        assert len(results) == 1
        assert results[0].metric_name == "completeness_overall"
        assert results[0].value == 0.0
        assert results[0].status == "fail"
    
    def test_calculate_reporting_completeness(self, completeness_metrics, sample_data):
        """Test reporting completeness calculation"""
        results = completeness_metrics.calculate(sample_data)
        
        # Should have reporting completeness result
        reporting_result = next(
            (r for r in results if r.metric_name == "reporting_completeness"), 
            None
        )
        assert reporting_result is not None
        
        # Expected combinations: 2 data elements × 3 org units × 2 periods = 12
        # Actual combinations in sample data: 6
        expected_completeness = 6 / 12  # 0.5
        assert abs(reporting_result.value - expected_completeness) < 0.01
        assert reporting_result.status == "fail"  # Below 0.90 threshold
    
    def test_calculate_element_completeness(self, completeness_metrics, sample_data):
        """Test data element completeness calculation"""
        results = completeness_metrics.calculate(sample_data)
        
        # Should have element completeness result
        element_result = next(
            (r for r in results if r.metric_name == "data_element_completeness"),
            None
        )
        assert element_result is not None
        
        # 5 non-null values out of 6 total = 83.3%
        expected_completeness = 5 / 6
        assert abs(element_result.value - expected_completeness) < 0.01
        assert element_result.status == "warning"  # Between 0.80 and 0.90 threshold
    
    def test_calculate_perfect_completeness(self, completeness_metrics):
        """Test calculation with perfect completeness"""
        # Create perfect data (no missing values, all combinations)
        perfect_data = pd.DataFrame({
            'dataElement': ['DE1', 'DE1', 'DE2', 'DE2'],
            'orgUnit': ['OU1', 'OU2', 'OU1', 'OU2'],
            'period': ['202301', '202301', '202301', '202301'],
            'value': [100, 150, 200, 250]
        })
        
        results = completeness_metrics.calculate(perfect_data)
        
        # Both metrics should pass
        for result in results:
            assert result.value == 1.0
            assert result.status == "pass"


class TestConsistencyMetrics:
    """Tests for the ConsistencyMetrics class"""
    
    @pytest.fixture
    def consistency_metrics(self):
        """Consistency metrics instance"""
        return ConsistencyMetrics()
    
    @pytest.fixture
    def sample_data_with_outliers(self):
        """Sample data with outliers for testing"""
        np.random.seed(42)  # For reproducible tests
        
        # Generate normal data
        normal_values = np.random.normal(100, 10, 50)
        
        # Add some outliers
        outliers = [200, 300, -50]  # Clear outliers
        
        all_values = list(normal_values) + outliers
        
        data = {
            'value': all_values,
            'orgUnit': [f'OU{i%5}' for i in range(len(all_values))],
            'period': [f'2023{(i%12)+1:02d}' for i in range(len(all_values))]
        }
        
        return pd.DataFrame(data)
    
    def test_init(self, consistency_metrics):
        """Test consistency metrics initialization"""
        assert consistency_metrics.thresholds['outlier_extreme'] == 3.0
        assert consistency_metrics.thresholds['trend_consistency_pass'] == 0.90
    
    def test_calculate_empty_data(self, consistency_metrics):
        """Test calculation with empty data"""
        empty_df = pd.DataFrame()
        results = consistency_metrics.calculate(empty_df)
        
        assert len(results) == 1
        assert results[0].status == "fail"
        assert "Insufficient data" in results[0].message
    
    def test_detect_outliers(self, consistency_metrics, sample_data_with_outliers):
        """Test outlier detection"""
        results = consistency_metrics.calculate(sample_data_with_outliers)
        
        outlier_result = next(
            (r for r in results if r.metric_name == "outlier_detection"),
            None
        )
        assert outlier_result is not None
        assert outlier_result.value < 1.0  # Should detect some outliers
        assert 'outlier_count' in outlier_result.details
        assert outlier_result.details['outlier_count'] > 0
    
    def test_assess_trend_consistency(self, consistency_metrics):
        """Test trend consistency assessment"""
        # Create data with consistent trends
        consistent_data = pd.DataFrame({
            'value': [100, 105, 110, 115, 120] * 2,  # Consistent upward trend
            'orgUnit': ['OU1'] * 5 + ['OU2'] * 5,
            'period': ['202301', '202302', '202303', '202304', '202305'] * 2
        })
        
        results = consistency_metrics.calculate(consistent_data)
        
        trend_result = next(
            (r for r in results if r.metric_name == "trend_consistency"),
            None
        )
        assert trend_result is not None
        assert trend_result.value > 0.5  # Should have decent consistency
        assert 'org_units_analyzed' in trend_result.details
    
    def test_insufficient_data_for_outliers(self, consistency_metrics):
        """Test outlier detection with insufficient data"""
        small_data = pd.DataFrame({
            'value': [100, 105],  # Only 2 values
            'orgUnit': ['OU1', 'OU1'],
            'period': ['202301', '202302']
        })
        
        results = consistency_metrics.calculate(small_data)
        
        outlier_result = next(
            (r for r in results if r.metric_name == "outlier_detection"),
            None
        )
        assert outlier_result is not None
        assert outlier_result.status == "warning"
        assert "Insufficient data" in outlier_result.message


class TestTimelinessMetrics:
    """Tests for the TimelinessMetrics class"""
    
    @pytest.fixture
    def timeliness_metrics(self):
        """Timeliness metrics instance"""
        return TimelinessMetrics()
    
    @pytest.fixture
    def sample_data_with_timestamps(self):
        """Sample data with timestamps"""
        now = datetime.now()
        
        data = {
            'value': [100, 150, 200, 250, 300],
            'orgUnit': ['OU1', 'OU2', 'OU3', 'OU4', 'OU5'],
            'period': ['202301', '202301', '202302', '202302', '202303'],
            'lastUpdated': [
                (now - timedelta(days=5)).isoformat(),   # Recent
                (now - timedelta(days=10)).isoformat(),  # Recent
                (now - timedelta(days=45)).isoformat(),  # Old
                (now - timedelta(days=2)).isoformat(),   # Recent
                (now - timedelta(days=60)).isoformat(),  # Very old
            ]
        }
        
        return pd.DataFrame(data)
    
    def test_init(self, timeliness_metrics):
        """Test timeliness metrics initialization"""
        assert timeliness_metrics.thresholds['submission_timeliness_pass'] == 0.90
        assert timeliness_metrics.thresholds['max_delay_days'] == 30
    
    def test_calculate_empty_data(self, timeliness_metrics):
        """Test calculation with empty data"""
        empty_df = pd.DataFrame()
        results = timeliness_metrics.calculate(empty_df)
        
        assert len(results) == 1
        assert results[0].status == "fail"
        assert "No data available" in results[0].message
    
    def test_calculate_no_time_columns(self, timeliness_metrics):
        """Test calculation with no time columns"""
        data_without_time = pd.DataFrame({
            'value': [100, 150, 200],
            'orgUnit': ['OU1', 'OU2', 'OU3']
        })
        
        results = timeliness_metrics.calculate(data_without_time)
        
        assert len(results) == 1
        assert results[0].status == "warning"
        assert "No time columns available" in results[0].message
    
    def test_calculate_submission_timeliness(self, timeliness_metrics, sample_data_with_timestamps):
        """Test submission timeliness calculation"""
        results = timeliness_metrics.calculate(sample_data_with_timestamps)
        
        timeliness_result = results[0]
        assert timeliness_result.metric_name == "submission_timeliness"
        
        # 3 out of 5 records are within 30 days = 60%
        expected_rate = 3 / 5
        assert abs(timeliness_result.value - expected_rate) < 0.01
        assert timeliness_result.status == "fail"  # Below 0.90 threshold
        
        assert 'total_records' in timeliness_result.details
        assert 'timely_records' in timeliness_result.details
        assert timeliness_result.details['total_records'] == 5
        assert timeliness_result.details['timely_records'] == 3


class TestDQRConfiguration:
    """Tests for DQR configuration loading"""
    
    def test_load_dqr_config_default(self):
        """Test loading default DQR configuration"""
        # This will try to load from pydhis2/dqr/config.yml
        config = load_dqr_config()
        
        # Should return a dict (empty if file doesn't exist)
        assert isinstance(config, dict)
    
    def test_load_dqr_config_nonexistent(self):
        """Test loading non-existent config file"""
        config = load_dqr_config("/nonexistent/path.yml")
        
        # Should return empty dict without raising exception
        assert config == {}


class TestDQRIntegration:
    """Tests for DQR metrics integration"""
    
    @pytest.fixture
    def realistic_health_data(self):
        """Generate realistic health data for testing"""
        np.random.seed(42)
        
        # Generate 100 records across 5 facilities, 3 indicators, 6 months
        facilities = [f'FAC{i:03d}' for i in range(1, 6)]
        indicators = ['BCG_DOSES', 'DPT1_DOSES', 'DPT3_DOSES']
        periods = ['202301', '202302', '202303', '202304', '202305', '202306']
        
        data = []
        
        for facility in facilities:
            for indicator in indicators:
                for period in periods:
                    # Generate realistic values with some variation
                    base_value = {
                        'BCG_DOSES': 80,
                        'DPT1_DOSES': 75,
                        'DPT3_DOSES': 70
                    }[indicator]
                    
                    # Add some randomness
                    value = max(0, int(np.random.normal(base_value, 10)))
                    
                    # Sometimes add missing values (5% chance)
                    if np.random.random() < 0.05:
                        value = None
                    
                    # Add timestamps (most recent, some older)
                    if np.random.random() < 0.8:
                        last_updated = datetime.now() - timedelta(days=np.random.randint(1, 20))
                    else:
                        last_updated = datetime.now() - timedelta(days=np.random.randint(40, 80))
                    
                    data.append({
                        'dataElement': indicator,
                        'orgUnit': facility,
                        'period': period,
                        'value': value,
                        'lastUpdated': last_updated.isoformat()
                    })
        
        return pd.DataFrame(data)
    
    def test_full_dqr_analysis(self, realistic_health_data):
        """Test complete DQR analysis on realistic data"""
        # Run all three types of metrics
        completeness_metrics = CompletenessMetrics()
        consistency_metrics = ConsistencyMetrics()
        timeliness_metrics = TimelinessMetrics()
        
        completeness_results = completeness_metrics.calculate(realistic_health_data)
        consistency_results = consistency_metrics.calculate(realistic_health_data)
        timeliness_results = timeliness_metrics.calculate(realistic_health_data)
        
        all_results = completeness_results + consistency_results + timeliness_results
        
        # Should have multiple results
        assert len(all_results) >= 3
        
        # All results should have required fields
        for result in all_results:
            assert result.metric_name
            assert isinstance(result.value, (int, float))
            assert result.status in ['pass', 'warning', 'fail']
            assert result.message
            assert isinstance(result.details, dict)
    
    def test_dqr_with_custom_thresholds(self, realistic_health_data):
        """Test DQR with custom threshold configuration"""
        custom_config = {
            'completeness': {
                'reporting': {
                    'thresholds': {
                        'pass': 0.95,
                        'warn': 0.85
                    }
                }
            },
            'consistency': {
                'outliers': {
                    'zscore': {
                        'extreme': 2.5  # More sensitive outlier detection
                    }
                }
            }
        }
        
        completeness_metrics = CompletenessMetrics(custom_config)
        results = completeness_metrics.calculate(realistic_health_data)
        
        # Should use custom thresholds
        reporting_result = next(
            (r for r in results if r.metric_name == "reporting_completeness"),
            None
        )
        
        if reporting_result:
            assert reporting_result.details['pass_threshold'] == 0.95
            assert reporting_result.details['warn_threshold'] == 0.85
    
    def test_metric_status_assessment(self):
        """Test status assessment logic"""
        completeness_metrics = CompletenessMetrics()
        
        # Test pass status
        status = completeness_metrics._assess_status(0.95, 0.90, 0.80)
        assert status == "pass"
        
        # Test warning status
        status = completeness_metrics._assess_status(0.85, 0.90, 0.80)
        assert status == "warning"
        
        # Test fail status
        status = completeness_metrics._assess_status(0.75, 0.90, 0.80)
        assert status == "fail"
    
    def test_dqr_performance_with_large_dataset(self):
        """Test DQR performance with larger dataset"""
        # Generate a larger dataset
        np.random.seed(42)
        large_data = pd.DataFrame({
            'dataElement': np.random.choice(['DE1', 'DE2', 'DE3'], 10000),
            'orgUnit': np.random.choice([f'OU{i}' for i in range(100)], 10000),
            'period': np.random.choice(['202301', '202302', '202303'], 10000),
            'value': np.random.randint(1, 1000, 10000),
            'lastUpdated': [
                (datetime.now() - timedelta(days=np.random.randint(1, 60))).isoformat()
                for _ in range(10000)
            ]
        })
        
        # All metrics should complete without errors
        completeness_metrics = CompletenessMetrics()
        consistency_metrics = ConsistencyMetrics()
        timeliness_metrics = TimelinessMetrics()
        
        import time
        start_time = time.time()
        
        completeness_results = completeness_metrics.calculate(large_data)
        consistency_results = consistency_metrics.calculate(large_data)
        timeliness_results = timeliness_metrics.calculate(large_data)
        
        elapsed = time.time() - start_time
        
        # Should complete reasonably quickly (under 5 seconds)
        assert elapsed < 5.0
        
        # Should produce results
        assert len(completeness_results) >= 1
        assert len(consistency_results) >= 1
        assert len(timeliness_results) >= 1
