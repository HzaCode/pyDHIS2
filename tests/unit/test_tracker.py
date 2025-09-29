"""Tests for the tracker endpoint"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from pydhis2.endpoints.tracker import TrackerEndpoint
from pydhis2.core.types import ExportFormat
from pydhis2.io.to_pandas import TrackerConverter
from pydhis2.io.arrow import ArrowConverter


class TestTrackerEndpoint:
    """Tests for the TrackerEndpoint class"""
    
    def setup_method(self):
        """Setup test endpoint"""
        self.mock_client = AsyncMock()
        self.endpoint = TrackerEndpoint(self.mock_client)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test endpoint initialization"""
        assert self.endpoint.client == self.mock_client
        assert isinstance(self.endpoint.converter, TrackerConverter)
        assert isinstance(self.endpoint.arrow_converter, ArrowConverter)
    
    async def test_events_basic(self):
        """Test basic events query"""
        expected_response = {
            'instances': [
                {'event': 'event1', 'program': 'prog1'},
                {'event': 'event2', 'program': 'prog1'}
            ]
        }
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.events()
        
        self.mock_client.get.assert_called_once_with(
            '/api/tracker/events',
            params={
                'page': 1,
                'pageSize': 50,
                'totalPages': 'false',
                'skipMeta': 'false',
                'ouMode': 'SELECTED'
            }
        )
        assert result == expected_response
    
    async def test_events_with_parameters(self):
        """Test events query with all parameters"""
        await self.endpoint.events(
            program='PROG123',
            org_unit='ORG456',
            org_unit_mode='DESCENDANTS',
            status='COMPLETED',
            program_stage='STAGE789',
            start_date='2024-01-01',
            end_date='2024-12-31',
            last_updated_start_date='2024-01-01',
            last_updated_end_date='2024-12-31',
            skip_meta=True,
            page=2,
            page_size=100,
            total_pages=True,
            custom_param='value'
        )
        
        call_args = self.mock_client.get.call_args
        params = call_args[1]['params']
        
        assert params['program'] == 'PROG123'
        assert params['orgUnit'] == 'ORG456'
        assert params['ouMode'] == 'DESCENDANTS'
        assert params['status'] == 'COMPLETED'
        assert params['programStage'] == 'STAGE789'
        assert params['startDate'] == '2024-01-01'
        assert params['endDate'] == '2024-12-31'
        assert params['lastUpdatedStartDate'] == '2024-01-01'
        assert params['lastUpdatedEndDate'] == '2024-12-31'
        assert params['skipMeta'] == 'true'
        assert params['page'] == 2
        assert params['pageSize'] == 100
        assert params['totalPages'] == 'true'
        assert params['custom_param'] == 'value'
    
    async def test_events_to_pandas_single_page(self):
        """Test events to pandas with single page"""
        mock_events = [
            {'event': 'event1', 'program': 'prog1'},
            {'event': 'event2', 'program': 'prog1'}
        ]
        
        mock_response = {
            'instances': mock_events,
            'page': {'pageCount': 1}
        }
        
        self.mock_client.get.return_value = mock_response
        
        # Mock converter
        expected_df = pd.DataFrame([{'event_id': 'event1'}, {'event_id': 'event2'}])
        with patch.object(self.endpoint.converter, 'events_to_dataframe', return_value=expected_df) as mock_convert:
            result = await self.endpoint.events_to_pandas(program='PROG123')
        
        mock_convert.assert_called_once_with(mock_events)
        assert result.equals(expected_df)
    
    async def test_events_to_pandas_multiple_pages(self):
        """Test events to pandas with multiple pages"""
        # First page response
        page1_response = {
            'instances': [{'event': 'event1'}],
            'page': {'pageCount': 2}
        }
        
        # Second page response
        page2_response = {
            'instances': [{'event': 'event2'}],
            'page': {'pageCount': 2}
        }
        
        self.mock_client.get.side_effect = [page1_response, page2_response]
        
        # Mock converter
        expected_df = pd.DataFrame([{'event_id': 'event1'}, {'event_id': 'event2'}])
        with patch.object(self.endpoint.converter, 'events_to_dataframe', return_value=expected_df) as mock_convert:
            await self.endpoint.events_to_pandas()
        
        # Should have called converter with all events
        mock_convert.assert_called_once_with([{'event': 'event1'}, {'event': 'event2'}])
        assert self.mock_client.get.call_count == 2
    
    async def test_events_to_pandas_max_pages(self):
        """Test events to pandas with max pages limit"""
        mock_response = {
            'instances': [{'event': 'event1'}],
            'page': {'pageCount': 10}  # Many pages available
        }
        
        self.mock_client.get.return_value = mock_response
        
        expected_df = pd.DataFrame([{'event_id': 'event1'}])
        with patch.object(self.endpoint.converter, 'events_to_dataframe', return_value=expected_df):
            await self.endpoint.events_to_pandas(max_pages=2)
        
        # Should only call 2 pages
        assert self.mock_client.get.call_count == 2
    
    async def test_events_to_pandas_empty_response(self):
        """Test events to pandas with empty response"""
        empty_response = {'instances': []}
        self.mock_client.get.return_value = empty_response
        
        expected_df = pd.DataFrame()
        with patch.object(self.endpoint.converter, 'events_to_dataframe', return_value=expected_df):
            result = await self.endpoint.events_to_pandas()
        
        assert result.empty
        assert self.mock_client.get.call_count == 1
    
    async def test_tracked_entities_basic(self):
        """Test basic tracked entities query"""
        expected_response = {
            'instances': [
                {'trackedEntity': 'te1', 'trackedEntityType': 'person'},
                {'trackedEntity': 'te2', 'trackedEntityType': 'person'}
            ]
        }
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.tracked_entities()
        
        self.mock_client.get.assert_called_once_with(
            '/api/tracker/trackedEntities',
            params={
                'page': 1,
                'pageSize': 50,
                'totalPages': 'false',
                'ouMode': 'SELECTED',
                'fields': '*'
            }
        )
        assert result == expected_response
    
    async def test_tracked_entities_with_parameters(self):
        """Test tracked entities query with parameters"""
        await self.endpoint.tracked_entities(
            org_unit='ORG123',
            org_unit_mode='CHILDREN',
            program='PROG456',
            tracked_entity_type='TYPE789',
            last_updated_start_date='2024-01-01',
            last_updated_end_date='2024-12-31',
            page=3,
            page_size=25,
            total_pages=True,
            fields='id,attributes',
            filter_param='value'
        )
        
        call_args = self.mock_client.get.call_args
        params = call_args[1]['params']
        
        assert params['orgUnit'] == 'ORG123'
        assert params['ouMode'] == 'CHILDREN'
        assert params['program'] == 'PROG456'
        assert params['trackedEntityType'] == 'TYPE789'
        assert params['lastUpdatedStartDate'] == '2024-01-01'
        assert params['lastUpdatedEndDate'] == '2024-12-31'
        assert params['page'] == 3
        assert params['pageSize'] == 25
        assert params['totalPages'] == 'true'
        assert params['fields'] == 'id,attributes'
        assert params['filter_param'] == 'value'
    
    async def test_tracked_entities_to_pandas(self):
        """Test tracked entities to pandas conversion"""
        mock_entities = [
            {'trackedEntity': 'te1', 'trackedEntityType': 'person'},
            {'trackedEntity': 'te2', 'trackedEntityType': 'person'}
        ]
        
        mock_response = {
            'instances': mock_entities,
            'page': {'pageCount': 1}
        }
        
        self.mock_client.get.return_value = mock_response
        
        # Mock converter
        expected_df = pd.DataFrame([{'entity_id': 'te1'}, {'entity_id': 'te2'}])
        with patch.object(self.endpoint.converter, 'tracked_entities_to_dataframe', return_value=expected_df) as mock_convert:
            result = await self.endpoint.tracked_entities_to_pandas(org_unit='ORG123')
        
        mock_convert.assert_called_once_with(mock_entities)
        assert result.equals(expected_df)
    
    async def test_stream_events(self):
        """Test streaming events"""
        # Mock responses for 2 pages
        page1_response = {
            'instances': [{'event': 'event1'}],
            'page': {'pageCount': 2}
        }
        page2_response = {
            'instances': [{'event': 'event2'}],
            'page': {'pageCount': 2}
        }
        
        self.mock_client.get.side_effect = [page1_response, page2_response]
        
        # Mock converter
        df1 = pd.DataFrame([{'event_id': 'event1'}])
        df2 = pd.DataFrame([{'event_id': 'event2'}])
        
        with patch.object(self.endpoint.converter, 'events_to_dataframe', side_effect=[df1, df2]):
            results = []
            async for df in self.endpoint.stream_events(program='PROG123'):
                results.append(df)
        
        assert len(results) == 2
        assert results[0].equals(df1)
        assert results[1].equals(df2)
        assert self.mock_client.get.call_count == 2
    
    async def test_stream_events_empty_page(self):
        """Test streaming events with empty page"""
        empty_response = {'instances': []}
        self.mock_client.get.return_value = empty_response
        
        results = []
        async for df in self.endpoint.stream_events():
            results.append(df)
        
        assert len(results) == 0
        assert self.mock_client.get.call_count == 1
    
    async def test_stream_events_max_pages(self):
        """Test streaming events with max pages limit"""
        mock_response = {
            'instances': [{'event': 'event1'}],
            'page': {'pageCount': 10}  # Many pages available
        }
        
        self.mock_client.get.return_value = mock_response
        
        df = pd.DataFrame([{'event_id': 'event1'}])
        with patch.object(self.endpoint.converter, 'events_to_dataframe', return_value=df):
            results = []
            async for result_df in self.endpoint.stream_events(max_pages=2):
                results.append(result_df)
        
        assert len(results) == 2
        assert self.mock_client.get.call_count == 2
    
    async def test_get_event(self):
        """Test get single event"""
        event_id = 'EVENT123'
        expected_response = {'event': event_id, 'program': 'PROG1'}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.get_event(event_id)
        
        self.mock_client.get.assert_called_once_with(f'/api/tracker/events/{event_id}')
        assert result == expected_response
    
    async def test_get_tracked_entity(self):
        """Test get single tracked entity"""
        entity_id = 'TE123'
        expected_response = {'trackedEntity': entity_id, 'trackedEntityType': 'person'}
        self.mock_client.get.return_value = expected_response
        
        result = await self.endpoint.get_tracked_entity(entity_id)
        
        self.mock_client.get.assert_called_once_with(f'/api/tracker/trackedEntities/{entity_id}')
        assert result == expected_response
    
    async def test_create_event(self):
        """Test create event"""
        event_data = {
            'program': 'PROG123',
            'programStage': 'STAGE456',
            'orgUnit': 'ORG789',
            'dataValues': [{'dataElement': 'DE1', 'value': '100'}]
        }
        
        expected_response = {
            'status': 'SUCCESS',
            'stats': {'created': 1}
        }
        self.mock_client.post.return_value = expected_response
        
        result = await self.endpoint.create_event(event_data)
        
        self.mock_client.post.assert_called_once_with(
            '/api/tracker',
            data={'events': [event_data]}
        )
        assert result == expected_response
    
    async def test_update_event(self):
        """Test update event"""
        event_id = 'EVENT123'
        event_data = {
            'event': event_id,
            'dataValues': [{'dataElement': 'DE1', 'value': '200'}]
        }
        
        expected_response = {
            'status': 'SUCCESS',
            'stats': {'updated': 1}
        }
        self.mock_client.put.return_value = expected_response
        
        result = await self.endpoint.update_event(event_id, event_data)
        
        self.mock_client.put.assert_called_once_with(
            f'/api/tracker/events/{event_id}',
            data=event_data
        )
        assert result == expected_response
    
    async def test_delete_event(self):
        """Test delete event"""
        event_id = 'EVENT123'
        expected_response = {
            'status': 'SUCCESS',
            'stats': {'deleted': 1}
        }
        self.mock_client.delete.return_value = expected_response
        
        result = await self.endpoint.delete_event(event_id)
        
        self.mock_client.delete.assert_called_once_with(f'/api/tracker/events/{event_id}')
        assert result == expected_response
    
    async def test_export_events_to_file_parquet(self):
        """Test export events to parquet file"""
        mock_df = pd.DataFrame([{'event': 'event1', 'value': 100}])
        
        with patch.object(self.endpoint, 'events_to_pandas', return_value=mock_df) as mock_events, \
             patch.object(mock_df, 'to_parquet') as mock_to_parquet:
            
            file_path = str(Path(self.temp_dir) / "events.parquet")
            result = await self.endpoint.export_events_to_file(
                file_path,
                format=ExportFormat.PARQUET,
                program='PROG123'
            )
        
        mock_events.assert_called_once_with(program='PROG123')
        mock_to_parquet.assert_called_once_with(file_path)
        assert result == file_path
    
    async def test_export_events_to_file_csv(self):
        """Test export events to CSV file"""
        mock_df = pd.DataFrame([{'event': 'event1', 'value': 100}])
        
        with patch.object(self.endpoint, 'events_to_pandas', return_value=mock_df), \
             patch.object(mock_df, 'to_csv') as mock_to_csv:
            
            file_path = str(Path(self.temp_dir) / "events.csv")
            result = await self.endpoint.export_events_to_file(
                file_path,
                format=ExportFormat.CSV
            )
        
        mock_to_csv.assert_called_once_with(file_path, index=False)
        assert result == file_path
    
    async def test_export_events_to_file_excel(self):
        """Test export events to Excel file"""
        mock_df = pd.DataFrame([{'event': 'event1'}])
        
        with patch.object(self.endpoint, 'events_to_pandas', return_value=mock_df), \
             patch.object(mock_df, 'to_excel') as mock_to_excel:
            
            file_path = str(Path(self.temp_dir) / "events.xlsx")
            await self.endpoint.export_events_to_file(file_path, format=ExportFormat.EXCEL)
        
        mock_to_excel.assert_called_once_with(file_path, index=False)
    
    async def test_export_events_to_file_feather(self):
        """Test export events to Feather file"""
        mock_df = pd.DataFrame([{'event': 'event1'}])
        
        with patch.object(self.endpoint, 'events_to_pandas', return_value=mock_df), \
             patch.object(mock_df, 'to_feather') as mock_to_feather:
            
            file_path = str(Path(self.temp_dir) / "events.feather")
            await self.endpoint.export_events_to_file(file_path, format=ExportFormat.FEATHER)
        
        mock_to_feather.assert_called_once_with(file_path)
    
    async def test_export_events_to_file_json(self):
        """Test export events to JSON file"""
        mock_df = pd.DataFrame([{'event': 'event1'}])
        
        with patch.object(self.endpoint, 'events_to_pandas', return_value=mock_df), \
             patch.object(mock_df, 'to_json') as mock_to_json:
            
            file_path = str(Path(self.temp_dir) / "events.json")
            await self.endpoint.export_events_to_file(file_path, format=ExportFormat.JSON)
        
        mock_to_json.assert_called_once_with(file_path, orient='records')
    
    async def test_export_events_unsupported_format(self):
        """Test export events with unsupported format"""
        mock_df = pd.DataFrame([{'event': 'event1'}])
        
        with patch.object(self.endpoint, 'events_to_pandas', return_value=mock_df):
            with pytest.raises(ValueError, match="Unsupported export format"):
                await self.endpoint.export_events_to_file(
                    "events.unknown",
                    format="UNKNOWN_FORMAT"
                )
    
    async def test_export_tracked_entities_to_file_parquet(self):
        """Test export tracked entities to parquet file"""
        mock_df = pd.DataFrame([{'entity': 'te1', 'type': 'person'}])
        
        with patch.object(self.endpoint, 'tracked_entities_to_pandas', return_value=mock_df) as mock_entities, \
             patch.object(mock_df, 'to_parquet') as mock_to_parquet:
            
            file_path = str(Path(self.temp_dir) / "entities.parquet")
            result = await self.endpoint.export_tracked_entities_to_file(
                file_path,
                format=ExportFormat.PARQUET,
                program='PROG123'
            )
        
        mock_entities.assert_called_once_with(program='PROG123')
        mock_to_parquet.assert_called_once_with(file_path)
        assert result == file_path
    
    async def test_export_tracked_entities_to_file_csv(self):
        """Test export tracked entities to CSV file"""
        mock_df = pd.DataFrame([{'entity': 'te1'}])
        
        with patch.object(self.endpoint, 'tracked_entities_to_pandas', return_value=mock_df), \
             patch.object(mock_df, 'to_csv') as mock_to_csv:
            
            file_path = str(Path(self.temp_dir) / "entities.csv")
            await self.endpoint.export_tracked_entities_to_file(file_path, format=ExportFormat.CSV)
        
        mock_to_csv.assert_called_once_with(file_path, index=False)
    
    async def test_export_tracked_entities_unsupported_format(self):
        """Test export tracked entities with unsupported format"""
        mock_df = pd.DataFrame([{'entity': 'te1'}])
        
        with patch.object(self.endpoint, 'tracked_entities_to_pandas', return_value=mock_df):
            with pytest.raises(ValueError, match="Unsupported export format"):
                await self.endpoint.export_tracked_entities_to_file(
                    "entities.unknown",
                    format="UNKNOWN_FORMAT"
                )


class TestTrackerIntegration:
    """Tests for tracker endpoint integration scenarios"""
    
    def setup_method(self):
        """Setup integration tests"""
        self.mock_client = AsyncMock()
        self.endpoint = TrackerEndpoint(self.mock_client)
    
    async def test_full_event_workflow(self):
        """Test complete event workflow"""
        # Mock event creation
        create_response = {
            'status': 'SUCCESS',
            'stats': {'created': 1},
            'bundleReport': {
                'typeReportMap': {
                    'EVENT': {
                        'objectReports': [
                            {'uid': 'EVENT123', 'index': 0}
                        ]
                    }
                }
            }
        }
        
        # Mock event retrieval
        get_response = {
            'event': 'EVENT123',
            'program': 'PROG1',
            'dataValues': [{'dataElement': 'DE1', 'value': '100'}]
        }
        
        # Mock event update
        update_response = {
            'status': 'SUCCESS',
            'stats': {'updated': 1}
        }
        
        self.mock_client.post.return_value = create_response
        self.mock_client.get.return_value = get_response
        self.mock_client.put.return_value = update_response
        
        # Create event
        event_data = {
            'program': 'PROG1',
            'orgUnit': 'ORG1',
            'dataValues': [{'dataElement': 'DE1', 'value': '100'}]
        }
        
        create_result = await self.endpoint.create_event(event_data)
        assert create_result['status'] == 'SUCCESS'
        
        # Get event
        get_result = await self.endpoint.get_event('EVENT123')
        assert get_result['event'] == 'EVENT123'
        
        # Update event
        updated_data = event_data.copy()
        updated_data['dataValues'] = [{'dataElement': 'DE1', 'value': '200'}]
        
        update_result = await self.endpoint.update_event('EVENT123', updated_data)
        assert update_result['status'] == 'SUCCESS'
    
    async def test_pagination_handling(self):
        """Test pagination handling across different methods"""
        # Mock multiple pages with decreasing data
        responses = [
            {'instances': [{'event': f'event{i}'}], 'page': {'pageCount': 3}}
            for i in range(1, 4)
        ]
        
        self.mock_client.get.side_effect = responses
        
        # Mock converter to return appropriate DataFrames
        
        with patch.object(self.endpoint.converter, 'events_to_dataframe', return_value=pd.DataFrame([{'event_id': 'combined'}])):
            result = await self.endpoint.events_to_pandas()
        
        # Should have fetched all 3 pages
        assert self.mock_client.get.call_count == 3
        assert isinstance(result, pd.DataFrame)
    
    async def test_since_parameter_handling(self):
        """Test 'since' parameter handling"""
        mock_response = {'instances': [], 'page': {'pageCount': 1}}
        self.mock_client.get.return_value = mock_response
        
        since_date = '2024-01-01T00:00:00'
        
        with patch.object(self.endpoint.converter, 'events_to_dataframe', return_value=pd.DataFrame()):
            await self.endpoint.events_to_pandas(since=since_date)
        
        call_args = self.mock_client.get.call_args
        params = call_args[1]['params']
        assert params['lastUpdatedStartDate'] == since_date
    
    async def test_error_handling_in_pagination(self):
        """Test error handling during pagination"""
        # First page succeeds, second page fails
        self.mock_client.get.side_effect = [
            {'instances': [{'event': 'event1'}], 'page': {'pageCount': 2}},
            Exception("Network error")
        ]
        
        with pytest.raises(Exception, match="Network error"):
            with patch.object(self.endpoint.converter, 'events_to_dataframe', return_value=pd.DataFrame()):
                await self.endpoint.events_to_pandas()
