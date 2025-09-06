"""Endpoints module - Wrappers for various DHIS2 API endpoints"""

from pydhis2.endpoints.analytics import AnalyticsEndpoint
from pydhis2.endpoints.datavaluesets import DataValueSetsEndpoint
from pydhis2.endpoints.tracker import TrackerEndpoint
from pydhis2.endpoints.metadata import MetadataEndpoint

__all__ = [
    "AnalyticsEndpoint",
    "DataValueSetsEndpoint", 
    "TrackerEndpoint",
    "MetadataEndpoint",
]
