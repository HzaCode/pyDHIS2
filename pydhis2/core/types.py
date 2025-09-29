"""Type definitions and configuration models"""

from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class AuthMethod(str, Enum):
    """Authentication method enumeration"""
    BASIC = "basic"
    TOKEN = "token" 
    PAT = "pat"  # Personal Access Token


class RetryStrategy(str, Enum):
    """Retry strategy enumeration"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


class DHIS2Config(BaseModel):
    """
    Configuration model for the DHIS2 client.
    """
    base_url: str = Field(..., description="Base URL of the DHIS2 instance")
    auth: Optional[Union[Tuple[str, str], str]] = Field(None, description="Authentication: tuple for basic auth or string for token")
    api_version: Optional[Union[int, str]] = Field(None, description="DHIS2 API version")
    user_agent: str = Field("pydhis2/0.2.0", description="User-Agent for requests")
    
    # Timeout settings (total) - Increased default for more resilience
    timeout: float = Field(60.0, description="Total request timeout in seconds")
    
    # Concurrency and rate limiting
    rps: float = Field(10.0, description="Requests per second limit", gt=0)
    concurrency: int = Field(10, description="Maximum concurrent connections", gt=0)

    # Compression and caching
    compression: bool = Field(True, description="Whether to enable gzip compression")
    enable_cache: bool = Field(True, description="Whether to enable caching")
    cache_ttl: int = Field(3600, description="Cache TTL in seconds", gt=0)
    
    # Retry configuration - Increased defaults for more resilience
    max_retries: int = Field(5, description="Maximum retry attempts", ge=0)
    retry_strategy: RetryStrategy = Field(RetryStrategy.EXPONENTIAL, description="Retry strategy")
    retry_base_delay: float = Field(1.5, description="Base retry delay in seconds", gt=0)
    retry_backoff_factor: float = Field(2.0, description="Backoff factor", gt=1.0)
    retry_on_status: List[int] = Field(
        [429, 500, 502, 503, 504], description="HTTP status codes that trigger a retry"
    )

    @validator('base_url')
    def validate_base_url(cls, v):
        """Validate and normalize base URL"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        # Remove trailing slash
        return v.rstrip('/')

    @validator('auth')
    def validate_auth(cls, v):
        """Validate authentication"""
        if v is None:
            return v
        if isinstance(v, tuple):
            if len(v) != 2:
                raise ValueError('Authentication tuple must have exactly 2 elements (username, password)')
            return v
        if isinstance(v, str):
            return v
        raise ValueError('Authentication must be a tuple or string')

    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout"""
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v

    @property
    def auth_method(self) -> AuthMethod:
        """Get authentication method"""
        if self.auth is None:
            return AuthMethod.BASIC  # Default fallback
        if isinstance(self.auth, tuple):
            return AuthMethod.BASIC
        return AuthMethod.TOKEN

    class Config:
        frozen = True
        use_enum_values = True


class PaginationConfig(BaseModel):
    """Pagination configuration"""
    
    page_size: int = Field(200, description="Default page size", gt=0, le=10000)
    max_pages: Optional[int] = Field(None, description="Maximum page limit")
    use_paging: bool = Field(True, description="Whether to enable paging")


class AnalyticsQuery(BaseModel):
    """Analytics query configuration"""
    
    dx: Union[str, List[str]] = Field(..., description="Data dimension (indicators/data elements)")
    ou: Union[str, List[str]] = Field(..., description="Organization units") 
    pe: Union[str, List[str]] = Field(..., description="Period dimension")
    co: Optional[Union[str, List[str]]] = Field(None, description="Category option combinations")
    ao: Optional[Union[str, List[str]]] = Field(None, description="Attribute option combinations")
    
    output_id_scheme: str = Field("UID", description="Output ID scheme")
    display_property: str = Field("NAME", description="Display property")
    skip_meta: bool = Field(False, description="Skip metadata")
    skip_data: bool = Field(False, description="Skip data")
    skip_rounding: bool = Field(False, description="Skip rounding")
    
    def to_params(self) -> Dict[str, Any]:
        """Convert to request parameters"""
        params = {}
        dimensions = []
        
        # Process dimensions - use correct DHIS2 Analytics API format
        for dim in ['dx', 'ou', 'pe', 'co', 'ao']:
            value = getattr(self, dim)
            if value is not None:
                if isinstance(value, list):
                    dimensions.append(f'{dim}:{";".join(value)}')
                else:
                    dimensions.append(f'{dim}:{value}')
        
        # Add dimensions as multiple dimension parameters
        if dimensions:
            params['dimension'] = dimensions
        
        # Other parameters
        params.update({
            'outputIdScheme': self.output_id_scheme,
            'displayProperty': self.display_property,
            'skipMeta': str(self.skip_meta).lower(),
            'skipData': str(self.skip_data).lower(),
            'skipRounding': str(self.skip_rounding).lower(),
        })
        
        return params


class ImportStrategy(str, Enum):
    """Import strategy enumeration"""
    CREATE = "CREATE"
    UPDATE = "UPDATE" 
    CREATE_AND_UPDATE = "CREATE_AND_UPDATE"
    DELETE = "DELETE"


class ImportMode(str, Enum):
    """Import mode enumeration"""
    COMMIT = "COMMIT"
    VALIDATE = "VALIDATE"


class ImportConfig(BaseModel):
    """Import configuration"""
    
    strategy: ImportStrategy = Field(
        ImportStrategy.CREATE_AND_UPDATE, description="Import strategy"
    )
    import_mode: ImportMode = Field(ImportMode.COMMIT, description="Import mode")
    atomic: bool = Field(True, description="Whether to perform atomic import")
    dry_run: bool = Field(False, description="Whether this is a dry run")
    chunk_size: int = Field(5000, description="Chunk size", gt=0)
    max_chunks: Optional[int] = Field(None, description="Maximum number of chunks")
    
    # Conflict handling
    skip_existing_check: bool = Field(False, description="Skip existing check")
    skip_audit: bool = Field(False, description="Skip audit")
    
    # Performance options
    async_import: bool = Field(False, description="Whether to perform async import")
    force: bool = Field(False, description="Force import")


class DataFrameFormat(str, Enum):
    """DataFrame output format"""
    PANDAS = "pandas"
    ARROW = "arrow" 
    POLARS = "polars"


class ExportFormat(str, Enum):
    """Export format"""
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    EXCEL = "excel"
    FEATHER = "feather"
