"""
EVOX Framework Base Exceptions
==============================

Defines the core exception hierarchy for the EVOX framework.
All framework-specific exceptions inherit from BaseError.

Exception Hierarchy:
- BaseError
  - ValidationError
  - StorageError
    - StorageConnectionError
    - StorageOperationError
  - IntentError
    - IntentParsingError
    - IntentConflictError
  - CommunicationError
    - ServiceNotFoundError
    - ProxyError
  - ConfigurationError
  - LifecycleError
"""

from typing import Optional, Any, Dict
import traceback


class BaseError(Exception):
    """Base exception class for all EVOX framework errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message='{self.message}', error_code={self.error_code})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }


class ValidationError(BaseError):
    """Raised when data validation fails."""
    
    def __init__(
        self, 
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        error_code: str = "VALIDATION_ERROR"
    ):
        details = {"field": field, "value": value} if field else {}
        super().__init__(message, error_code, details)


class StorageError(BaseError):
    """Base class for storage-related errors."""
    pass


class StorageConnectionError(StorageError):
    """Raised when storage connection fails."""
    
    def __init__(
        self, 
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        error_code: str = "STORAGE_CONNECTION_ERROR"
    ):
        details = {"host": host, "port": port}
        super().__init__(message, error_code, details)


class StorageOperationError(StorageError):
    """Raised when storage operations fail."""
    
    def __init__(
        self, 
        message: str,
        operation: Optional[str] = None,
        key: Optional[str] = None,
        error_code: str = "STORAGE_OPERATION_ERROR"
    ):
        details = {"operation": operation, "key": key}
        super().__init__(message, error_code, details)


class IntentError(BaseError):
    """Base class for intent-related errors."""
    pass


class IntentParsingError(IntentError):
    """Raised when intent parsing fails."""
    
    def __init__(
        self, 
        message: str,
        intent_source: Optional[str] = None,
        error_code: str = "INTENT_PARSING_ERROR"
    ):
        details = {"intent_source": intent_source}
        super().__init__(message, error_code, details)


class IntentConflictError(IntentError):
    """Raised when conflicting intents are detected."""
    
    def __init__(
        self, 
        message: str,
        field_a: Optional[str] = None,
        field_b: Optional[str] = None,
        error_code: str = "INTENT_CONFLICT_ERROR"
    ):
        details = {"field_a": field_a, "field_b": field_b}
        super().__init__(message, error_code, details)


class CommunicationError(BaseError):
    """Base class for communication-related errors."""
    pass


class ServiceNotFoundError(CommunicationError):
    """Raised when a requested service is not found."""
    
    def __init__(
        self, 
        message: str,
        service_name: Optional[str] = None,
        error_code: str = "SERVICE_NOT_FOUND"
    ):
        details = {"service_name": service_name}
        super().__init__(message, error_code, details)


class ProxyError(CommunicationError):
    """Raised when proxy communication fails."""
    
    def __init__(
        self, 
        message: str,
        target_service: Optional[str] = None,
        error_code: str = "PROXY_ERROR"
    ):
        details = {"target_service": target_service}
        super().__init__(message, error_code, details)


class ConfigurationError(BaseError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(
        self, 
        message: str,
        config_key: Optional[str] = None,
        error_code: str = "CONFIGURATION_ERROR"
    ):
        details = {"config_key": config_key}
        super().__init__(message, error_code, details)


class LifecycleError(BaseError):
    """Raised when lifecycle operations fail."""
    
    def __init__(
        self, 
        message: str,
        phase: Optional[str] = None,
        component: Optional[str] = None,
        error_code: str = "LIFECYCLE_ERROR"
    ):
        details = {"phase": phase, "component": component}
        super().__init__(message, error_code, details)


# Convenience functions for raising common errors
def raise_validation_error(field: str, value: Any, reason: str) -> None:
    """Raise a ValidationError with standardized format."""
    message = f"Validation failed for field '{field}': {reason}"
    raise ValidationError(message, field=field, value=value)


def raise_storage_connection_error(host: str, port: int, reason: str) -> None:
    """Raise a StorageConnectionError with standardized format."""
    message = f"Failed to connect to storage at {host}:{port}: {reason}"
    raise StorageConnectionError(message, host=host, port=port)


def raise_service_not_found(service_name: str) -> None:
    """Raise a ServiceNotFoundError with standardized format."""
    message = f"Service '{service_name}' not found or not registered"
    raise ServiceNotFoundError(message, service_name=service_name)


# Export all exceptions
__all__ = [
    "BaseError",
    "ValidationError", 
    "StorageError",
    "StorageConnectionError",
    "StorageOperationError",
    "IntentError",
    "IntentParsingError",
    "IntentConflictError",
    "CommunicationError",
    "ServiceNotFoundError",
    "ProxyError",
    "ConfigurationError",
    "LifecycleError",
    "raise_validation_error",
    "raise_storage_connection_error",
    "raise_service_not_found"
]