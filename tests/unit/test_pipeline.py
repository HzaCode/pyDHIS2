"""Tests for pipeline module"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from pydhis2.pipeline.config import StepConfig, PipelineConfig
from pydhis2.pipeline.steps import (
    PipelineStep, AnalyticsStep, DataValueSetsStep,
    DQRStep, TrackerStep, StepRegistry
)
from pydhis2.pipeline.executor import PipelineExecutor


class TestStepConfig:
    """Test StepConfig model"""
    
    def test_step_config_minimal(self):
        """Test minimal step configuration"""
        config = StepConfig(
            type="analytics",
            name="test_step"
        )
        assert config.type == "analytics"
        assert config.name == "test_step"
        assert config.enabled is True
        assert config.retry_count == 0
    
    def test_step_config_full(self):
        """Test full step configuration"""
        config = StepConfig(
            type="analytics",
            name="test_step",
            depends_on=["step1"],
            enabled=True,
            timeout=300,
            retry_count=3,
            params={"dx": "test"},
            input="input.parquet",
            output="output.parquet"
        )
        assert config.depends_on == ["step1"]
        assert config.timeout == 300
        assert config.retry_count == 3
        assert config.params == {"dx": "test"}
        assert config.input == "input.parquet"
        assert config.output == "output.parquet"


class TestPipelineConfig:
    """Test PipelineConfig model"""
    
    def test_pipeline_config_minimal(self):
        """Test minimal pipeline configuration"""
        config = PipelineConfig(
            name="test_pipeline",
            steps=[
                StepConfig(type="analytics", name="step1")
            ]
        )
        assert config.name == "test_pipeline"
        assert config.version == "1.0.0"
        assert config.rps == 8.0
        assert config.concurrency == 8
        assert len(config.steps) == 1
    
    def test_pipeline_config_full(self):
        """Test full pipeline configuration"""
        config = PipelineConfig(
            name="test_pipeline",
            description="Test pipeline",
            version="2.0.0",
            rps=10.0,
            concurrency=16,
            timeout=600,
            steps=[
                StepConfig(type="analytics", name="step1"),
                StepConfig(type="transform", name="step2", depends_on=["step1"])
            ],
            metadata={"author": "test"}
        )
        assert config.description == "Test pipeline"
        assert config.version == "2.0.0"
        assert config.rps == 10.0
        assert config.metadata == {"author": "test"}
    
    def test_validate_dependencies_valid(self):
        """Test dependency validation - valid case"""
        config = PipelineConfig(
            name="test",
            steps=[
                StepConfig(type="analytics", name="step1"),
                StepConfig(type="transform", name="step2", depends_on=["step1"])
            ]
        )
        errors = config.validate_dependencies()
        assert len(errors) == 0
    
    def test_validate_dependencies_invalid(self):
        """Test dependency validation - invalid case"""
        config = PipelineConfig(
            name="test",
            steps=[
                StepConfig(type="analytics", name="step1"),
                StepConfig(type="transform", name="step2", depends_on=["nonexistent"])
            ]
        )
        errors = config.validate_dependencies()
        assert len(errors) > 0
    
    def test_get_execution_order(self):
        """Test execution order calculation"""
        config = PipelineConfig(
            name="test",
            steps=[
                StepConfig(type="analytics", name="step1"),
                StepConfig(type="transform", name="step2", depends_on=["step1"]),
                StepConfig(type="export", name="step3", depends_on=["step2"])
            ]
        )
        order = config.get_execution_order()
        assert order == ["step1", "step2", "step3"]
    
    def test_get_step_by_name(self):
        """Test getting step by name"""
        config = PipelineConfig(
            name="test",
            steps=[
                StepConfig(type="analytics", name="step1"),
                StepConfig(type="transform", name="step2")
            ]
        )
        step = config.get_step_by_name("step1")
        assert step.name == "step1"
        
        step = config.get_step_by_name("nonexistent")
        assert step is None


class TestAnalyticsStep:
    """Test AnalyticsStep"""
    
    def test_validate_params_success(self):
        """Test parameter validation - success"""
        config = StepConfig(
            type="analytics",
            name="test",
            params={"dx": "d1", "ou": "o1", "pe": "2023"}
        )
        step = AnalyticsStep(config)
        step.validate_params()  # Should not raise
    
    def test_validate_params_missing(self):
        """Test parameter validation - missing params"""
        config = StepConfig(
            type="analytics",
            name="test",
            params={"dx": "d1"}  # Missing ou and pe
        )
        step = AnalyticsStep(config)
        with pytest.raises(ValueError, match="missing required parameter"):
            step.validate_params()
    
    @pytest.mark.asyncio
    async def test_execute(self):
        """Test execute method"""
        config = StepConfig(
            type="analytics",
            name="test",
            params={"dx": "d1", "ou": "o1", "pe": "2023"},
            output="test.parquet"
        )
        step = AnalyticsStep(config)
        
        # Mock client
        mock_client = MagicMock()
        mock_client.analytics.to_pandas = AsyncMock(
            return_value=pd.DataFrame({"data": [1, 2, 3]})
        )
        
        result = await step.execute(client=mock_client, context={})
        
        assert result["status"] == "success"
        assert "dataframe" in result
        assert len(result["dataframe"]) == 3


class TestDataValueSetsStep:
    """Test DataValueSetsStep"""
    
    def test_validate_params_pull(self):
        """Test parameter validation for pull"""
        config = StepConfig(
            type="datavaluesets",
            name="test",
            params={"action": "pull", "dataSet": "ds1"}
        )
        step = DataValueSetsStep(config)
        step.validate_params()  # Should not raise
    
    def test_validate_params_missing_action(self):
        """Test parameter validation - missing action"""
        config = StepConfig(
            type="datavaluesets",
            name="test",
            params={}
        )
        step = DataValueSetsStep(config)
        with pytest.raises(ValueError, match="missing required parameter: action"):
            step.validate_params()


class TestDQRStep:
    """Test DQRStep"""
    
    def test_validate_params(self):
        """Test parameter validation"""
        config = StepConfig(
            type="dqr",
            name="test",
            input="data.parquet",
            params={"metrics": ["completeness"]}
        )
        step = DQRStep(config)
        step.validate_params()  # Should not raise
    
    @pytest.mark.asyncio
    async def test_execute_with_file(self):
        """Test execute with input file"""
        config = StepConfig(
            type="dqr",
            name="test",
            input="test.parquet",
            params={"metrics": ["completeness"]}
        )
        step = DQRStep(config)
        
        # Mock file reading
        test_df = pd.DataFrame({
            "dx": ["d1", "d2"],
            "value": [100, 200]
        })
        
        with patch('pandas.read_parquet', return_value=test_df):
            result = await step.execute(context={})
            
            assert result["status"] == "success"
            assert "dqr_results" in result


class TestTrackerStep:
    """Test TrackerStep"""
    
    def test_validate_params(self):
        """Test parameter validation"""
        config = StepConfig(
            type="tracker",
            name="test",
            params={"program": "prog1"}
        )
        step = TrackerStep(config)
        step.validate_params()  # Should not raise


class TestStepRegistry:
    """Test StepRegistry"""
    
    def test_step_registry(self):
        """Test step registry functionality"""
        registry = StepRegistry()
        assert registry is not None


class TestPipelineExecutor:
    """Test PipelineExecutor"""
    
    @pytest.mark.asyncio
    async def test_executor_init(self):
        """Test executor initialization"""
        config = PipelineConfig(
            name="test",
            steps=[
                StepConfig(type="analytics", name="step1", params={"dx": "d1", "ou": "o1", "pe": "2023"})
            ]
        )
        
        executor = PipelineExecutor(config)
        assert executor is not None
        assert executor.config == config

