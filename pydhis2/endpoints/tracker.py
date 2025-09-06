"""Tracker endpoint - Event and entity queries and management"""

from typing import Any, Dict, List, Optional, Union, AsyncIterator
import asyncio
from datetime import datetime

import pandas as pd
import pyarrow as pa

from pydhis2.core.types import ExportFormat
from pydhis2.io.to_pandas import TrackerConverter
from pydhis2.io.arrow import ArrowConverter


class TrackerEndpoint:
    """Tracker API endpoint"""
    
    def __init__(self, client):
        self.client = client
        self.converter = TrackerConverter()
        self.arrow_converter = ArrowConverter()
    
    async def events(
        self,
        program: Optional[str] = None,
        org_unit: Optional[str] = None,
        org_unit_mode: str = "SELECTED",
        status: Optional[str] = None,
        program_stage: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        last_updated_start_date: Optional[str] = None,
        last_updated_end_date: Optional[str] = None,
        skip_meta: bool = False,
        page: int = 1,
        page_size: int = 50,
        total_pages: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Get event data (raw JSON)"""
        params = {
            'page': page,
            'pageSize': page_size,
            'totalPages': str(total_pages).lower(),
            'skipMeta': str(skip_meta).lower(),
            'ouMode': org_unit_mode,
        }
        
        if program:
            params['program'] = program
        if org_unit:
            params['orgUnit'] = org_unit  
        if status:
            params['status'] = status
        if program_stage:
            params['programStage'] = program_stage
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        if last_updated_start_date:
            params['lastUpdatedStartDate'] = last_updated_start_date
        if last_updated_end_date:
            params['lastUpdatedEndDate'] = last_updated_end_date
        
        # Add other parameters
        params.update(kwargs)
        
        return await self.client.get('/api/tracker/events', params=params)
    
    async def events_to_pandas(
        self,
        program: Optional[str] = None,
        org_unit: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[str] = None,
        paging_size: int = 200,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> pd.DataFrame:
        """Get event data and convert to DataFrame"""
        all_events = []
        page = 1
        
        while True:
            # Set date parameters
            if since:
                kwargs['lastUpdatedStartDate'] = since
            
            response = await self.events(
                program=program,
                org_unit=org_unit,
                status=status,
                page=page,
                page_size=paging_size,
                total_pages=True,
                **kwargs
            )
            
            events = response.get('instances', [])
            if not events:
                break
            
            all_events.extend(events)
            
            # Check pagination
            pager = response.get('page', {})
            total_pages = pager.get('pageCount', 1)
            
            if page >= total_pages:
                break
            
            if max_pages and page >= max_pages:
                break
            
            page += 1
        
        return self.converter.events_to_dataframe(all_events)
    
    async def tracked_entities(
        self,
        org_unit: Optional[str] = None,
        org_unit_mode: str = "SELECTED",
        program: Optional[str] = None,
        tracked_entity_type: Optional[str] = None,
        last_updated_start_date: Optional[str] = None,
        last_updated_end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        total_pages: bool = False,
        fields: str = "*",
        **kwargs
    ) -> Dict[str, Any]:
        """Get tracked entity data (raw JSON)"""
        params = {
            'page': page,
            'pageSize': page_size,
            'totalPages': str(total_pages).lower(),
            'ouMode': org_unit_mode,
            'fields': fields,
        }
        
        if org_unit:
            params['orgUnit'] = org_unit
        if program:
            params['program'] = program
        if tracked_entity_type:
            params['trackedEntityType'] = tracked_entity_type
        if last_updated_start_date:
            params['lastUpdatedStartDate'] = last_updated_start_date
        if last_updated_end_date:
            params['lastUpdatedEndDate'] = last_updated_end_date
        
        params.update(kwargs)
        
        return await self.client.get('/api/tracker/trackedEntities', params=params)
    
    async def tracked_entities_to_pandas(
        self,
        org_unit: Optional[str] = None,
        program: Optional[str] = None,
        since: Optional[str] = None,
        paging_size: int = 200,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> pd.DataFrame:
        """Get tracked entity data and convert to DataFrame"""
        all_entities = []
        page = 1
        
        while True:
            if since:
                kwargs['lastUpdatedStartDate'] = since
            
            response = await self.tracked_entities(
                org_unit=org_unit,
                program=program,
                page=page,
                page_size=paging_size,
                total_pages=True,
                **kwargs
            )
            
            entities = response.get('instances', [])
            if not entities:
                break
            
            all_entities.extend(entities)
            
            # Check pagination
            pager = response.get('page', {})
            total_pages = pager.get('pageCount', 1)
            
            if page >= total_pages:
                break
            
            if max_pages and page >= max_pages:
                break
            
            page += 1
        
        return self.converter.tracked_entities_to_dataframe(all_entities)
    
    async def stream_events(
        self,
        program: Optional[str] = None,
        org_unit: Optional[str] = None,
        page_size: int = 200,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[pd.DataFrame]:
        """Stream event data"""
        page = 1
        
        while True:
            response = await self.events(
                program=program,
                org_unit=org_unit,
                page=page,
                page_size=page_size,
                total_pages=True,
                **kwargs
            )
            
            events = response.get('instances', [])
            if not events:
                break
            
            df = self.converter.events_to_dataframe(events)
            if not df.empty:
                yield df
            
            # Check pagination
            pager = response.get('page', {})
            total_pages = pager.get('pageCount', 1)
            
            if page >= total_pages:
                break
            
            if max_pages and page >= max_pages:
                break
            
            page += 1
    
    async def get_event(self, event_id: str) -> Dict[str, Any]:
        """Get a single event"""
        return await self.client.get(f'/api/tracker/events/{event_id}')
    
    async def get_tracked_entity(self, entity_id: str) -> Dict[str, Any]:
        """Get a single tracked entity"""
        return await self.client.get(f'/api/tracker/trackedEntities/{entity_id}')
    
    async def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an event"""
        payload = {'events': [event_data]}
        return await self.client.post('/api/tracker', data=payload)
    
    async def update_event(self, event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an event"""
        return await self.client.put(f'/api/tracker/events/{event_id}', data=event_data)
    
    async def delete_event(self, event_id: str) -> Dict[str, Any]:
        """Delete an event"""
        return await self.client.delete(f'/api/tracker/events/{event_id}')
    
    async def export_events_to_file(
        self,
        file_path: str,
        format: ExportFormat = ExportFormat.PARQUET,
        **query_kwargs
    ) -> str:
        """Export events to file"""
        df = await self.events_to_pandas(**query_kwargs)
        
        if format == ExportFormat.PARQUET:
            df.to_parquet(file_path)
        elif format == ExportFormat.CSV:
            df.to_csv(file_path, index=False)
        elif format == ExportFormat.EXCEL:
            df.to_excel(file_path, index=False)
        elif format == ExportFormat.FEATHER:
            df.to_feather(file_path)
        elif format == ExportFormat.JSON:
            df.to_json(file_path, orient='records')
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        return file_path
    
    async def export_tracked_entities_to_file(
        self,
        file_path: str,
        format: ExportFormat = ExportFormat.PARQUET,
        **query_kwargs
    ) -> str:
        """Export tracked entities to file"""
        df = await self.tracked_entities_to_pandas(**query_kwargs)
        
        if format == ExportFormat.PARQUET:
            df.to_parquet(file_path)
        elif format == ExportFormat.CSV:
            df.to_csv(file_path, index=False)
        elif format == ExportFormat.EXCEL:
            df.to_excel(file_path, index=False)
        elif format == ExportFormat.FEATHER:
            df.to_feather(file_path)
        elif format == ExportFormat.JSON:
            df.to_json(file_path, orient='records')
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        return file_path
