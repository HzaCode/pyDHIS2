"""Exception definitions"""

from typing import Any, Dict, List, Optional
import json


class DHIS2Error(Exception):
    """DHIS2 SDK base exception"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DHIS2HTTPError(DHIS2Error):
    """HTTP request exception"""
    
    def __init__(
        self,
        status: int,
        url: str,
        message: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        self.status = status
        self.url = url
        self.response_data = response_data or {}
        
        if message is None:
            message = f"HTTP {status} error for {url}"
            
        super().__init__(message, {
            'status': status,
            'url': url,
            'response_data': response_data
        })


class AllPagesFetchError(DHIS2HTTPError):
    """Raised when not all pages could be fetched in an atomic paginated request"""
    pass


class RateLimitExceeded(DHIS2Error):
    """Rate limit exceeded exception"""
    
    def __init__(
        self, 
        retry_after: Optional[float] = None,
        current_rate: Optional[float] = None,
        limit: Optional[float] = None
    ):
        self.retry_after = retry_after
        self.current_rate = current_rate  
        self.limit = limit
        
        message = "Rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after}s"
        if current_rate and limit:
            message += f" (current: {current_rate:.2f}, limit: {limit:.2f})"
            
        super().__init__(message, {
            'retry_after': retry_after,
            'current_rate': current_rate,
            'limit': limit
        })


class RetryExhausted(DHIS2Error):
    """Retry attempts exhausted exception"""
    
    def __init__(
        self,
        max_retries: int,
        last_error: Optional[Exception] = None,
        attempt_details: Optional[List[Dict[str, Any]]] = None
    ):
        self.max_retries = max_retries
        self.last_error = last_error
        self.attempt_details = attempt_details or []
        
        message = f"Retry exhausted after {max_retries} attempts"
        if last_error:
            message += f", last error: {last_error}"
            
        super().__init__(message, {
            'max_retries': max_retries,
            'last_error': str(last_error) if last_error else None,
            'attempt_details': attempt_details
        })


class ImportConflictError(DHIS2Error):
    """Import conflict exception"""
    
    def __init__(
        self,
        conflicts: List[Dict[str, Any]],
        import_summary: Optional[Dict[str, Any]] = None
    ):
        self.conflicts = conflicts
        self.import_summary = import_summary or {}
        
        conflict_count = len(conflicts)
        message = f"Import failed with {conflict_count} conflict(s)"
        
        super().__init__(message, {
            'conflicts': conflicts,
            'import_summary': import_summary,
            'conflict_count': conflict_count
        })


class AuthenticationError(DHIS2Error):
    """Authentication failed exception"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class AuthorizationError(DHIS2Error):
    """Authorization failed exception"""
    
    def __init__(self, message: str = "Authorization failed", required_permission: Optional[str] = None):
        self.required_permission = required_permission
        
        if required_permission:
            message += f", required permission: {required_permission}"
            
        super().__init__(message, {'required_permission': required_permission})


class ValidationError(DHIS2Error):
    """Data validation exception"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None
    ):
        self.field = field
        self.value = value
        self.validation_errors = validation_errors or []
        
        super().__init__(message, {
            'field': field,
            'value': value,
            'validation_errors': validation_errors
        })


class TimeoutError(DHIS2HTTPError):
    """Raised on request timeout"""
    pass


class DataFormatError(DHIS2Error):
    """Data format exception"""
    
    def __init__(
        self,
        message: str,
        expected_format: Optional[str] = None,
        actual_format: Optional[str] = None,
        data_sample: Optional[Any] = None
    ):
        self.expected_format = expected_format
        self.actual_format = actual_format
        self.data_sample = data_sample
        
        super().__init__(message, {
            'expected_format': expected_format,
            'actual_format': actual_format,
            'data_sample': str(data_sample)[:200] if data_sample else None
        })


class MetadataError(DHIS2Error):
    """Metadata related exception"""
    
    def __init__(
        self,
        message: str,
        object_type: Optional[str] = None,
        object_id: Optional[str] = None
    ):
        self.object_type = object_type
        self.object_id = object_id
        
        super().__init__(message, {
            'object_type': object_type,
            'object_id': object_id
        })


def format_dhis2_error(error_data: Dict[str, Any]) -> str:
    """Format DHIS2 server error message"""
    if not error_data:
        return "Unknown DHIS2 error"
    
    # Try to extract standard error format
    if 'message' in error_data:
        return error_data['message']
    
    if 'error' in error_data:
        error_info = error_data['error']
        if isinstance(error_info, dict):
            return error_info.get('message', str(error_info))
        return str(error_info)
    
    # Try to extract conflict information
    if 'conflicts' in error_data:
        conflicts = error_data['conflicts']
        if conflicts and isinstance(conflicts, list):
            first_conflict = conflicts[0]
            if isinstance(first_conflict, dict):
                return first_conflict.get('object', str(first_conflict))
    
    # Fallback to JSON string
    try:
        return json.dumps(error_data, indent=2)[:500]
    except (TypeError, ValueError):
        return str(error_data)[:500]
