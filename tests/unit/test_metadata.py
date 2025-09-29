"""Tests for the metadata endpoint"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from pydhis2.endpoints.metadata import MetadataEndpoint, MetadataImportSummary
from pydhis2.core.errors import ImportConflictError
from pydhis2.core.types import ExportFormat


class TestMetadataImportSummary:
    """Tests for the MetadataImportSummary class"""
    
    def test_init_basic(self):
        """Test basic initialization"""
        summary_data = {
            'status': 'SUCCESS',
            'stats': {'created': 5, 'updated': 3},
            'typeReports': []
        }
        
        summary = MetadataImportSummary(summary_data)
        assert summary.raw_data == summary_data
        assert summary.status == 'SUCCESS'
        assert summary.stats == {'created': 5, 'updated': 3}
        assert summary.type_reports == []
    
    def test_init_with_type_reports(self):
        """Test initialization with type reports"""
        summary_data = {
            'status': 'SUCCESS',
            'typeReports': [
                {
                    'klass': 'DataElement',
                    'objectReports': [
                        {'index': 0, 'uid': 'abc123', 'message': 'created'},
                        {'index': 1, 'uid': 'def456', 'message': 'updated'},
                        {'index': 2, 'uid': 'ghi789', 'message': 'ignored'}
                    ]
                }
            ]
        }
        
        summary = MetadataImportSummary(summary_data)
        assert summary.total == 3
        assert summary.imported == 1
        assert summary.updated == 1
        assert summary.ignored == 1
    
    def test_success_rate(self):
        """Test success rate calculation"""
        summary_data = {
            'typeReports': [
                {
                    'objectReports': [
                        {'index': 0, 'message': 'created'},
                        {'index': 1, 'message': 'updated'},
                        {'index': 2, 'message': 'ignored'},
                        {'index': 3, 'message': 'error'}
                    ]
                }
            ]
        }
        
        summary = MetadataImportSummary(summary_data)
        assert summary.success_rate == 0.5  # 2 out of 4
    
    def test_success_rate_zero_total(self):
        """Test success rate with zero total"""
        summary_data = {'typeReports': []}
        summary = MetadataImportSummary(summary_data)
        assert summary.success_rate == 0.0
    
    def test_has_errors_true(self):
        """Test has_errors property with errors"""
        summary_data = {'status': 'ERROR'}
        summary = MetadataImportSummary(summary_data)
        assert summary.has_errors is True
        
        summary_data = {'status': 'WARNING'}
        summary = MetadataImportSummary(summary_data)
        assert summary.has_errors is True
    
    def test_has_errors_false(self):
        """Test has_errors property without errors"""
        summary_data = {'status': 'SUCCESS'}
        summary = MetadataImportSummary(summary_data)
        assert summary.has_errors is False
    
    def test_get_conflicts_df(self):
        """Test conflicts DataFrame generation"""
        summary_data = {
            'typeReports': [
                {
                    'klass': 'DataElement',
                    'objectReports': [
                        {
                            'uid': 'abc123',
                            'index': 0,
                            'errorReports': [
                                {
                                    'errorCode': 'E1001',
                                    'message': 'Duplicate name',
                                    'property': 'name',
                                    'value': 'Test Element'
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        summary = MetadataImportSummary(summary_data)
        conflicts_df = summary.get_conflicts_df()
        
        assert len(conflicts_df) == 1
        assert conflicts_df.iloc[0]['object_type'] == 'DataElement'
        assert conflicts_df.iloc[0]['uid'] == 'abc123'
        assert conflicts_df.iloc[0]['error_code'] == 'E1001'
        assert conflicts_df.iloc[0]['message'] == 'Duplicate name'
    
    def test_get_conflicts_df_empty(self):
        """Test conflicts DataFrame with no conflicts"""
        summary_data = {'typeReports': []}
        summary = MetadataImportSummary(summary_data)
        conflicts_df = summary.get_conflicts_df()
        
        assert len(conflicts_df) == 0
        # Empty DataFrame may not have columns, just check it's a DataFrame
        assert isinstance(conflicts_df, pd.DataFrame)


class TestMetadataEndpoint:
    """Tests for the metadata endpoint class"""
    
    def setup_method(self):
        """Setup test endpoint"""
        self.mock_client = AsyncMock()
        self.endpoint = MetadataEndpoint(self.mock_client)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test endpoint initialization"""
        assert self.endpoint.client == self.mock_client
    
    async def test_export_basic(self):
        """Test basic metadata export"""
        expected_response = {'dataElements': [{'id': 'test', 'name': 'Test Element'}]}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.export()
        
        self.mock_client.get.assert_called_once_with(
            '/api/metadata',
            params={
                'fields': ':owner',
                'defaults': 'INCLUDE',
                'download': 'false'
            }
        )
        assert result == expected_response
    
    async def test_export_with_filter(self):
        """Test metadata export with filter"""
        filter_params = {'name': 'Test', 'code': 'TEST'}
        
        await self.endpoint.export(filter=filter_params)
        
        call_args = self.mock_client.get.call_args
        params = call_args[1]['params']
        assert 'name:filter' in params
        assert 'code:filter' in params
        assert params['name:filter'] == 'Test'
        assert params['code:filter'] == 'TEST'
    
    async def test_export_with_custom_params(self):
        """Test metadata export with custom parameters"""
        await self.endpoint.export(
            fields='id,name',
            defaults='EXCLUDE',
            download=True,
            custom_param='value'
        )
        
        call_args = self.mock_client.get.call_args
        params = call_args[1]['params']
        assert params['fields'] == 'id,name'
        assert params['defaults'] == 'EXCLUDE'
        assert params['download'] == 'true'
        assert params['custom_param'] == 'value'
    
    async def test_import_dict(self):
        """Test metadata import with dictionary"""
        metadata = {'dataElements': [{'name': 'Test Element'}]}
        import_response = {
            'status': 'SUCCESS',
            'stats': {'created': 1},
            'typeReports': []
        }
        
        self.mock_client.post.return_value = import_response
        
        result = await self.endpoint.import_(metadata)
        
        assert isinstance(result, MetadataImportSummary)
        assert result.status == 'SUCCESS'
        
        self.mock_client.post.assert_called_once()
        call_args = self.mock_client.post.call_args
        assert call_args[0][0] == '/api/metadata'
        assert call_args[1]['data'] == metadata
    
    async def test_import_string(self):
        """Test metadata import with JSON string"""
        metadata_dict = {'dataElements': [{'name': 'Test Element'}]}
        metadata_string = json.dumps(metadata_dict)
        import_response = {
            'status': 'SUCCESS',
            'stats': {'created': 1},
            'typeReports': []
        }
        
        self.mock_client.post.return_value = import_response
        
        result = await self.endpoint.import_(metadata_string)
        
        assert isinstance(result, MetadataImportSummary)
        
        call_args = self.mock_client.post.call_args
        assert call_args[1]['data'] == metadata_dict
    
    async def test_import_with_conflicts(self):
        """Test metadata import with conflicts"""
        metadata = {'dataElements': [{'name': 'Test Element'}]}
        import_response = {
            'status': 'ERROR',
            'typeReports': [
                {
                    'klass': 'DataElement',
                    'objectReports': [
                        {
                            'uid': 'abc123',
                            'index': 0,
                            'errorReports': [
                                {
                                    'errorCode': 'E1001',
                                    'message': 'Duplicate name'
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        self.mock_client.post.return_value = import_response
        
        with pytest.raises(ImportConflictError):
            await self.endpoint.import_(metadata)
    
    async def test_import_dry_run_with_conflicts(self):
        """Test metadata import dry run with conflicts (should not raise)"""
        metadata = {'dataElements': [{'name': 'Test Element'}]}
        import_response = {
            'status': 'ERROR',
            'typeReports': [
                {
                    'klass': 'DataElement',
                    'objectReports': [
                        {
                            'uid': 'abc123',
                            'index': 0,
                            'errorReports': [
                                {
                                    'errorCode': 'E1001',
                                    'message': 'Duplicate name'
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        self.mock_client.post.return_value = import_response
        
        # Dry run should not raise exception even with errors
        result = await self.endpoint.import_(metadata, dry_run=True)
        assert isinstance(result, MetadataImportSummary)
        assert result.has_errors is True
    
    async def test_import_custom_params(self):
        """Test metadata import with custom parameters"""
        metadata = {'dataElements': []}
        import_response = {'status': 'SUCCESS', 'typeReports': []}
        
        self.mock_client.post.return_value = import_response
        
        await self.endpoint.import_(
            metadata,
            atomic=False,
            strategy="MERGE",
            merge_mode="MERGE",
            flush_mode="OBJECT",
            skip_sharing=True,
            skip_validation=True
        )
        
        call_args = self.mock_client.post.call_args
        params = call_args[1]['params']
        assert params['atomic'] == 'false'
        assert params['importStrategy'] == 'MERGE'
        assert params['mergeMode'] == 'MERGE'
        assert params['flushMode'] == 'OBJECT'
        assert params['skipSharing'] == 'true'
        assert params['skipValidation'] == 'true'
    
    async def test_get_schemas(self):
        """Test get schemas"""
        expected_response = {'schemas': [{'name': 'dataElement'}]}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.get_schemas()
        
        self.mock_client.get.assert_called_once_with('/api/schemas')
        assert result == expected_response
    
    async def test_get_schema(self):
        """Test get specific schema"""
        schema_name = 'dataElement'
        expected_response = {'name': 'dataElement', 'properties': []}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.get_schema(schema_name)
        
        self.mock_client.get.assert_called_once_with(f'/api/schemas/{schema_name}')
        assert result == expected_response
    
    async def test_get_data_elements(self):
        """Test get data elements"""
        expected_response = {'dataElements': [{'id': 'test', 'name': 'Test'}]}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.get_data_elements()
        
        self.mock_client.get.assert_called_once_with(
            '/api/dataElements',
            params={
                'fields': 'id,name,code,valueType',
                'paging': 'false'
            }
        )
        assert result == expected_response
    
    async def test_get_data_elements_with_filter(self):
        """Test get data elements with filter"""
        filter_params = {'name': 'Test'}
        
        await self.endpoint.get_data_elements(filter=filter_params)
        
        call_args = self.mock_client.get.call_args
        params = call_args[1]['params']
        assert 'filter' in params
        assert params['filter'] == 'name:eq:Test'
    
    async def test_get_indicators(self):
        """Test get indicators"""
        expected_response = {'indicators': [{'id': 'test', 'name': 'Test Indicator'}]}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.get_indicators()
        
        self.mock_client.get.assert_called_once_with(
            '/api/indicators',
            params={
                'fields': 'id,name,code,numerator,denominator',
                'paging': 'false'
            }
        )
        assert result == expected_response
    
    async def test_get_indicators_with_custom_fields(self):
        """Test get indicators with custom fields"""
        await self.endpoint.get_indicators(
            fields='id,name',
            paging=True,
            pageSize=50
        )
        
        call_args = self.mock_client.get.call_args
        params = call_args[1]['params']
        assert params['fields'] == 'id,name'
        assert params['paging'] == 'true'
        assert params['pageSize'] == 50
    
    async def test_get_organisation_units(self):
        """Test get organisation units"""
        expected_response = {'organisationUnits': [{'id': 'test', 'name': 'Test Org'}]}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.get_organisation_units()
        
        self.mock_client.get.assert_called_once_with(
            '/api/organisationUnits',
            params={
                'fields': 'id,name,code,level,path',
                'paging': 'false'
            }
        )
        assert result == expected_response
    
    async def test_get_option_sets(self):
        """Test get option sets"""
        expected_response = {'optionSets': [{'id': 'test', 'name': 'Test Options'}]}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.get_option_sets()
        
        self.mock_client.get.assert_called_once_with(
            '/api/optionSets',
            params={
                'fields': 'id,name,code,options[id,name,code]',
                'paging': 'false'
            }
        )
        assert result == expected_response
    
    async def test_validate_metadata(self):
        """Test metadata validation (dry run)"""
        metadata = {'dataElements': [{'name': 'Test'}]}
        expected_response = {'status': 'SUCCESS', 'typeReports': []}
        
        # Mock the import_ method
        with patch.object(self.endpoint, 'import_', return_value=expected_response) as mock_import:
            result = await self.endpoint.validate_metadata(metadata)
        
        mock_import.assert_called_once_with(metadata, dry_run=True)
        assert result == expected_response
    
    async def test_export_to_file_json(self):
        """Test export metadata to JSON file"""
        metadata = {'dataElements': [{'id': 'test', 'name': 'Test'}]}
        self.mock_client.get.return_value = metadata
        
        file_path = Path(self.temp_dir) / "metadata.json"
        
        result = await self.endpoint.export_to_file(str(file_path))
        
        assert result == str(file_path)
        assert file_path.exists()
        
        # Verify file contents
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == metadata
    
    async def test_export_to_file_unsupported_format(self):
        """Test export to file with unsupported format"""
        file_path = Path(self.temp_dir) / "metadata.xml"
        
        with pytest.raises(ValueError, match="Metadata export only supports JSON format"):
            await self.endpoint.export_to_file(str(file_path), format=ExportFormat.CSV)
    
    async def test_import_from_file(self):
        """Test import metadata from file"""
        metadata = {'dataElements': [{'name': 'Test Element'}]}
        file_path = Path(self.temp_dir) / "metadata.json"
        
        # Create test file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f)
        
        import_response = {'status': 'SUCCESS', 'typeReports': []}
        
        # Mock the import_ method
        with patch.object(self.endpoint, 'import_', return_value=MetadataImportSummary(import_response)) as mock_import:
            result = await self.endpoint.import_from_file(str(file_path))
        
        mock_import.assert_called_once_with(metadata)
        assert isinstance(result, MetadataImportSummary)
    
    async def test_import_from_file_with_params(self):
        """Test import metadata from file with parameters"""
        metadata = {'dataElements': []}
        file_path = Path(self.temp_dir) / "metadata.json"
        
        # Create test file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f)
        
        import_response = {'status': 'SUCCESS', 'typeReports': []}
        
        with patch.object(self.endpoint, 'import_', return_value=MetadataImportSummary(import_response)) as mock_import:
            await self.endpoint.import_from_file(
                str(file_path),
                atomic=False,
                dry_run=True
            )
        
        mock_import.assert_called_once_with(
            metadata,
            atomic=False,
            dry_run=True
        )


class TestMetadataIntegration:
    """Tests for metadata endpoint integration scenarios"""
    
    def setup_method(self):
        """Setup integration tests"""
        self.mock_client = AsyncMock()
        self.endpoint = MetadataEndpoint(self.mock_client)
    
    async def test_full_export_import_cycle(self):
        """Test complete export-import cycle"""
        # Mock export
        export_data = {
            'dataElements': [
                {'id': 'elem1', 'name': 'Element 1', 'code': 'ELEM1'}
            ]
        }
        self.mock_client.get.return_value = export_data
        
        # Mock import
        import_response = {
            'status': 'SUCCESS',
            'stats': {'created': 1},
            'typeReports': []
        }
        self.mock_client.post.return_value = import_response
        
        # Export
        exported = await self.endpoint.export(filter={'code': 'ELEM'})
        assert exported == export_data
        
        # Import
        summary = await self.endpoint.import_(exported)
        assert summary.status == 'SUCCESS'
        assert summary.total >= 0
    
    async def test_validation_workflow(self):
        """Test metadata validation workflow"""
        metadata = {'dataElements': [{'name': 'Invalid Element'}]}
        validation_response = {
            'status': 'ERROR',
            'typeReports': [
                {
                    'klass': 'DataElement',
                    'objectReports': [
                        {
                            'uid': 'abc123',
                            'errorReports': [
                                {'errorCode': 'E1001', 'message': 'Invalid name'}
                            ]
                        }
                    ]
                }
            ]
        }
        
        self.mock_client.post.return_value = validation_response
        
        # Validation should return summary without raising exception
        result = await self.endpoint.validate_metadata(metadata)
        assert isinstance(result, MetadataImportSummary)
        assert result.has_errors is True
        
        conflicts_df = result.get_conflicts_df()
        assert len(conflicts_df) == 1
        assert conflicts_df.iloc[0]['error_code'] == 'E1001'
    
    async def test_metadata_queries_with_filters(self):
        """Test various metadata queries with filters"""
        # Test data elements query
        self.mock_client.get.return_value = {'dataElements': []}
        await self.endpoint.get_data_elements(filter={'valueType': 'NUMBER'})
        
        # Test indicators query  
        await self.endpoint.get_indicators(filter={'indicatorType': 'TYPE1'})
        
        # Test org units query
        await self.endpoint.get_organisation_units(filter={'level': '3'})
        
        # Test option sets query
        await self.endpoint.get_option_sets(filter={'name': 'Colors'})
        
        # Verify all calls were made
        assert self.mock_client.get.call_count == 4
