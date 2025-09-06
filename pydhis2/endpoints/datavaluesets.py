"""DataValueSets endpoint - Data value set reading and import"""

from typing import Any, Dict, List, Optional, Union, AsyncIterator
import asyncio
import json
from datetime import datetime
import math

import pandas as pd
import pyarrow as pa

from pydhis2.core.types import ImportConfig, ImportStrategy, ExportFormat
from pydhis2.core.errors import ImportConflictError
from pydhis2.io.to_pandas import DataValueSetsConverter
from pydhis2.io.arrow import ArrowConverter


class ImportSummary:
    """Import summary result"""
    
    def __init__(self, summary_data: Dict[str, Any]):
        self.raw_data = summary_data
        self.status = summary_data.get('status', 'UNKNOWN')
        self.imported = summary_data.get('imported', 0)
        self.updated = summary_data.get('updated', 0)
        self.deleted = summary_data.get('deleted', 0)
        self.ignored = summary_data.get('ignored', 0)
        self.total = summary_data.get('total', 0)
        
        # Conflict information
        self.conflicts = summary_data.get('conflicts', [])
        self.has_conflicts = len(self.conflicts) > 0
    
    @property
    def success_rate(self) -> float:
        """Success rate"""
        if self.total == 0:
            return 0.0
        return (self.imported + self.updated) / self.total
    
    @property
    def conflicts_df(self) -> pd.DataFrame:
        """Conflicts DataFrame"""
        if not self.conflicts:
            return pd.DataFrame()
        
        conflicts_data = []
        for conflict in self.conflicts:
            conflicts_data.append({
                'uid': conflict.get('object', ''),
                'path': conflict.get('property', ''),
                'value': conflict.get('value', ''),
                'conflict_msg': conflict.get('message', ''),
                'status': 'ERROR'
            })
        
        return pd.DataFrame(conflicts_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'status': self.status,
            'imported': self.imported,
            'updated': self.updated,
            'deleted': self.deleted,
            'ignored': self.ignored,
            'total': self.total,
            'success_rate': self.success_rate,
            'has_conflicts': self.has_conflicts,
            'conflicts_count': len(self.conflicts),
        }


class DataValueSetsEndpoint:
    """DataValueSets API endpoint"""
    
    def __init__(self, client):
        self.client = client
        self.converter = DataValueSetsConverter()
        self.arrow_converter = ArrowConverter()
    
    async def pull(
        self,
        data_set: Optional[str] = None,
        org_unit: Optional[str] = None,
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        children: bool = False,
        last_updated: Optional[str] = None,
        completed_only: bool = False,
        include_deleted: bool = False,
        **kwargs
    ) -> pd.DataFrame:
        """Pull data value sets"""
        params = {}
        
        if data_set:
            params['dataSet'] = data_set
        if org_unit:
            params['orgUnit'] = org_unit
        if period:
            params['period'] = period
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        if children:
            params['children'] = 'true'
        if last_updated:
            params['lastUpdated'] = last_updated
        if completed_only:
            params['completedOnly'] = 'true'
        if include_deleted:
            params['includeDeleted'] = 'true'
        
        # Add other parameters
        params.update(kwargs)
        
        response = await self.client.get('/api/dataValueSets', params=params)
        return self.converter.to_dataframe(response)
    
    async def pull_paginated(
        self,
        page_size: int = 5000,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[pd.DataFrame]:
        """Pull paginated data value sets"""
        page = 1
        
        while True:
            page_kwargs = kwargs.copy()
            page_kwargs.update({
                'page': page,
                'pageSize': page_size,
                'paging': 'true'
            })
            
            try:
                response = await self.client.get('/api/dataValueSets', params=page_kwargs)
                df = self.converter.to_dataframe(response)
                
                if not df.empty:
                    yield df
                
                # Check pagination information
                pager = response.get('pager', {})
                total_pages = pager.get('pageCount', 1)
                
                if page >= total_pages:
                    break
                
                if max_pages and page >= max_pages:
                    break
                
            except Exception as e:
                # Some DHIS2 versions may not support paging
                if page == 1:
                    # Fallback to non-paginated mode
                    df = await self.pull(**kwargs)
                    if not df.empty:
                        yield df
                break
            
            page += 1
    
    async def push(
        self,
        data: Union[pd.DataFrame, Dict[str, Any], str],
        config: Optional[ImportConfig] = None,
        chunk_size: int = 5000,
        resume_from_chunk: int = 0
    ) -> ImportSummary:
        """Push (import) data value sets"""
        if config is None:
            config = ImportConfig()
        
        # Preprocess data
        if isinstance(data, pd.DataFrame):
            data_dict = self.converter.from_dataframe(data)
        elif isinstance(data, str):
            data_dict = json.loads(data)
        else:
            data_dict = data
        
        # If data is large, process in chunks
        data_values = data_dict.get('dataValues', [])
        if len(data_values) <= chunk_size:
            return await self._push_single(data_dict, config)
        else:
            return await self._push_chunked(data_dict, config, chunk_size, resume_from_chunk)
    
    async def _push_single(
        self,
        data_dict: Dict[str, Any],
        config: ImportConfig
    ) -> ImportSummary:
        """Single push"""
        params = {
            'strategy': config.strategy.value,
            'dryRun': str(config.dry_run).lower(),
            'atomic': str(config.atomic).lower(),
            'skipAudit': str(config.skip_audit).lower(),
            'skipExistingCheck': str(config.skip_existing_check).lower(),
            'force': str(config.force).lower(),
        }
        
        if config.async_import:
            params['async'] = 'true'
        
        response = await self.client.post(
            '/api/dataValueSets',
            data=data_dict,
            params=params
        )
        
        summary = ImportSummary(response)
        
        # Check for conflicts
        if summary.has_conflicts and not config.dry_run:
            raise ImportConflictError(
                conflicts=summary.conflicts,
                import_summary=summary.raw_data
            )
        
        return summary
    
    async def _push_chunked(
        self,
        data_dict: Dict[str, Any],
        config: ImportConfig,
        chunk_size: int,
        resume_from_chunk: int = 0
    ) -> ImportSummary:
        """Chunked push"""
        data_values = data_dict.get('dataValues', [])
        total_chunks = math.ceil(len(data_values) / chunk_size)
        
        # Accumulate results
        total_imported = 0
        total_updated = 0
        total_ignored = 0
        total_conflicts = []
        
        for chunk_idx in range(resume_from_chunk, total_chunks):
            start_idx = chunk_idx * chunk_size
            end_idx = min(start_idx + chunk_size, len(data_values))
            
            chunk_data = data_dict.copy()
            chunk_data['dataValues'] = data_values[start_idx:end_idx]
            
            try:
                chunk_summary = await self._push_single(chunk_data, config)
                
                total_imported += chunk_summary.imported
                total_updated += chunk_summary.updated
                total_ignored += chunk_summary.ignored
                total_conflicts.extend(chunk_summary.conflicts)
                
                print(f"Chunk {chunk_idx + 1}/{total_chunks} completed: "
                      f"imported={chunk_summary.imported}, "
                      f"updated={chunk_summary.updated}, "
                      f"conflicts={len(chunk_summary.conflicts)}")
                
            except ImportConflictError as e:
                # Record conflicts but continue processing
                total_conflicts.extend(e.conflicts)
                print(f"Chunk {chunk_idx + 1}/{total_chunks} has conflicts: {len(e.conflicts)}")
                
                if config.atomic:
                    # Stop on conflict in atomic mode
                    raise
        
        # Construct overall summary
        total_summary_data = {
            'status': 'SUCCESS' if not total_conflicts else 'WARNING',
            'imported': total_imported,
            'updated': total_updated,
            'ignored': total_ignored,
            'total': len(data_values),
            'conflicts': total_conflicts,
        }
        
        summary = ImportSummary(total_summary_data)
        
        if summary.has_conflicts and not config.dry_run:
            raise ImportConflictError(
                conflicts=summary.conflicts,
                import_summary=summary.raw_data
            )
        
        return summary
    
    async def get_import_status(self, task_id: str) -> Dict[str, Any]:
        """Get async import status"""
        return await self.client.get(f'/api/system/tasks/dataValueImport/{task_id}')
    
    async def export_to_file(
        self,
        file_path: str,
        format: ExportFormat = ExportFormat.PARQUET,
        **pull_kwargs
    ) -> str:
        """Export to file"""
        df = await self.pull(**pull_kwargs)
        
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
