"""Schema manager - Handles data structure differences across DHIS2 versions"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DHIS2Version(Enum):
    """DHIS2 version enumeration"""
    V2_36 = "2.36"
    V2_37 = "2.37"
    V2_38 = "2.38"
    V2_39 = "2.39"
    V2_40 = "2.40"
    V2_41 = "2.41"
    UNKNOWN = "unknown"


@dataclass
class FieldMapping:
    """Field mapping definition"""
    source_field: str
    target_field: str
    data_type: str = "string"
    default_value: Any = None
    transform_func: Optional[str] = None
    required: bool = False
    version_introduced: Optional[DHIS2Version] = None
    version_deprecated: Optional[DHIS2Version] = None


@dataclass
class EndpointSchema:
    """Endpoint Schema definition"""
    endpoint: str
    version: DHIS2Version
    field_mappings: List[FieldMapping] = field(default_factory=list)
    response_structure: Dict[str, Any] = field(default_factory=dict)
    pagination_fields: Dict[str, str] = field(default_factory=dict)


class SchemaManager:
    """Schema manager"""
    
    def __init__(self):
        self.schemas: Dict[str, Dict[DHIS2Version, EndpointSchema]] = {}
        self._init_default_schemas()
    
    def _init_default_schemas(self) -> None:
        """Initialize default Schemas"""
        self._init_analytics_schemas()
        self._init_datavaluesets_schemas()
        self._init_tracker_schemas()
        self._init_metadata_schemas()
    
    def _init_analytics_schemas(self) -> None:
        """Initialize Analytics Schema"""
        # Common Analytics field mapping
        common_analytics_fields = [
            FieldMapping("dx", "dx", "string", required=True),
            FieldMapping("pe", "period", "string", required=True),
            FieldMapping("ou", "orgUnit", "string", required=True),
            FieldMapping("co", "categoryOptionCombo", "string"),
            FieldMapping("ao", "attributeOptionCombo", "string"),
            FieldMapping("value", "value", "float"),
        ]
        
        analytics_schemas = {}
        
        for version in DHIS2Version:
            if version == DHIS2Version.UNKNOWN:
                continue
            
            schema = EndpointSchema(
                endpoint="analytics",
                version=version,
                field_mappings=common_analytics_fields.copy(),
                response_structure={
                    "headers": "array",
                    "rows": "array",
                    "metaData": "object",
                    "width": "integer",
                    "height": "integer"
                },
                pagination_fields={
                    "page": "page",
                    "pageSize": "pageSize",
                    "pageCount": "pageCount",
                    "total": "total"
                }
            )
            
            # Version-specific adjustments
            if version in [DHIS2Version.V2_36, DHIS2Version.V2_37]:
                # Older versions may not have some fields
                schema.field_mappings.append(
                    FieldMapping("lastUpdated", "lastUpdated", "datetime", 
                               version_introduced=DHIS2Version.V2_38)
                )
            
            analytics_schemas[version] = schema
        
        self.schemas["analytics"] = analytics_schemas
    
    def _init_datavaluesets_schemas(self) -> None:
        """Initialize DataValueSets Schema"""
        common_dvs_fields = [
            FieldMapping("dataElement", "dataElement", "string", required=True),
            FieldMapping("period", "period", "string", required=True),
            FieldMapping("orgUnit", "orgUnit", "string", required=True),
            FieldMapping("categoryOptionCombo", "categoryOptionCombo", "string"),
            FieldMapping("attributeOptionCombo", "attributeOptionCombo", "string"),
            FieldMapping("value", "value", "string", required=True),
            FieldMapping("storedBy", "storedBy", "string"),
            FieldMapping("lastUpdated", "lastUpdated", "datetime"),
            FieldMapping("created", "created", "datetime"),
            FieldMapping("comment", "comment", "string"),
            FieldMapping("followup", "followup", "boolean"),
        ]
        
        dvs_schemas = {}
        
        for version in DHIS2Version:
            if version == DHIS2Version.UNKNOWN:
                continue
            
            schema = EndpointSchema(
                endpoint="dataValueSets",
                version=version,
                field_mappings=common_dvs_fields.copy(),
                response_structure={
                    "dataValues": "array",
                    "completeDataSetRegistrations": "array"
                }
            )
            
            dvs_schemas[version] = schema
        
        self.schemas["dataValueSets"] = dvs_schemas
    
    def _init_tracker_schemas(self) -> None:
        """Initialize Tracker Schema"""
        tracker_event_fields = [
            FieldMapping("event", "event", "string"),
            FieldMapping("program", "program", "string", required=True),
            FieldMapping("programStage", "programStage", "string"),
            FieldMapping("orgUnit", "orgUnit", "string", required=True),
            FieldMapping("orgUnitName", "orgUnitName", "string"),
            FieldMapping("status", "status", "string"),
            FieldMapping("occurredAt", "occurredAt", "datetime"),
            FieldMapping("scheduledAt", "scheduledAt", "datetime"),
            FieldMapping("createdAt", "createdAt", "datetime"),
            FieldMapping("updatedAt", "updatedAt", "datetime"),
            FieldMapping("dataValues", "dataValues", "array"),
        ]
        
        tracker_schemas = {}
        
        for version in DHIS2Version:
            if version == DHIS2Version.UNKNOWN:
                continue
            
            schema = EndpointSchema(
                endpoint="tracker/events",
                version=version,
                field_mappings=tracker_event_fields.copy(),
                response_structure={
                    "instances": "array",
                    "page": "object"
                },
                pagination_fields={
                    "page": "page",
                    "pageSize": "pageSize",
                    "pageCount": "pageCount",
                    "total": "total"
                }
            )
            
            # Version-specific adjustments
            if version in [DHIS2Version.V2_36, DHIS2Version.V2_37]:
                # Older versions use different field names
                schema.field_mappings = [
                    fm for fm in schema.field_mappings 
                    if fm.source_field not in ["occurredAt", "scheduledAt"]
                ]
                schema.field_mappings.extend([
                    FieldMapping("eventDate", "occurredAt", "datetime"),
                    FieldMapping("dueDate", "scheduledAt", "datetime"),
                ])
            
            tracker_schemas[version] = schema
        
        self.schemas["tracker"] = tracker_schemas
    
    def _init_metadata_schemas(self) -> None:
        """Initialize Metadata Schema"""
        metadata_fields = [
            FieldMapping("id", "id", "string", required=True),
            FieldMapping("name", "name", "string"),
            FieldMapping("code", "code", "string"),
            FieldMapping("lastUpdated", "lastUpdated", "datetime"),
            FieldMapping("created", "created", "datetime"),
        ]
        
        metadata_schemas = {}
        
        for version in DHIS2Version:
            if version == DHIS2Version.UNKNOWN:
                continue
            
            schema = EndpointSchema(
                endpoint="metadata",
                version=version,
                field_mappings=metadata_fields.copy(),
                response_structure={
                    "system": "object",
                    "date": "string",
                    "dataElements": "array",
                    "indicators": "array",
                    "organisationUnits": "array",
                    "optionSets": "array",
                }
            )
            
            metadata_schemas[version] = schema
        
        self.schemas["metadata"] = metadata_schemas
    
    def get_schema(
        self,
        endpoint: str,
        version: DHIS2Version = DHIS2Version.V2_41
    ) -> Optional[EndpointSchema]:
        """Get Schema for a specific endpoint and version"""
        endpoint_schemas = self.schemas.get(endpoint)
        if not endpoint_schemas:
            return None
        
        return endpoint_schemas.get(version)
    
    def get_field_mapping(
        self,
        endpoint: str,
        version: DHIS2Version = DHIS2Version.V2_41
    ) -> Dict[str, FieldMapping]:
        """Get field mapping"""
        schema = self.get_schema(endpoint, version)
        if not schema:
            return {}
        
        return {fm.source_field: fm for fm in schema.field_mappings}
    
    def transform_response(
        self,
        data: Dict[str, Any],
        endpoint: str,
        version: DHIS2Version = DHIS2Version.V2_41
    ) -> Dict[str, Any]:
        """Transform response data according to Schema"""
        schema = self.get_schema(endpoint, version)
        if not schema:
            logger.warning(f"No schema found for {endpoint} version {version}")
            return data
        
        # Apply field mappings
        transformed_data = {}
        field_mappings = self.get_field_mapping(endpoint, version)
        
        for key, value in data.items():
            if key in field_mappings:
                mapping = field_mappings[key]
                transformed_data[mapping.target_field] = self._transform_value(
                    value, mapping.data_type, mapping.transform_func
                )
            else:
                transformed_data[key] = value
        
        return transformed_data
    
    def _transform_value(
        self,
        value: Any,
        data_type: str,
        transform_func: Optional[str] = None
    ) -> Any:
        """Transform a single value"""
        if value is None:
            return None
        
        # Apply custom transform function
        if transform_func:
            try:
                if transform_func == "to_float":
                    return float(value)
                elif transform_func == "to_int":
                    return int(value)
                elif transform_func == "to_bool":
                    return bool(value)
                elif transform_func == "to_datetime":
                    import pandas as pd
                    return pd.to_datetime(value)
            except (ValueError, TypeError):
                logger.warning(f"Failed to apply transform {transform_func} to {value}")
                return value
        
        # Default type conversion
        try:
            if data_type == "float":
                return float(value)
            elif data_type == "integer":
                return int(value)
            elif data_type == "boolean":
                return bool(value)
            elif data_type == "datetime":
                import pandas as pd
                return pd.to_datetime(value)
            else:
                return str(value) if value is not None else None
        except (ValueError, TypeError):
            return value
    
    def detect_version(self, response: Dict[str, Any]) -> DHIS2Version:
        """Detect DHIS2 version from response"""
        # Check system info
        if "system" in response:
            system_info = response["system"]
            version_str = system_info.get("version", "")
            
            for version in DHIS2Version:
                if version.value in version_str:
                    return version
        
        # Infer version based on response structure
        if "instances" in response:
            # New Tracker API
            return DHIS2Version.V2_40
        elif "events" in response and isinstance(response["events"], list):
            # Old Tracker API
            return DHIS2Version.V2_36
        
        # Default to latest version
        return DHIS2Version.V2_41
    
    def validate_data(
        self,
        data: Dict[str, Any],
        endpoint: str,
        version: DHIS2Version = DHIS2Version.V2_41
    ) -> List[str]:
        """Validate data against Schema"""
        schema = self.get_schema(endpoint, version)
        if not schema:
            return ["Schema not found"]
        
        errors = []
        field_mappings = self.get_field_mapping(endpoint, version)
        
        # Check required fields
        for mapping in schema.field_mappings:
            if mapping.required and mapping.source_field not in data:
                errors.append(f"Missing required field: {mapping.source_field}")
        
        # Check data types (simple validation)
        for key, value in data.items():
            if key in field_mappings and value is not None:
                mapping = field_mappings[key]
                if not self._validate_type(value, mapping.data_type):
                    errors.append(f"Invalid type for {key}: expected {mapping.data_type}")
        
        return errors
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type"""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "float":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        elif expected_type == "datetime":
            import pandas as pd
            try:
                pd.to_datetime(value)
                return True
            except:
                return False
        else:
            return True  # Unknown types pass validation
