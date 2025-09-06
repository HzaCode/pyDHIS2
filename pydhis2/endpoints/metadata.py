"""Metadata endpoint - Metadata import, export, and management"""

from typing import Any, Dict, List, Optional, Union
import json

import pandas as pd

from pydhis2.core.types import ImportConfig, ExportFormat
from pydhis2.core.errors import ImportConflictError, MetadataError


class MetadataImportSummary:
    """Metadata import summary"""
    
    def __init__(self, summary_data: Dict[str, Any]):
        self.raw_data = summary_data
        self.status = summary_data.get('status', 'UNKNOWN')
        self.stats = summary_data.get('stats', {})
        self.type_reports = summary_data.get('typeReports', [])
        
        # Calculate overall statistics
        self.total = 0
        self.imported = 0
        self.updated = 0
        self.deleted = 0
        self.ignored = 0
        
        for type_report in self.type_reports:
            object_reports = type_report.get('objectReports', [])
            for report in object_reports:
                self.total += 1
                if report.get('index') is not None:
                    if 'created' in str(report).lower():
                        self.imported += 1
                    elif 'updated' in str(report).lower():
                        self.updated += 1
                    elif 'deleted' in str(report).lower():
                        self.deleted += 1
                    else:
                        self.ignored += 1
    
    @property
    def success_rate(self) -> float:
        """Success rate"""
        if self.total == 0:
            return 0.0
        return (self.imported + self.updated) / self.total
    
    @property
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return self.status in ['ERROR', 'WARNING']
    
    def get_conflicts_df(self) -> pd.DataFrame:
        """Get conflicts as a DataFrame"""
        conflicts = []
        
        for type_report in self.type_reports:
            object_type = type_report.get('klass', 'Unknown')
            object_reports = type_report.get('objectReports', [])
            
            for report in object_reports:
                error_reports = report.get('errorReports', [])
                for error in error_reports:
                    conflicts.append({
                        'object_type': object_type,
                        'uid': report.get('uid', ''),
                        'index': report.get('index', ''),
                        'error_code': error.get('errorCode', ''),
                        'message': error.get('message', ''),
                        'property': error.get('property', ''),
                        'value': error.get('value', ''),
                    })
        
        return pd.DataFrame(conflicts)


class MetadataEndpoint:
    """Metadata API endpoint"""
    
    def __init__(self, client):
        self.client = client
    
    async def export(
        self,
        filter: Optional[Dict[str, str]] = None,
        fields: str = ":owner",
        defaults: str = "INCLUDE",
        download: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Export metadata"""
        params = {
            'fields': fields,
            'defaults': defaults,
            'download': str(download).lower(),
        }
        
        # Add filters
        if filter:
            for key, value in filter.items():
                params[f'{key}:filter'] = value
        
        # Add other parameters
        params.update(kwargs)
        
        return await self.client.get('/api/metadata', params=params)
    
    async def import_(
        self,
        metadata: Union[Dict[str, Any], str],
        atomic: bool = True,
        dry_run: bool = False,
        strategy: str = "CREATE_AND_UPDATE",
        merge_mode: str = "REPLACE",
        flush_mode: str = "AUTO",
        skip_sharing: bool = False,
        skip_validation: bool = False,
        **kwargs
    ) -> MetadataImportSummary:
        """Import metadata"""
        params = {
            'atomic': str(atomic).lower(),
            'dryRun': str(dry_run).lower(),
            'importStrategy': strategy,
            'mergeMode': merge_mode,
            'flushMode': flush_mode,
            'skipSharing': str(skip_sharing).lower(),
            'skipValidation': str(skip_validation).lower(),
        }
        
        # Add other parameters
        params.update(kwargs)
        
        # Prepare data
        if isinstance(metadata, str):
            metadata_dict = json.loads(metadata)
        else:
            metadata_dict = metadata
        
        response = await self.client.post(
            '/api/metadata',
            data=metadata_dict,
            params=params
        )
        
        summary = MetadataImportSummary(response)
        
        # Check for errors
        if summary.has_errors and not dry_run:
            conflicts_df = summary.get_conflicts_df()
            if not conflicts_df.empty:
                conflicts = conflicts_df.to_dict('records')
                raise ImportConflictError(
                    conflicts=conflicts,
                    import_summary=summary.raw_data
                )
        
        return summary
    
    async def get_schemas(self) -> Dict[str, Any]:
        """Get all schemas"""
        return await self.client.get('/api/schemas')
    
    async def get_schema(self, schema_name: str) -> Dict[str, Any]:
        """Get a specific schema"""
        return await self.client.get(f'/api/schemas/{schema_name}')
    
    async def get_data_elements(
        self,
        fields: str = "id,name,code,valueType",
        filter: Optional[Dict[str, str]] = None,
        paging: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Get data elements"""
        params = {
            'fields': fields,
            'paging': str(paging).lower(),
        }
        
        if filter:
            for key, value in filter.items():
                params[f'filter'] = f'{key}:eq:{value}'
        
        params.update(kwargs)
        
        return await self.client.get('/api/dataElements', params=params)
    
    async def get_indicators(
        self,
        fields: str = "id,name,code,numerator,denominator",
        filter: Optional[Dict[str, str]] = None,
        paging: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Get indicators"""
        params = {
            'fields': fields,
            'paging': str(paging).lower(),
        }
        
        if filter:
            for key, value in filter.items():
                params[f'filter'] = f'{key}:eq:{value}'
        
        params.update(kwargs)
        
        return await self.client.get('/api/indicators', params=params)
    
    async def get_organisation_units(
        self,
        fields: str = "id,name,code,level,path",
        filter: Optional[Dict[str, str]] = None,
        paging: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Get organisation units"""
        params = {
            'fields': fields,
            'paging': str(paging).lower(),
        }
        
        if filter:
            for key, value in filter.items():
                params[f'filter'] = f'{key}:eq:{value}'
        
        params.update(kwargs)
        
        return await self.client.get('/api/organisationUnits', params=params)
    
    async def get_option_sets(
        self,
        fields: str = "id,name,code,options[id,name,code]",
        filter: Optional[Dict[str, str]] = None,
        paging: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Get option sets"""
        params = {
            'fields': fields,
            'paging': str(paging).lower(),
        }
        
        if filter:
            for key, value in filter.items():
                params[f'filter'] = f'{key}:eq:{value}'
        
        params.update(kwargs)
        
        return await self.client.get('/api/optionSets', params=params)
    
    async def validate_metadata(
        self,
        metadata: Union[Dict[str, Any], str]
    ) -> Dict[str, Any]:
        """Validate metadata (dry run import)"""
        return await self.import_(metadata, dry_run=True)
    
    async def export_to_file(
        self,
        file_path: str,
        format: ExportFormat = ExportFormat.JSON,
        **export_kwargs
    ) -> str:
        """Export metadata to file"""
        metadata = await self.export(**export_kwargs)
        
        if format == ExportFormat.JSON:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Metadata export only supports JSON format, got: {format}")
        
        return file_path
    
    async def import_from_file(
        self,
        file_path: str,
        **import_kwargs
    ) -> MetadataImportSummary:
        """Import metadata from file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return await self.import_(metadata, **import_kwargs)
