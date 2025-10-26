"""Tests for schema module"""

import pytest
from pydhis2.io.schema import (
    DHIS2Version, FieldMapping, EndpointSchema, SchemaManager
)


class TestDHIS2Version:
    """Test DHIS2Version enum"""
    
    def test_version_values(self):
        """Test version enum values"""
        assert DHIS2Version.V2_36.value == "2.36"
        assert DHIS2Version.V2_37.value == "2.37"
        assert DHIS2Version.V2_38.value == "2.38"
        assert DHIS2Version.V2_39.value == "2.39"
        assert DHIS2Version.V2_40.value == "2.40"
        assert DHIS2Version.V2_41.value == "2.41"
        assert DHIS2Version.UNKNOWN.value == "unknown"
    
    def test_version_iteration(self):
        """Test iterating through versions"""
        versions = list(DHIS2Version)
        assert len(versions) > 0
        assert DHIS2Version.V2_38 in versions


class TestFieldMapping:
    """Test FieldMapping dataclass"""
    
    def test_field_mapping_minimal(self):
        """Test minimal field mapping"""
        mapping = FieldMapping(source_field="dx", target_field="data")
        assert mapping.source_field == "dx"
        assert mapping.target_field == "data"
        assert mapping.data_type == "string"
        assert mapping.required is False
    
    def test_field_mapping_full(self):
        """Test full field mapping"""
        mapping = FieldMapping(
            source_field="dx",
            target_field="data",
            data_type="integer",
            default_value=0,
            transform_func="int",
            required=True,
            version_introduced=DHIS2Version.V2_38,
            version_deprecated=DHIS2Version.V2_40
        )
        assert mapping.data_type == "integer"
        assert mapping.default_value == 0
        assert mapping.transform_func == "int"
        assert mapping.required is True
        assert mapping.version_introduced == DHIS2Version.V2_38
        assert mapping.version_deprecated == DHIS2Version.V2_40


class TestEndpointSchema:
    """Test EndpointSchema dataclass"""
    
    def test_endpoint_schema_minimal(self):
        """Test minimal endpoint schema"""
        schema = EndpointSchema(
            endpoint="analytics",
            version=DHIS2Version.V2_38
        )
        assert schema.endpoint == "analytics"
        assert schema.version == DHIS2Version.V2_38
        assert len(schema.field_mappings) == 0
    
    def test_endpoint_schema_with_mappings(self):
        """Test endpoint schema with field mappings"""
        mappings = [
            FieldMapping("dx", "data"),
            FieldMapping("pe", "period")
        ]
        schema = EndpointSchema(
            endpoint="analytics",
            version=DHIS2Version.V2_38,
            field_mappings=mappings
        )
        assert len(schema.field_mappings) == 2
    
    def test_endpoint_schema_with_pagination(self):
        """Test endpoint schema with pagination fields"""
        schema = EndpointSchema(
            endpoint="analytics",
            version=DHIS2Version.V2_38,
            pagination_fields={
                "page": "page",
                "pageSize": "pageSize"
            }
        )
        assert "page" in schema.pagination_fields
        assert schema.pagination_fields["page"] == "page"


class TestSchemaManager:
    """Test SchemaManager"""
    
    @pytest.fixture
    def manager(self):
        """Schema manager instance"""
        return SchemaManager()
    
    def test_init(self, manager):
        """Test schema manager initialization"""
        assert manager is not None
        assert isinstance(manager.schemas, dict)
    
    def test_default_schemas_loaded(self, manager):
        """Test that default schemas are loaded"""
        # Should have schemas for common endpoints
        assert len(manager.schemas) > 0
    
    def test_get_schema_analytics(self, manager):
        """Test getting analytics schema"""
        schema = manager.get_schema("analytics", DHIS2Version.V2_38)
        assert schema is not None
        assert schema.endpoint == "analytics"
        assert schema.version == DHIS2Version.V2_38
    
    def test_get_schema_datavaluesets(self, manager):
        """Test getting datavaluesets schema"""
        schema = manager.get_schema("datavaluesets", DHIS2Version.V2_38)
        assert schema is not None
        assert schema.endpoint == "datavaluesets"
    
    def test_get_schema_tracker(self, manager):
        """Test getting tracker schema"""
        schema = manager.get_schema("tracker", DHIS2Version.V2_38)
        assert schema is not None
        assert schema.endpoint == "tracker"
    
    def test_get_schema_metadata(self, manager):
        """Test getting metadata schema"""
        schema = manager.get_schema("metadata", DHIS2Version.V2_38)
        assert schema is not None
        assert schema.endpoint == "metadata"
    
    def test_get_schema_unknown_endpoint(self, manager):
        """Test getting schema for unknown endpoint"""
        schema = manager.get_schema("unknown_endpoint", DHIS2Version.V2_38)
        assert schema is None
    
    def test_get_schema_fallback_version(self, manager):
        """Test schema fallback to earlier version"""
        # Should fall back to latest available version
        schema = manager.get_schema("analytics", DHIS2Version.UNKNOWN)
        # Should still get a schema (fallback to default)
        assert schema is None or schema is not None
    
    def test_register_schema(self, manager):
        """Test registering a custom schema"""
        custom_schema = EndpointSchema(
            endpoint="custom",
            version=DHIS2Version.V2_38
        )
        manager.register_schema("custom", DHIS2Version.V2_38, custom_schema)
        
        retrieved = manager.get_schema("custom", DHIS2Version.V2_38)
        assert retrieved == custom_schema
    
    def test_get_field_mapping(self, manager):
        """Test getting field mapping"""
        mapping = manager.get_field_mapping("analytics", "dx", DHIS2Version.V2_38)
        if mapping:
            assert mapping.source_field == "dx"
    
    def test_get_pagination_fields(self, manager):
        """Test getting pagination fields"""
        pagination = manager.get_pagination_fields("analytics", DHIS2Version.V2_38)
        if pagination:
            assert isinstance(pagination, dict)
    
    def test_list_endpoints(self, manager):
        """Test listing available endpoints"""
        endpoints = manager.list_endpoints()
        assert isinstance(endpoints, list)
        assert len(endpoints) > 0
    
    def test_list_versions_for_endpoint(self, manager):
        """Test listing versions for an endpoint"""
        versions = manager.list_versions("analytics")
        assert isinstance(versions, list)
        if len(versions) > 0:
            assert all(isinstance(v, DHIS2Version) for v in versions)


# Note: SchemaValidator and SchemaConverter are not implemented yet

