"""Unit tests for DHIS2 API endpoints"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from pydhis2.core.types import AnalyticsQuery, ImportConfig, ImportStrategy, ExportFormat
from pydhis2.endpoints.analytics import AnalyticsEndpoint
from pydhis2.endpoints.datavaluesets import DataValueSetsEndpoint, ImportSummary
from pydhis2.endpoints.tracker import TrackerEndpoint
from pydhis2.core.errors import ImportConflictError


class TestAnalyticsEndpoint:
    """Tests for the AnalyticsEndpoint class"""
    
    @pytest.fixture
    def mock_client(self):
        """Mock DHIS2 client"""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def analytics_endpoint(self, mock_client):
        """Analytics endpoint instance"""
        return AnalyticsEndpoint(mock_client)
    
    @pytest.fixture
    def sample_analytics_response(self):
        """Sample Analytics API response"""
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
            "metaData": {"items": {}, "dimensions": {}},
            "width": 4,
            "height": 3
        }
    
    def test_init(self, analytics_endpoint, mock_client):
        """Test Analytics endpoint initialization"""
        assert analytics_endpoint.client is mock_client
        assert analytics_endpoint.converter is not None
        assert analytics_endpoint.arrow_converter is not None
    
    @pytest.mark.asyncio
    async def test_raw_query(self, analytics_endpoint, sample_analytics_response):
        """Test raw Analytics query"""
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(
            dx="DE123",
            ou="OU456", 
            pe="202301"
        )
        
        result = await analytics_endpoint.raw(query)
        
        assert result == sample_analytics_response
        analytics_endpoint.client.get.assert_called_once_with(
            '/api/analytics',
            params=query.to_params()
        )
    
    @pytest.mark.asyncio
    async def test_to_pandas(self, analytics_endpoint, sample_analytics_response):
        """Test conversion to Pandas DataFrame"""
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        df = await analytics_endpoint.to_pandas(query)
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 3  # 3 rows in sample data
        assert 'dx' in df.columns or 'Data' in df.columns
    
    @pytest.mark.asyncio
    async def test_validate_query(self, analytics_endpoint):
        """Test query validation"""
        analytics_endpoint.client.get.return_value = {"valid": True}
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        await analytics_endpoint.validate_query(query)
        
        # Should add dryRun parameter
        expected_params = query.to_params()
        expected_params['dryRun'] = 'true'
        
        analytics_endpoint.client.get.assert_called_once_with(
            '/api/analytics',
            params=expected_params
        )
    
    @pytest.mark.asyncio
    async def test_get_dimensions(self, analytics_endpoint):
        """Test getting available dimensions"""
        expected_response = {"dimensions": ["dx", "pe", "ou"]}
        analytics_endpoint.client.get.return_value = expected_response
        
        result = await analytics_endpoint.get_dimensions()
        
        assert result == expected_response
        analytics_endpoint.client.get.assert_called_once_with('/api/analytics/dimensions')
    
    @pytest.mark.asyncio
    async def test_get_dimension_items(self, analytics_endpoint):
        """Test getting items for a specific dimension"""
        dimension = "dx"
        expected_response = {"items": [{"id": "DE123", "name": "Data Element 1"}]}
        analytics_endpoint.client.get.return_value = expected_response
        
        result = await analytics_endpoint.get_dimension_items(dimension)
        
        assert result == expected_response
        analytics_endpoint.client.get.assert_called_once_with(f'/api/analytics/dimensions/{dimension}')
    
    @pytest.mark.asyncio
    async def test_raw_query_with_format(self, analytics_endpoint, sample_analytics_response):
        """Test raw query with custom format"""
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        await analytics_endpoint.raw(query, output_format="csv")
        
        expected_params = query.to_params()
        expected_params['format'] = 'csv'
        
        analytics_endpoint.client.get.assert_called_once_with(
            '/api/analytics',
            params=expected_params
        )
    
    @pytest.mark.asyncio
    async def test_to_arrow(self, analytics_endpoint, sample_analytics_response):
        """Test conversion to Arrow Table"""
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        # Mock the arrow converter
        import pyarrow as pa
        mock_table = pa.table({'dx': ['DE123'], 'value': [100]})
        
        with patch.object(analytics_endpoint.arrow_converter, 'from_pandas', return_value=mock_table) as mock_from_pandas:
            result = await analytics_endpoint.to_arrow(query)
        
        assert isinstance(result, pa.Table)
        mock_from_pandas.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stream_paginated(self, analytics_endpoint):
        """Test streaming with max pages limit"""
        # Mock responses for 2 pages
        page1_response = {
            "headers": [{"name": "dx", "column": "Data", "type": "TEXT"}],
            "rows": [["DE123"]],
            "pager": {"page": 1, "pageCount": 2}
        }
        page2_response = {
            "headers": [{"name": "dx", "column": "Data", "type": "TEXT"}],
            "rows": [["DE456"]],
            "pager": {"page": 2, "pageCount": 2}
        }
        
        analytics_endpoint.client.get.side_effect = [page1_response, page2_response]
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        results = []
        async for df in analytics_endpoint.stream_paginated(query, page_size=1):
            results.append(df)
        
        assert len(results) == 2
        assert analytics_endpoint.client.get.call_count == 2
        
        # Check parameters for pagination
        first_call_params = analytics_endpoint.client.get.call_args_list[0][1]['params']
        assert first_call_params['page'] == 1
        assert first_call_params['pageSize'] == 1
        assert first_call_params['paging'] == 'true'
    
    @pytest.mark.asyncio
    async def test_stream_paginated_max_pages(self, analytics_endpoint):
        """Test streaming with max pages limit"""
        mock_response = {
            "headers": [{"name": "dx", "column": "Data", "type": "TEXT"}],
            "rows": [["DE123"]],
            "pager": {"page": 1, "pageCount": 10}  # Many pages available
        }
        
        analytics_endpoint.client.get.return_value = mock_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        results = []
        async for df in analytics_endpoint.stream_paginated(query, max_pages=2):
            results.append(df)
        
        assert len(results) == 2
        assert analytics_endpoint.client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_stream_paginated_empty_page(self, analytics_endpoint):
        """Test streaming with empty page"""
        empty_response = {
            "headers": [{"name": "dx", "column": "Data", "type": "TEXT"}],
            "rows": [],
            "pager": {"page": 1, "pageCount": 1}
        }
        
        analytics_endpoint.client.get.return_value = empty_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        results = []
        async for df in analytics_endpoint.stream_paginated(query):
            results.append(df)
        
        assert len(results) == 0  # Empty DataFrame should not be yielded
    
    @pytest.mark.asyncio
    async def test_export_to_file_parquet(self, analytics_endpoint, sample_analytics_response):
        """Test export to Parquet file"""
        import tempfile
        from pathlib import Path
        
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "analytics.parquet")
            
            # Mock DataFrame.to_parquet
            with patch('pandas.DataFrame.to_parquet') as mock_to_parquet:
                result = await analytics_endpoint.export_to_file(
                    query, file_path, format=ExportFormat.PARQUET
                )
            
            assert result == file_path
            mock_to_parquet.assert_called_once_with(file_path)
    
    @pytest.mark.asyncio
    async def test_export_to_file_csv(self, analytics_endpoint, sample_analytics_response):
        """Test export to CSV file"""
        import tempfile
        from pathlib import Path
        
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "analytics.csv")
            
            with patch('pandas.DataFrame.to_csv') as mock_to_csv:
                result = await analytics_endpoint.export_to_file(
                    query, file_path, format=ExportFormat.CSV
                )
            
            assert result == file_path
            mock_to_csv.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_to_file_excel(self, analytics_endpoint, sample_analytics_response):
        """Test export to Excel file"""
        import tempfile
        from pathlib import Path
        
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "analytics.xlsx")
            
            with patch('pandas.DataFrame.to_excel') as mock_to_excel:
                await analytics_endpoint.export_to_file(
                    query, file_path, format=ExportFormat.EXCEL
                )
            
            mock_to_excel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_to_file_feather(self, analytics_endpoint, sample_analytics_response):
        """Test export to Feather file"""
        import tempfile
        from pathlib import Path
        
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "analytics.feather")
            
            with patch('pandas.DataFrame.to_feather') as mock_to_feather:
                await analytics_endpoint.export_to_file(
                    query, file_path, format=ExportFormat.FEATHER
                )
            
            mock_to_feather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_to_file_json(self, analytics_endpoint, sample_analytics_response):
        """Test export to JSON file"""
        import tempfile
        from pathlib import Path
        
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "analytics.json")
            
            with patch('pandas.DataFrame.to_json') as mock_to_json:
                await analytics_endpoint.export_to_file(
                    query, file_path, format=ExportFormat.JSON
                )
            
            mock_to_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_to_file_unsupported_format(self, analytics_endpoint, sample_analytics_response):
        """Test export with unsupported format"""
        import tempfile
        from pathlib import Path
        
        analytics_endpoint.client.get.return_value = sample_analytics_response
        
        query = AnalyticsQuery(dx="DE123", ou="OU456", pe="202301")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "analytics.unknown")
            
            with pytest.raises(ValueError, match="Unsupported export format"):
                await analytics_endpoint.export_to_file(
                    query, file_path, format="UNKNOWN_FORMAT"
                )


class TestImportSummary:
    """Tests for the ImportSummary class"""
    
    @pytest.fixture
    def sample_import_response(self):
        """Sample import response"""
        return {
            "status": "SUCCESS",
            "imported": 80,
            "updated": 15,
            "deleted": 0,
            "ignored": 5,
            "total": 100,
            "conflicts": [
                {
                    "object": "CONFLICT1",
                    "property": "value",
                    "value": "invalid",
                    "message": "Invalid data value"
                }
            ]
        }
    
    def test_init(self, sample_import_response):
        """Test ImportSummary initialization"""
        summary = ImportSummary(sample_import_response)
        
        assert summary.status == "SUCCESS"
        assert summary.imported == 80
        assert summary.updated == 15
        assert summary.deleted == 0
        assert summary.ignored == 5
        assert summary.total == 100
        assert summary.has_conflicts is True
        assert len(summary.conflicts) == 1
    
    def test_success_rate(self, sample_import_response):
        """Test success rate calculation"""
        summary = ImportSummary(sample_import_response)
        
        expected_rate = (80 + 15) / 100  # (imported + updated) / total
        assert summary.success_rate == expected_rate
    
    def test_success_rate_zero_total(self):
        """Test success rate with zero total"""
        summary = ImportSummary({"total": 0})
        assert summary.success_rate == 0.0
    
    def test_conflicts_df(self, sample_import_response):
        """Test conflicts DataFrame generation"""
        summary = ImportSummary(sample_import_response)
        
        conflicts_df = summary.conflicts_df
        
        assert isinstance(conflicts_df, pd.DataFrame)
        assert not conflicts_df.empty
        assert len(conflicts_df) == 1
        assert 'uid' in conflicts_df.columns
        assert 'conflict_msg' in conflicts_df.columns
        assert conflicts_df.iloc[0]['conflict_msg'] == "Invalid data value"
    
    def test_conflicts_df_empty(self):
        """Test conflicts DataFrame with no conflicts"""
        summary = ImportSummary({"conflicts": []})
        conflicts_df = summary.conflicts_df
        
        assert isinstance(conflicts_df, pd.DataFrame)
        assert conflicts_df.empty
    
    def test_to_dict(self, sample_import_response):
        """Test conversion to dictionary"""
        summary = ImportSummary(sample_import_response)
        
        result_dict = summary.to_dict()
        
        assert result_dict['status'] == "SUCCESS"
        assert result_dict['imported'] == 80
        assert result_dict['success_rate'] == 0.95
        assert result_dict['has_conflicts'] is True
        assert result_dict['conflicts_count'] == 1


class TestDataValueSetsEndpoint:
    """Tests for the DataValueSetsEndpoint class"""
    
    @pytest.fixture
    def mock_client(self):
        """Mock DHIS2 client"""
        return AsyncMock()
    
    @pytest.fixture
    def datavaluesets_endpoint(self, mock_client):
        """DataValueSets endpoint instance"""
        return DataValueSetsEndpoint(mock_client)
    
    @pytest.fixture
    def sample_datavaluesets_response(self):
        """Sample DataValueSets response"""
        return {
            "dataValues": [
                {
                    "dataElement": "DE123",
                    "period": "202301",
                    "orgUnit": "OU456",
                    "value": "100",
                    "lastUpdated": "2023-01-15T10:30:00.000"
                },
                {
                    "dataElement": "DE123",
                    "period": "202302", 
                    "orgUnit": "OU456",
                    "value": "150",
                    "lastUpdated": "2023-02-15T10:30:00.000"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_pull(self, datavaluesets_endpoint, sample_datavaluesets_response):
        """Test pulling data value sets"""
        datavaluesets_endpoint.client.get.return_value = sample_datavaluesets_response
        
        df = await datavaluesets_endpoint.pull(
            data_set="DS123",
            org_unit="OU456",
            period="202301"
        )
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 2
        
        # Check that correct parameters were passed
        datavaluesets_endpoint.client.get.assert_called_once_with(
            '/api/dataValueSets',
            params={
                'dataSet': 'DS123',
                'orgUnit': 'OU456',
                'period': '202301'
            }
        )
    
    @pytest.mark.asyncio
    async def test_pull_with_children(self, datavaluesets_endpoint, sample_datavaluesets_response):
        """Test pulling data with children parameter"""
        datavaluesets_endpoint.client.get.return_value = sample_datavaluesets_response
        
        await datavaluesets_endpoint.pull(
            org_unit="OU456",
            children=True,
            completed_only=True
        )
        
        # Check parameters
        call_args = datavaluesets_endpoint.client.get.call_args
        params = call_args[1]['params']
        
        assert params['orgUnit'] == 'OU456'
        assert params['children'] == 'true'
        assert params['completedOnly'] == 'true'
    
    @pytest.mark.asyncio
    async def test_push_single(self, datavaluesets_endpoint):
        """Test pushing small dataset (single chunk)"""
        # Mock successful import response
        import_response = {
            "status": "SUCCESS",
            "imported": 100,
            "updated": 0,
            "ignored": 0,
            "total": 100,
            "conflicts": []
        }
        datavaluesets_endpoint.client.post.return_value = import_response
        
        # Create test data
        test_data = pd.DataFrame({
            'dataElement': ['DE1', 'DE2'],
            'period': ['202301', '202301'],
            'orgUnit': ['OU1', 'OU1'],
            'value': [100, 150]
        })
        
        summary = await datavaluesets_endpoint.push(test_data)
        
        assert isinstance(summary, ImportSummary)
        assert summary.status == "SUCCESS"
        assert summary.imported == 100
        assert summary.success_rate == 1.0
        assert not summary.has_conflicts
    
    @pytest.mark.asyncio
    async def test_push_with_conflicts(self, datavaluesets_endpoint):
        """Test pushing data that results in conflicts"""
        import_response = {
            "status": "WARNING",
            "imported": 80,
            "updated": 0,
            "ignored": 15,
            "total": 100,
            "conflicts": [
                {
                    "object": "CONFLICT1",
                    "property": "value", 
                    "value": "invalid",
                    "message": "Invalid value"
                }
            ]
        }
        datavaluesets_endpoint.client.post.return_value = import_response
        
        test_data = pd.DataFrame({
            'dataElement': ['DE1'],
            'period': ['202301'],
            'orgUnit': ['OU1'],
            'value': ['invalid']
        })
        
        # Should raise ImportConflictError
        with pytest.raises(ImportConflictError) as exc_info:
            await datavaluesets_endpoint.push(test_data)
        
        assert len(exc_info.value.conflicts) == 1
        assert exc_info.value.conflicts[0]['message'] == "Invalid value"
    
    @pytest.mark.asyncio
    async def test_push_dry_run(self, datavaluesets_endpoint):
        """Test dry run import (should not raise on conflicts)"""
        import_response = {
            "status": "WARNING",
            "conflicts": [{"message": "Test conflict"}],
            "imported": 0,
            "total": 1
        }
        datavaluesets_endpoint.client.post.return_value = import_response
        
        test_data = pd.DataFrame({
            'dataElement': ['DE1'],
            'period': ['202301'],
            'orgUnit': ['OU1'],
            'value': ['test']
        })
        
        config = ImportConfig(dry_run=True)
        
        # Should not raise exception in dry run mode
        summary = await datavaluesets_endpoint.push(test_data, config=config)
        assert summary.has_conflicts is True
    
    @pytest.mark.asyncio
    async def test_get_import_status(self, datavaluesets_endpoint):
        """Test getting async import status"""
        status_response = {"status": "RUNNING", "progress": 50}
        datavaluesets_endpoint.client.get.return_value = status_response
        
        result = await datavaluesets_endpoint.get_import_status("task123")
        
        assert result == status_response
        datavaluesets_endpoint.client.get.assert_called_once_with(
            '/api/system/tasks/dataValueImport/task123'
        )
    
    @pytest.mark.asyncio
    async def test_pull_with_all_parameters(self, datavaluesets_endpoint, sample_datavaluesets_response):
        """Test pull with all possible parameters"""
        datavaluesets_endpoint.client.get.return_value = sample_datavaluesets_response
        
        await datavaluesets_endpoint.pull(
            data_set="DS123",
            org_unit="OU456", 
            period="202301",
            start_date="2023-01-01",
            end_date="2023-01-31",
            children=True,
            last_updated="2023-01-15T10:00:00",
            completed_only=True,
            include_deleted=True,
            custom_param="custom_value"
        )
        
        call_args = datavaluesets_endpoint.client.get.call_args
        params = call_args[1]['params']
        
        assert params['dataSet'] == 'DS123'
        assert params['orgUnit'] == 'OU456'
        assert params['period'] == '202301'
        assert params['startDate'] == '2023-01-01'
        assert params['endDate'] == '2023-01-31'
        assert params['children'] == 'true'
        assert params['lastUpdated'] == '2023-01-15T10:00:00'
        assert params['completedOnly'] == 'true'
        assert params['includeDeleted'] == 'true'
        assert params['custom_param'] == 'custom_value'
    
    @pytest.mark.asyncio 
    async def test_push_large_dataset_chunked(self, datavaluesets_endpoint):
        """Test pushing large dataset with chunking"""
        # Create large dataset that will be chunked
        large_data = pd.DataFrame({
            'dataElement': [f'DE{i}' for i in range(15000)],  # More than chunk size
            'period': ['202301'] * 15000,
            'orgUnit': [f'OU{i%100}' for i in range(15000)],
            'value': list(range(15000))
        })
        
        # Mock successful responses for all chunks
        import_response = {
            "status": "SUCCESS",
            "imported": 5000,
            "total": 5000
        }
        datavaluesets_endpoint.client.post.return_value = import_response
        
        summary = await datavaluesets_endpoint.push(large_data, chunk_size=5000)
        
        # Should have made 3 API calls (15000 / 5000 = 3 chunks)
        assert datavaluesets_endpoint.client.post.call_count == 3
        assert isinstance(summary, ImportSummary)
    
    @pytest.mark.asyncio
    async def test_push_with_custom_config(self, datavaluesets_endpoint):
        """Test push with custom import configuration"""
        test_data = pd.DataFrame({
            'dataElement': ['DE1'],
            'period': ['202301'], 
            'orgUnit': ['OU1'],
            'value': [100]
        })
        
        import_response = {"status": "SUCCESS", "imported": 1, "total": 1}
        datavaluesets_endpoint.client.post.return_value = import_response
        
        config = ImportConfig(
            strategy=ImportStrategy.CREATE_AND_UPDATE,
            dry_run=False,
            skip_existing_check=True,
            skip_audit=True
        )
        
        await datavaluesets_endpoint.push(test_data, config=config)
        
        # Check that config parameters were passed to API
        call_args = datavaluesets_endpoint.client.post.call_args
        params = call_args[1]['params']
        
        assert params['strategy'] == 'CREATE_AND_UPDATE'
        assert params['dryRun'] == 'false'
        assert params['skipExistingCheck'] == 'true'
        assert params['skipAudit'] == 'true'
    
    @pytest.mark.asyncio
    async def test_export_to_file_parquet(self, datavaluesets_endpoint, sample_datavaluesets_response):
        """Test export to Parquet file"""
        import tempfile
        from pathlib import Path
        
        datavaluesets_endpoint.client.get.return_value = sample_datavaluesets_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "datavalues.parquet")
            
            with patch('pandas.DataFrame.to_parquet') as mock_to_parquet:
                result = await datavaluesets_endpoint.export_to_file(
                    file_path, format=ExportFormat.PARQUET, data_set="DS123"
                )
            
            assert result == file_path
            mock_to_parquet.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_to_file_csv(self, datavaluesets_endpoint, sample_datavaluesets_response):
        """Test export to CSV file"""
        import tempfile
        from pathlib import Path
        
        datavaluesets_endpoint.client.get.return_value = sample_datavaluesets_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "datavalues.csv")
            
            with patch('pandas.DataFrame.to_csv') as mock_to_csv:
                await datavaluesets_endpoint.export_to_file(
                    file_path, format=ExportFormat.CSV, data_set="DS123"
                )
            
            mock_to_csv.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_unsupported_format(self, datavaluesets_endpoint, sample_datavaluesets_response):
        """Test export with unsupported format"""
        datavaluesets_endpoint.client.get.return_value = sample_datavaluesets_response
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            await datavaluesets_endpoint.export_to_file(
                "test.unknown", format="UNKNOWN_FORMAT", data_set="DS123"
            )
    
    @pytest.mark.asyncio
    async def test_validate_data_before_import(self, datavaluesets_endpoint):
        """Test data validation before import"""
        # Test with invalid data (missing required columns)
        invalid_data = pd.DataFrame({
            'dataElement': ['DE1'],
            # Missing required columns: period, orgUnit, value
        })
        
        # Should raise ValueError for missing required columns
        with pytest.raises(ValueError, match="Missing required columns"):
            await datavaluesets_endpoint.push(invalid_data)
    
    @pytest.mark.asyncio
    async def test_pull_paginated(self, datavaluesets_endpoint):
        """Test paginated data pulling"""
        # Mock paginated responses
        page1_response = {
            "dataValues": [{"dataElement": "DE1", "value": "100"}],
            "pager": {"page": 1, "pageCount": 2}
        }
        page2_response = {
            "dataValues": [{"dataElement": "DE2", "value": "200"}],
            "pager": {"page": 2, "pageCount": 2}
        }
        
        datavaluesets_endpoint.client.get.side_effect = [page1_response, page2_response]
        
        results = []
        async for df in datavaluesets_endpoint.pull_paginated(page_size=1, data_set="DS123"):
            results.append(df)
        
        assert len(results) == 2
        assert datavaluesets_endpoint.client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_pull_paginated_max_pages(self, datavaluesets_endpoint):
        """Test paginated pulling with max pages limit"""
        mock_response = {
            "dataValues": [{"dataElement": "DE1", "value": "100"}],
            "pager": {"page": 1, "pageCount": 10}
        }
        
        datavaluesets_endpoint.client.get.return_value = mock_response
        
        results = []
        async for df in datavaluesets_endpoint.pull_paginated(max_pages=2):
            results.append(df)
        
        assert len(results) == 2
        assert datavaluesets_endpoint.client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_pull_paginated_fallback(self, datavaluesets_endpoint):
        """Test paginated pulling fallback to non-paginated"""
        # Mock exception on first paginated call, then success on fallback
        sample_data = {
            "dataValues": [{"dataElement": "DE1", "value": "100"}]
        }
        
        datavaluesets_endpoint.client.get.side_effect = [
            Exception("Paging not supported"),  # First call fails
            sample_data  # Fallback call succeeds
        ]
        
        results = []
        async for df in datavaluesets_endpoint.pull_paginated():
            results.append(df)
        
        assert len(results) == 1
        assert datavaluesets_endpoint.client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_push_chunked_large_data(self, datavaluesets_endpoint):
        """Test pushing large data with chunking"""
        # Create large DataFrame
        large_data = pd.DataFrame({
            'dataElement': [f'DE{i}' for i in range(12000)],
            'period': ['202301'] * 12000,
            'orgUnit': [f'OU{i%100}' for i in range(12000)],
            'value': list(range(12000))
        })
        
        # Mock successful responses for all chunks
        success_response = {
            "status": "SUCCESS",
            "imported": 4000,
            "total": 4000
        }
        datavaluesets_endpoint.client.post.return_value = success_response
        
        summary = await datavaluesets_endpoint.push(large_data, chunk_size=4000)
        
        # Should have made 3 API calls (12000 / 4000 = 3 chunks)
        assert datavaluesets_endpoint.client.post.call_count == 3
        assert isinstance(summary, ImportSummary)
    
    @pytest.mark.asyncio
    async def test_push_with_resume(self, datavaluesets_endpoint):
        """Test pushing with resume from specific chunk"""
        # Create data that will be chunked
        data = pd.DataFrame({
            'dataElement': [f'DE{i}' for i in range(8000)],
            'period': ['202301'] * 8000,
            'orgUnit': ['OU1'] * 8000,
            'value': list(range(8000))
        })
        
        success_response = {
            "status": "SUCCESS",
            "imported": 4000,
            "total": 4000
        }
        datavaluesets_endpoint.client.post.return_value = success_response
        
        # Resume from chunk 1 (should skip first chunk)
        await datavaluesets_endpoint.push(data, chunk_size=4000, resume_from_chunk=1)
        
        # Should only make 1 API call (starting from chunk 1, which is the second chunk)
        assert datavaluesets_endpoint.client.post.call_count == 1
    
    
    @pytest.mark.asyncio
    async def test_export_to_file_all_formats(self, datavaluesets_endpoint, sample_datavaluesets_response):
        """Test export to all supported file formats"""
        import tempfile
        from pathlib import Path
        
        datavaluesets_endpoint.client.get.return_value = sample_datavaluesets_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test all formats
            formats = [
                (ExportFormat.PARQUET, "data.parquet", "to_parquet"),
                (ExportFormat.CSV, "data.csv", "to_csv"),
                (ExportFormat.EXCEL, "data.xlsx", "to_excel"),
                (ExportFormat.FEATHER, "data.feather", "to_feather"),
                (ExportFormat.JSON, "data.json", "to_json")
            ]
            
            for export_format, filename, pandas_method in formats:
                file_path = str(Path(temp_dir) / filename)
                
                with patch(f'pandas.DataFrame.{pandas_method}') as mock_method:
                    result = await datavaluesets_endpoint.export_to_file(
                        file_path, format=export_format, data_set="DS123"
                    )
                
                assert result == file_path
                mock_method.assert_called_once()


class TestTrackerEndpoint:
    """Tests for the TrackerEndpoint class"""
    
    @pytest.fixture
    def mock_client(self):
        """Mock DHIS2 client"""
        return AsyncMock()
    
    @pytest.fixture
    def tracker_endpoint(self, mock_client):
        """Tracker endpoint instance"""
        return TrackerEndpoint(mock_client)
    
    @pytest.fixture
    def sample_events_response(self):
        """Sample Tracker events response"""
        return {
            "instances": [
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
                        {
                            "dataElement": "DE1",
                            "value": "Yes"
                        },
                        {
                            "dataElement": "DE2", 
                            "value": "25"
                        }
                    ]
                }
            ],
            "page": {
                "page": 1,
                "pageSize": 50,
                "pageCount": 1,
                "total": 1
            }
        }
    
    @pytest.mark.asyncio
    async def test_events_raw(self, tracker_endpoint, sample_events_response):
        """Test getting raw events data"""
        tracker_endpoint.client.get.return_value = sample_events_response
        
        result = await tracker_endpoint.events(
            program="PROG456",
            org_unit="OU123",
            status="COMPLETED"
        )
        
        assert result == sample_events_response
        
        # Check parameters
        call_args = tracker_endpoint.client.get.call_args
        params = call_args[1]['params']
        assert params['program'] == 'PROG456'
        assert params['orgUnit'] == 'OU123'
        assert params['status'] == 'COMPLETED'
    
    @pytest.mark.asyncio
    async def test_events_to_pandas(self, tracker_endpoint, sample_events_response):
        """Test converting events to DataFrame"""
        tracker_endpoint.client.get.return_value = sample_events_response
        
        df = await tracker_endpoint.events_to_pandas(
            program="PROG456",
            org_unit="OU123"
        )
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 1  # 1 event in sample
        
        # Check that data values are flattened
        assert 'event' in df.columns
        assert 'program' in df.columns
        assert 'dataValue_DE1' in df.columns
        assert 'dataValue_DE2' in df.columns
        
        # Check values
        assert df.iloc[0]['dataValue_DE1'] == 'Yes'
        assert df.iloc[0]['dataValue_DE2'] == '25'
    
    @pytest.mark.asyncio
    async def test_get_event(self, tracker_endpoint):
        """Test getting a single event"""
        event_response = {"event": "EVENT123", "status": "COMPLETED"}
        tracker_endpoint.client.get.return_value = event_response
        
        result = await tracker_endpoint.get_event("EVENT123")
        
        assert result == event_response
        tracker_endpoint.client.get.assert_called_once_with('/api/tracker/events/EVENT123')
    
    @pytest.mark.asyncio
    async def test_create_event(self, tracker_endpoint):
        """Test creating an event"""
        create_response = {"status": "SUCCESS", "imported": 1}
        tracker_endpoint.client.post.return_value = create_response
        
        event_data = {
            "program": "PROG456",
            "orgUnit": "OU123",
            "status": "ACTIVE"
        }
        
        result = await tracker_endpoint.create_event(event_data)
        
        assert result == create_response
        
        # Check that event was wrapped in events array
        call_args = tracker_endpoint.client.post.call_args
        posted_data = call_args[1]['data']
        assert 'events' in posted_data
        assert posted_data['events'][0] == event_data


class TestEndpointIntegration:
    """Integration tests using a mock server"""
    
    @pytest.mark.asyncio
    async def test_analytics_end_to_end(self):
        """Test Analytics endpoint end-to-end"""
        from pydhis2.testing import MockDHIS2Server, TestDataGenerator
        
        # Setup test data
        generator = TestDataGenerator()
        org_units = generator.generate_org_units(3)
        data_elements = generator.generate_data_elements(2)
        periods = generator.generate_periods(months=3)
        
        # Start mock server
        mock_server = MockDHIS2Server(port=8085)
        analytics_response = generator.generate_analytics_response(
            data_elements, org_units, periods, null_rate=0.0
        )
        mock_server.configure_analytics_response(
            analytics_response["headers"],
            analytics_response["rows"]
        )
        
        async with mock_server as base_url:
            from pydhis2.core.types import DHIS2Config
            from pydhis2.core.client import AsyncDHIS2Client
            
            config = DHIS2Config(base_url=base_url, auth=("test", "test"))
            
            async with AsyncDHIS2Client(config) as client:
                query = AnalyticsQuery(
                    dx=data_elements[0]["id"],
                    ou=org_units[0]["id"],
                    pe=periods[0]
                )
                
                df = await client.analytics.to_pandas(query)
                
                assert isinstance(df, pd.DataFrame)
                assert not df.empty
                # Should have data for the query
                assert len(df) >= 1
    
    @pytest.mark.asyncio
    async def test_datavaluesets_import_end_to_end(self):
        """Test DataValueSets import end-to-end"""
        from pydhis2.testing import MockDHIS2Server
        
        # Setup mock server
        mock_server = MockDHIS2Server(port=8086)
        mock_server.configure_import_response(
            imported=100,
            updated=0,
            ignored=0
        )
        
        async with mock_server as base_url:
            from pydhis2.core.types import DHIS2Config
            from pydhis2.core.client import AsyncDHIS2Client
            
            config = DHIS2Config(base_url=base_url, auth=("test", "test"))
            
            async with AsyncDHIS2Client(config) as client:
                # Create test data
                test_data = pd.DataFrame({
                    'dataElement': ['DE1', 'DE2'],
                    'period': ['202301', '202301'],
                    'orgUnit': ['OU1', 'OU1'],
                    'value': [100, 150]
                })
                
                summary = await client.datavaluesets.push(test_data)
                
                assert isinstance(summary, ImportSummary)
                assert summary.imported == 100
                assert summary.success_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_tracker_events_end_to_end(self):
        """Test Tracker events end-to-end"""
        from pydhis2.testing import MockDHIS2Server, TestDataGenerator
        
        # Setup test data
        generator = TestDataGenerator()
        org_units = generator.generate_org_units(2)
        
        # Setup mock server
        mock_server = MockDHIS2Server(port=8087)
        events_response = generator.generate_tracker_events(
            "PROG123", "STAGE456", org_units, event_count=5
        )
        mock_server.configure_endpoint(
            "GET", "/api/tracker/events",
            events_response
        )
        
        async with mock_server as base_url:
            from pydhis2.core.types import DHIS2Config
            from pydhis2.core.client import AsyncDHIS2Client
            
            config = DHIS2Config(base_url=base_url, auth=("test", "test"))
            
            async with AsyncDHIS2Client(config) as client:
                df = await client.tracker.events_to_pandas(
                    program="PROG123",
                    org_unit=org_units[0]["id"]
                )
                
                assert isinstance(df, pd.DataFrame)
                assert not df.empty
                assert len(df) == 5  # Should have 5 events
                assert 'event' in df.columns
                assert 'program' in df.columns
