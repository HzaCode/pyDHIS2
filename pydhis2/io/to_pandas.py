"""Pandas DataFrame converters"""

from typing import Any, Dict, List, Optional, Union
import pandas as pd
import json
from datetime import datetime


class AnalyticsDataFrameConverter:
    """Analytics data converter"""
    
    def to_dataframe(
        self,
        data: Dict[str, Any],
        long_format: bool = True
    ) -> pd.DataFrame:
        """Convert Analytics JSON to DataFrame"""
        if 'rows' not in data:
            return pd.DataFrame()
        
        rows = data['rows']
        headers = data.get('headers', [])
        
        if not rows or not headers:
            return pd.DataFrame()
        
        # Create column name mapping
        column_names = [h.get('name', f'col_{i}') for i, h in enumerate(headers)]
        
        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=column_names)
        
        if long_format:
            return self._to_long_format(df, data)
        else:
            return df
    
    def _to_long_format(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """Convert to long format (standardized)"""
        if df.empty:
            return df
        
        # Standard column name mapping
        standard_columns = {
            'dx': 'dx',
            'pe': 'period', 
            'ou': 'orgUnit',
            'co': 'categoryOptionCombo',
            'ao': 'attributeOptionCombo',
            'value': 'value'
        }
        
        # Rename columns
        df_renamed = df.copy()
        for old_name, new_name in standard_columns.items():
            if old_name in df.columns:
                df_renamed = df_renamed.rename(columns={old_name: new_name})
        
        # Convert data types
        if 'value' in df_renamed.columns:
            df_renamed['value'] = pd.to_numeric(df_renamed['value'], errors='coerce')
        
        return df_renamed


class DataValueSetsConverter:
    """DataValueSets data converter"""
    
    def to_dataframe(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Convert DataValueSets JSON to DataFrame"""
        if 'dataValues' not in data:
            return pd.DataFrame()
        
        data_values = data['dataValues']
        if not data_values:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(data_values)
        
        # Standardize column names
        column_mapping = {
            'dataElement': 'dataElement',
            'period': 'period',
            'orgUnit': 'orgUnit',
            'categoryOptionCombo': 'categoryOptionCombo',
            'attributeOptionCombo': 'attributeOptionCombo',
            'value': 'value',
            'storedBy': 'storedBy',
            'lastUpdated': 'lastUpdated',
            'created': 'created',
            'comment': 'comment',
            'followup': 'followup',
        }
        
        # Rename existing columns
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns and old_name != new_name:
                df = df.rename(columns={old_name: new_name})
        
        # Convert data types
        if 'value' in df.columns:
            # Try to convert to numeric, otherwise keep as string
            df['value'] = pd.to_numeric(df['value'], errors='ignore')
        
        # Convert date columns
        date_columns = ['lastUpdated', 'created']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Convert boolean columns
        if 'followup' in df.columns:
            df['followup'] = df['followup'].astype(bool, errors='ignore')
        
        return df
    
    def from_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Convert DataFrame to DataValueSets JSON format"""
        if df.empty:
            return {'dataValues': []}
        
        # Ensure required columns exist
        required_columns = ['dataElement', 'period', 'orgUnit', 'value']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Convert to list of dictionaries
        data_values = []
        for _, row in df.iterrows():
            data_value = {}
            
            # Required fields
            for col in required_columns:
                if pd.notna(row[col]):
                    data_value[col] = str(row[col])
            
            # Optional fields
            optional_fields = [
                'categoryOptionCombo', 'attributeOptionCombo',
                'comment', 'storedBy', 'followup'
            ]
            
            for field in optional_fields:
                if field in df.columns and pd.notna(row[field]):
                    if field == 'followup':
                        data_value[field] = bool(row[field])
                    else:
                        data_value[field] = str(row[field])
            
            data_values.append(data_value)
        
        return {'dataValues': data_values}


class TrackerConverter:
    """Tracker data converter"""
    
    def events_to_dataframe(self, events: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert list of events to DataFrame"""
        if not events:
            return pd.DataFrame()
        
        flattened_events = []
        
        for event in events:
            flat_event = {
                'event': event.get('event', ''),
                'program': event.get('program', ''),
                'programStage': event.get('programStage', ''),
                'orgUnit': event.get('orgUnit', ''),
                'orgUnitName': event.get('orgUnitName', ''),
                'status': event.get('status', ''),
                'occurredAt': event.get('occurredAt', ''),
                'scheduledAt': event.get('scheduledAt', ''),
                'createdAt': event.get('createdAt', ''),
                'updatedAt': event.get('updatedAt', ''),
                'geometry': json.dumps(event.get('geometry')) if event.get('geometry') else None,
            }
            
            # Flatten data values
            data_values = event.get('dataValues', [])
            for dv in data_values:
                data_element = dv.get('dataElement', '')
                value = dv.get('value', '')
                flat_event[f'dataValue_{data_element}'] = value
            
            flattened_events.append(flat_event)
        
        df = pd.DataFrame(flattened_events)
        
        # Convert date columns
        date_columns = ['occurredAt', 'scheduledAt', 'createdAt', 'updatedAt']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def tracked_entities_to_dataframe(self, entities: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert list of tracked entities to DataFrame"""
        if not entities:
            return pd.DataFrame()
        
        flattened_entities = []
        
        for entity in entities:
            flat_entity = {
                'trackedEntity': entity.get('trackedEntity', ''),
                'trackedEntityType': entity.get('trackedEntityType', ''),
                'orgUnit': entity.get('orgUnit', ''),
                'createdAt': entity.get('createdAt', ''),
                'updatedAt': entity.get('updatedAt', ''),
                'geometry': json.dumps(entity.get('geometry')) if entity.get('geometry') else None,
            }
            
            # Flatten attributes
            attributes = entity.get('attributes', [])
            for attr in attributes:
                attribute_id = attr.get('attribute', '')
                value = attr.get('value', '')
                flat_entity[f'attribute_{attribute_id}'] = value
            
            # Add enrollment information
            enrollments = entity.get('enrollments', [])
            if enrollments:
                enrollment = enrollments[0]  # Take the first enrollment
                flat_entity.update({
                    'enrollment': enrollment.get('enrollment', ''),
                    'program': enrollment.get('program', ''),
                    'enrollmentDate': enrollment.get('enrolledAt', ''),
                    'incidentDate': enrollment.get('occurredAt', ''),
                    'enrollmentStatus': enrollment.get('status', ''),
                })
            
            flattened_entities.append(flat_entity)
        
        df = pd.DataFrame(flattened_entities)
        
        # Convert date columns
        date_columns = ['createdAt', 'updatedAt', 'enrollmentDate', 'incidentDate']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def dataframe_to_events(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Convert DataFrame to event format"""
        if df.empty:
            return []
        
        events = []
        
        for _, row in df.iterrows():
            event = {
                'program': row.get('program', ''),
                'programStage': row.get('programStage', ''),
                'orgUnit': row.get('orgUnit', ''),
                'status': row.get('status', 'ACTIVE'),
                'occurredAt': row.get('occurredAt', ''),
            }
            
            # Add optional fields
            optional_fields = ['event', 'scheduledAt', 'geometry']
            for field in optional_fields:
                if field in row and pd.notna(row[field]):
                    if field == 'geometry':
                        try:
                            event[field] = json.loads(row[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    else:
                        event[field] = row[field]
            
            # Extract data values
            data_values = []
            for col in df.columns:
                if col.startswith('dataValue_'):
                    data_element = col.replace('dataValue_', '')
                    value = row[col]
                    if pd.notna(value):
                        data_values.append({
                            'dataElement': data_element,
                            'value': str(value)
                        })
            
            if data_values:
                event['dataValues'] = data_values
            
            events.append(event)
        
        return events


class ImportSummaryConverter:
    """Import summary converter"""
    
    @staticmethod
    def conflicts_to_dataframe(conflicts: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert list of conflicts to DataFrame"""
        if not conflicts:
            return pd.DataFrame(columns=[
                'uid', 'path', 'value', 'conflict_msg', 'status'
            ])
        
        conflict_data = []
        for conflict in conflicts:
            conflict_data.append({
                'uid': conflict.get('object', conflict.get('uid', '')),
                'path': conflict.get('property', conflict.get('path', '')),
                'value': conflict.get('value', ''),
                'conflict_msg': conflict.get('message', ''),
                'status': conflict.get('errorCode', 'ERROR'),
            })
        
        return pd.DataFrame(conflict_data)
    
    @staticmethod
    def summary_to_dataframe(import_summary: Dict[str, Any]) -> pd.DataFrame:
        """Convert import summary to DataFrame"""
        summary_data = {
            'metric': ['imported', 'updated', 'deleted', 'ignored', 'total'],
            'count': [
                import_summary.get('imported', 0),
                import_summary.get('updated', 0),
                import_summary.get('deleted', 0),
                import_summary.get('ignored', 0),
                import_summary.get('total', 0),
            ]
        }
        
        return pd.DataFrame(summary_data)
