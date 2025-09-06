"""Analytics endpoint - Analysis data queries and DataFrame conversion"""

from typing import Any, Dict, List, Optional, Union, AsyncIterator
import asyncio
from urllib.parse import urlencode

import pandas as pd
import pyarrow as pa

from pydhis2.core.types import AnalyticsQuery, DataFrameFormat, ExportFormat
from pydhis2.io.to_pandas import AnalyticsDataFrameConverter
from pydhis2.io.arrow import ArrowConverter


class AnalyticsEndpoint:
    """Analytics API endpoint"""
    
    def __init__(self, client):
        self.client = client
        self.converter = AnalyticsDataFrameConverter()
        self.arrow_converter = ArrowConverter()
    
    async def raw(
        self,
        query: AnalyticsQuery,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """Get raw JSON data"""
        params = query.to_params()
        if output_format != "json":
            params['format'] = output_format
        
        return await self.client.get('/api/analytics', params=params)
    
    async def to_pandas(
        self,
        query: AnalyticsQuery,
        long_format: bool = True
    ) -> pd.DataFrame:
        """Convert to Pandas DataFrame"""
        data = await self.raw(query)
        return self.converter.to_dataframe(data, long_format=long_format)
    
    async def to_arrow(
        self,
        query: AnalyticsQuery,
        long_format: bool = True
    ) -> pa.Table:
        """Convert to Arrow Table"""
        df = await self.to_pandas(query, long_format=long_format)
        return self.arrow_converter.from_pandas(df)
    
    async def stream_paginated(
        self,
        query: AnalyticsQuery,
        page_size: int = 1000,
        max_pages: Optional[int] = None
    ) -> AsyncIterator[pd.DataFrame]:
        """Stream paginated data"""
        page = 1
        
        while True:
            # Modify query parameters to add paging
            page_params = query.to_params()
            page_params.update({
                'page': page,
                'pageSize': page_size,
                'paging': 'true'
            })
            
            response = await self.client.get('/api/analytics', params=page_params)
            
            # Convert to DataFrame
            df = self.converter.to_dataframe(response, long_format=True)
            if not df.empty:
                yield df
            
            # Check pagination information
            pager = response.get('pager', {})
            total_pages = pager.get('pageCount', 1)
            
            if page >= total_pages:
                break
            
            if max_pages and page >= max_pages:
                break
            
            page += 1
    
    async def export_to_file(
        self,
        query: AnalyticsQuery,
        file_path: str,
        format: ExportFormat = ExportFormat.PARQUET,
        **kwargs
    ) -> str:
        """Export to file"""
        df = await self.to_pandas(query)
        
        if format == ExportFormat.PARQUET:
            df.to_parquet(file_path, **kwargs)
        elif format == ExportFormat.CSV:
            df.to_csv(file_path, **kwargs)
        elif format == ExportFormat.EXCEL:
            df.to_excel(file_path, **kwargs)
        elif format == ExportFormat.FEATHER:
            df.to_feather(file_path, **kwargs)
        elif format == ExportFormat.JSON:
            df.to_json(file_path, **kwargs)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        return file_path
    
    async def get_dimensions(self) -> Dict[str, Any]:
        """Get available dimensions"""
        return await self.client.get('/api/analytics/dimensions')
    
    async def get_dimension_items(self, dimension: str) -> Dict[str, Any]:
        """Get items for a specific dimension"""
        return await self.client.get(f'/api/analytics/dimensions/{dimension}')
    
    async def validate_query(self, query: AnalyticsQuery) -> Dict[str, Any]:
        """Validate query (dry run)"""
        params = query.to_params()
        params['dryRun'] = 'true'
        return await self.client.get('/api/analytics', params=params)
