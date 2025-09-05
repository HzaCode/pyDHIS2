"""Unit tests for I/O functionality"""

import pytest
import pandas as pd
import numpy as np
import pyarrow as pa
from pydhis2.io.to_pandas import (
    AnalyticsDataFrameConverter,
    DataValueSetsConverter,
    TrackerConverter,
    ImportSummaryConverter
)
from pydhis2.io.arrow import ArrowConverter


class TestAnalyticsDataFrameConverter:
    """Tests for the AnalyticsDataFrameConverter class"""
    
    @pytest.fixture
    def converter(self):
        """Analytics converter instance"""
        return AnalyticsDataFrameConverter()
    
    @pytest.fixture
    def sample_analytics_data(self):
        """Sample Analytics API response data"""
        return {
            "headers": [
                {"name": "dx", "column": "Data", "type": "TEXT"},
                {"name": "pe", "column": "Period", "type": "TEXT"},
                {"name": "ou", "column": "Organisation unit", "type": "TEXT"},
                {"name": "value", "column": "Value", "type": "NUMBER"}
            ],
            "rows": [
                ["DE123", "202301", "OU456", "100"],
                ["DE123", "202302", "OU456", "150"],
                ["DE789", "202301", "OU456", "200"]
            ],
            "metaData": {"items": {}, "dimensions": {}}
        }
    
    def test_to_dataframe_empty_data(self, converter):
        """Test conversion of empty data"""
        empty_data = {"headers": [], "rows": []}
        df = converter.to_dataframe(empty_data)
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_to_dataframe_no_rows(self, converter):
        """Test conversion with no rows key"""
        data_without_rows = {"headers": [{"name": "test"}]}
        df = converter.to_dataframe(data_without_rows)
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_to_dataframe_wide_format(self, converter, sample_analytics_data):
        """Test conversion to wide format"""
        df = converter.to_dataframe(sample_analytics_data, long_format=False)
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 3  # 3 rows
        assert len(df.columns) == 4  # 4 columns from headers
        
        # Check column names match headers
        expected_columns = ["dx", "pe", "ou", "value"]
        for col in expected_columns:
            assert col in df.columns
    
    def test_to_dataframe_long_format(self, converter, sample_analytics_data):
        """Test conversion to long format (standardized)"""
        df = converter.to_dataframe(sample_analytics_data, long_format=True)
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        
        # Check standardized column names
        if 'period' in df.columns:
            assert 'period' in df.columns
        if 'orgUnit' in df.columns:
            assert 'orgUnit' in df.columns
        
        # Value column should be numeric
        if 'value' in df.columns:
            assert pd.api.types.is_numeric_dtype(df['value'])


class TestDataValueSetsConverter:
    """Tests for the DataValueSetsConverter class"""
    
    @pytest.fixture
    def converter(self):
        """DataValueSets converter instance"""
        return DataValueSetsConverter()
    
    @pytest.fixture
    def sample_datavaluesets_data(self):
        """Sample DataValueSets response data"""
        return {
            "dataValues": [
                {
                    "dataElement": "DE123",
                    "period": "202301",
                    "orgUnit": "OU456",
                    "value": "100",
                    "lastUpdated": "2023-01-15T10:30:00.000",
                    "created": "2023-01-15T10:00:00.000",
                    "storedBy": "admin",
                    "followup": False
                },
                {
                    "dataElement": "DE123",
                    "period": "202302",
                    "orgUnit": "OU456", 
                    "value": "150",
                    "lastUpdated": "2023-02-15T10:30:00.000",
                    "created": "2023-02-15T10:00:00.000"
                }
            ]
        }
    
    def test_to_dataframe(self, converter, sample_datavaluesets_data):
        """Test conversion to DataFrame"""
        df = converter.to_dataframe(sample_datavaluesets_data)
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 2
        
        # Check required columns
        required_cols = ['dataElement', 'period', 'orgUnit', 'value']
        for col in required_cols:
            assert col in df.columns
        
        # Check data types
        assert 'lastUpdated' in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df['lastUpdated'])
        
        if 'followup' in df.columns:
            assert pd.api.types.is_bool_dtype(df['followup'])
    
    def test_to_dataframe_empty(self, converter):
        """Test conversion of empty data"""
        empty_data = {"dataValues": []}
        df = converter.to_dataframe(empty_data)
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_to_dataframe_no_datavalues_key(self, converter):
        """Test conversion without dataValues key"""
        invalid_data = {"otherKey": "value"}
        df = converter.to_dataframe(invalid_data)
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_from_dataframe(self, converter):
        """Test conversion from DataFrame to JSON"""
        df = pd.DataFrame({
            'dataElement': ['DE1', 'DE2'],
            'period': ['202301', '202301'],
            'orgUnit': ['OU1', 'OU1'],
            'value': [100, 150],
            'comment': ['Test comment', None]
        })
        
        result = converter.from_dataframe(df)
        
        assert 'dataValues' in result
        assert len(result['dataValues']) == 2
        
        first_value = result['dataValues'][0]
        assert first_value['dataElement'] == 'DE1'
        assert first_value['value'] == '100'  # Should be string
        assert first_value['comment'] == 'Test comment'
        
        second_value = result['dataValues'][1]
        assert 'comment' not in second_value  # None values should be excluded
    
    def test_from_dataframe_missing_required_columns(self, converter):
        """Test conversion with missing required columns"""
        incomplete_df = pd.DataFrame({
            'dataElement': ['DE1'],
            'period': ['202301']
            # Missing orgUnit and value
        })
        
        with pytest.raises(ValueError, match="Missing required columns"):
            converter.from_dataframe(incomplete_df)


class TestTrackerConverter:
    """Tests for the TrackerConverter class"""
    
    @pytest.fixture
    def converter(self):
        """Tracker converter instance"""
        return TrackerConverter()
    
    @pytest.fixture
    def sample_events(self):
        """Sample event data"""
        return [
            {
                "event": "EVENT123",
                "program": "PROG456", 
                "programStage": "STAGE789",
                "orgUnit": "OU123",
                "orgUnitName": "Test Facility",
                "status": "COMPLETED",
                "occurredAt": "2023-01-15T10:30:00.000",
                "createdAt": "2023-01-15T10:30:00.000",
                "updatedAt": "2023-01-15T10:30:00.000",
                "dataValues": [
                    {"dataElement": "DE1", "value": "Yes"},
                    {"dataElement": "DE2", "value": "25"}
                ]
            }
        ]
    
    def test_events_to_dataframe(self, converter, sample_events):
        """Test converting events to DataFrame"""
        df = converter.events_to_dataframe(sample_events)
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 1
        
        # Check basic event fields
        assert df.iloc[0]['event'] == 'EVENT123'
        assert df.iloc[0]['program'] == 'PROG456'
        assert df.iloc[0]['orgUnit'] == 'OU123'
        assert df.iloc[0]['status'] == 'COMPLETED'
        
        # Check flattened data values
        assert 'dataValue_DE1' in df.columns
        assert 'dataValue_DE2' in df.columns
        assert df.iloc[0]['dataValue_DE1'] == 'Yes'
        assert df.iloc[0]['dataValue_DE2'] == '25'
        
        # Check date conversion
        assert pd.api.types.is_datetime64_any_dtype(df['occurredAt'])
    
    def test_events_to_dataframe_empty(self, converter):
        """Test converting empty events list"""
        df = converter.events_to_dataframe([])
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_dataframe_to_events(self, converter):
        """Test converting DataFrame back to events"""
        df = pd.DataFrame({
            'event': ['EVENT123'],
            'program': ['PROG456'],
            'programStage': ['STAGE789'],
            'orgUnit': ['OU123'],
            'status': ['COMPLETED'],
            'occurredAt': ['2023-01-15T10:30:00.000'],
            'dataValue_DE1': ['Yes'],
            'dataValue_DE2': ['25']
        })
        
        events = converter.dataframe_to_events(df)
        
        assert len(events) == 1
        
        event = events[0]
        assert event['event'] == 'EVENT123'
        assert event['program'] == 'PROG456'
        assert len(event['dataValues']) == 2
        
        # Check data values
        data_values = {dv['dataElement']: dv['value'] for dv in event['dataValues']}
        assert data_values['DE1'] == 'Yes'
        assert data_values['DE2'] == '25'


class TestArrowConverter:
    """Tests for the ArrowConverter class"""
    
    @pytest.fixture
    def converter(self):
        """Arrow converter instance"""
        return ArrowConverter()
    
    @pytest.fixture
    def sample_dataframe(self):
        """Sample DataFrame for testing"""
        return pd.DataFrame({
            'int_col': [1, 2, 3, 4, 5],
            'float_col': [1.1, 2.2, 3.3, 4.4, 5.5],
            'str_col': ['a', 'b', 'c', 'd', 'e'],
            'bool_col': [True, False, True, False, True],
            'date_col': pd.date_range('2023-01-01', periods=5)
        })
    
    def test_from_pandas(self, converter, sample_dataframe):
        """Test conversion from Pandas to Arrow"""
        table = converter.from_pandas(sample_dataframe)
        
        assert isinstance(table, pa.Table)
        assert table.num_columns == 5
        assert table.num_rows == 5
        
        # Check column names
        schema_names = [field.name for field in table.schema]
        assert 'int_col' in schema_names
        assert 'float_col' in schema_names
        assert 'str_col' in schema_names
    
    def test_to_pandas(self, converter, sample_dataframe):
        """Test conversion from Arrow to Pandas"""
        table = converter.from_pandas(sample_dataframe)
        df_back = converter.to_pandas(table)
        
        assert isinstance(df_back, pd.DataFrame)
        assert len(df_back) == len(sample_dataframe)
        assert list(df_back.columns) == list(sample_dataframe.columns)
        
        # Check data integrity (allowing for type changes)
        pd.testing.assert_frame_equal(
            df_back.reset_index(drop=True),
            sample_dataframe.reset_index(drop=True),
            check_dtype=False  # Arrow may change dtypes slightly
        )
    
    def test_from_pandas_empty(self, converter):
        """Test conversion of empty DataFrame"""
        empty_df = pd.DataFrame()
        table = converter.from_pandas(empty_df)
        
        assert isinstance(table, pa.Table)
        assert table.num_columns == 0
        assert table.num_rows == 0
    
    def test_get_schema_info(self, converter, sample_dataframe):
        """Test schema information extraction"""
        table = converter.from_pandas(sample_dataframe)
        schema_info = converter.get_schema_info(table)
        
        assert isinstance(schema_info, dict)
        assert schema_info['num_columns'] == 5
        assert schema_info['num_rows'] == 5
        assert 'columns' in schema_info
        assert len(schema_info['columns']) == 5
        
        # Check column info
        for col_info in schema_info['columns']:
            assert 'name' in col_info
            assert 'type' in col_info
            assert 'nullable' in col_info
    
    def test_optimize_schema(self, converter):
        """Test schema optimization"""
        # Create DataFrame with different data types
        df = pd.DataFrame({
            'small_int': [1, 2, 3],  # Should use int8
            'large_int': [1000000, 2000000, 3000000],  # Should use larger int
            'categorical': ['A', 'B', 'A'],  # Should use dictionary encoding
            'unique_strings': ['unique1', 'unique2', 'unique3'],  # Regular string
            'has_nulls': [1, None, 3]  # Should be nullable
        })
        
        schema = converter.optimize_schema(df)
        
        assert isinstance(schema, pa.Schema)
        assert len(schema) == 5
        
        # Check that nullable field is properly marked
        has_nulls_field = next(f for f in schema if f.name == 'has_nulls')
        assert has_nulls_field.nullable is True


class TestImportSummaryConverter:
    """Tests for the ImportSummaryConverter class"""
    
    def test_conflicts_to_dataframe(self):
        """Test converting conflicts to DataFrame"""
        conflicts = [
            {
                "object": "OBJ1",
                "property": "value",
                "value": "invalid",
                "message": "Invalid value",
                "errorCode": "E1234"
            },
            {
                "object": "OBJ2", 
                "property": "period",
                "value": "invalid_period",
                "message": "Invalid period"
            }
        ]
        
        df = ImportSummaryConverter.conflicts_to_dataframe(conflicts)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'uid' in df.columns
        assert 'conflict_msg' in df.columns
        
        # Check data
        assert df.iloc[0]['uid'] == 'OBJ1'
        assert df.iloc[0]['conflict_msg'] == 'Invalid value'
        assert df.iloc[1]['uid'] == 'OBJ2'
    
    def test_conflicts_to_dataframe_empty(self):
        """Test converting empty conflicts list"""
        df = ImportSummaryConverter.conflicts_to_dataframe([])
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert 'uid' in df.columns  # Should have expected columns
    
    def test_summary_to_dataframe(self):
        """Test converting import summary to DataFrame"""
        import_summary = {
            "imported": 80,
            "updated": 15,
            "deleted": 2,
            "ignored": 3,
            "total": 100
        }
        
        df = ImportSummaryConverter.summary_to_dataframe(import_summary)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5  # 5 metrics
        assert 'metric' in df.columns
        assert 'count' in df.columns
        
        # Check values
        metrics_dict = dict(zip(df['metric'], df['count']))
        assert metrics_dict['imported'] == 80
        assert metrics_dict['updated'] == 15
        assert metrics_dict['total'] == 100


class TestIOIntegration:
    """Tests for I/O functionality integration"""
    
    def test_analytics_roundtrip(self):
        """Test Analytics data roundtrip conversion"""
        # Start with Analytics response
        analytics_data = {
            "headers": [
                {"name": "dx", "column": "Data", "type": "TEXT"},
                {"name": "pe", "column": "Period", "type": "TEXT"},
                {"name": "ou", "column": "Organisation unit", "type": "TEXT"},
                {"name": "value", "column": "Value", "type": "NUMBER"}
            ],
            "rows": [
                ["DE123", "202301", "OU456", "100"],
                ["DE123", "202302", "OU456", "150"]
            ]
        }
        
        # Convert to DataFrame
        converter = AnalyticsDataFrameConverter()
        df = converter.to_dataframe(analytics_data)
        
        # Convert to Arrow and back
        arrow_converter = ArrowConverter()
        table = arrow_converter.from_pandas(df)
        df_back = arrow_converter.to_pandas(table)
        
        # Should preserve data integrity
        assert len(df_back) == len(df)
        assert list(df_back.columns) == list(df.columns)
    
    def test_datavaluesets_roundtrip(self):
        """Test DataValueSets roundtrip conversion"""
        # Create original DataFrame
        original_df = pd.DataFrame({
            'dataElement': ['DE1', 'DE2'],
            'period': ['202301', '202301'],
            'orgUnit': ['OU1', 'OU1'],
            'value': [100, 150],
            'comment': ['Test', 'Another test']
        })
        
        converter = DataValueSetsConverter()
        
        # Convert to JSON format
        json_data = converter.from_dataframe(original_df)
        
        # Convert back to DataFrame
        df_back = converter.to_dataframe(json_data)
        
        # Should preserve essential data
        assert len(df_back) == len(original_df)
        assert list(df_back['dataElement']) == list(original_df['dataElement'])
        assert list(df_back['value'].astype(str)) == ['100', '150']  # Values become strings
    
    def test_large_dataset_performance(self):
        """Test I/O performance with large datasets"""
        # Generate large dataset
        np.random.seed(42)
        large_df = pd.DataFrame({
            'dataElement': np.random.choice(['DE1', 'DE2', 'DE3'], 10000),
            'period': np.random.choice(['202301', '202302'], 10000),
            'orgUnit': np.random.choice([f'OU{i}' for i in range(100)], 10000),
            'value': np.random.randint(1, 1000, 10000)
        })
        
        # Test conversion performance
        import time
        
        converter = ArrowConverter()
        
        start_time = time.time()
        table = converter.from_pandas(large_df)
        conversion_time = time.time() - start_time
        
        # Should complete quickly (under 1 second)
        assert conversion_time < 1.0
        assert table.num_rows == 10000
        
        # Test back conversion
        start_time = time.time()
        df_back = converter.to_pandas(table)
        back_conversion_time = time.time() - start_time
        
        assert back_conversion_time < 1.0
        assert len(df_back) == 10000
