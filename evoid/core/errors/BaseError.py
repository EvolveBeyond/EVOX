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

from typing import Optional, Any, Dict, Callable
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


# DATABASE-SPECIFIC EXCEPTIONS
class DatabaseError(StorageError):
    """Base class for database-related errors."""
    
    def __init__(
        self,
        message: str,
        database_type: Optional[str] = None,
        query: Optional[str] = None,
        error_code: str = "DATABASE_ERROR"
    ):
        details = {"database_type": database_type, "query": query}
        super().__init__(message, error_code, details)


class DuplicateKeyError(DatabaseError):
    """Raised when attempting to insert duplicate key/constraint violation."""
    
    def __init__(
        self,
        message: str,
        table: Optional[str] = None,
        constraint: Optional[str] = None,
        error_code: str = "DUPLICATE_KEY_ERROR"
    ):
        details = {"table": table, "constraint": constraint}
        super().__init__(message, error_code=error_code, database_type="relational")


class ForeignKeyViolationError(DatabaseError):
    """Raised when foreign key constraint is violated."""
    
    def __init__(
        self,
        message: str,
        table: Optional[str] = None,
        foreign_key: Optional[str] = None,
        error_code: str = "FOREIGN_KEY_VIOLATION"
    ):
        details = {"table": table, "foreign_key": foreign_key}
        super().__init__(message, error_code=error_code, database_type="relational")


class ConnectionTimeoutError(DatabaseError):
    """Raised when database connection times out."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[int] = None,
        error_code: str = "CONNECTION_TIMEOUT"
    ):
        details = {"timeout_seconds": timeout_seconds}
        super().__init__(message, error_code=error_code)


class QueryExecutionError(DatabaseError):
    """Raised when database query execution fails."""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        error_details: Optional[str] = None,
        error_code: str = "QUERY_EXECUTION_ERROR"
    ):
        details = {"query": query, "error_details": error_details}
        super().__init__(message, error_code=error_code)


class TransactionError(DatabaseError):
    """Raised when database transaction operations fail."""
    
    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        operation: Optional[str] = None,
        error_code: str = "TRANSACTION_ERROR"
    ):
        details = {"transaction_id": transaction_id, "operation": operation}
        super().__init__(message, error_code=error_code)


class SchemaValidationError(DatabaseError):
    """Raised when database schema validation fails."""
    
    def __init__(
        self,
        message: str,
        table: Optional[str] = None,
        field: Optional[str] = None,
        error_code: str = "SCHEMA_VALIDATION_ERROR"
    ):
        details = {"table": table, "field": field}
        super().__init__(message, error_code=error_code)


class DBExceptionInterceptor:
    """
    Database Exception Interceptor - Unified error handling for database operations.
    
    This class intercepts database-specific exceptions and converts them
    to standardized EVOX framework errors, ensuring consistent error handling
    across different database backends.
    
    Features:
    - Maps database-specific errors to unified EVOX errors
    - Preserves original error context for debugging
    - Provides structured error responses for OpenAPI compliance
    - Supports custom error mapping rules
    """
    
    def __init__(self):
        self._error_mappings = {}
        self._setup_default_mappings()
    
    def _setup_default_mappings(self):
        """Setup default error mappings for common database errors."""
        # PostgreSQL error mappings
        self._error_mappings.update({
            "psycopg2.IntegrityError": self._handle_postgres_integrity_error,
            "psycopg2.OperationalError": self._handle_postgres_operational_error,
            "asyncpg.UniqueViolationError": self._handle_unique_violation,
            "asyncpg.ForeignKeyViolationError": self._handle_foreign_key_violation,
            "asyncpg.ConnectionDoesNotExistError": self._handle_connection_error,
        })
        
        # MySQL error mappings
        self._error_mappings.update({
            "pymysql.IntegrityError": self._handle_mysql_integrity_error,
            "aiomysql.OperationalError": self._handle_mysql_operational_error,
        })
        
        # MongoDB error mappings
        self._error_mappings.update({
            "pymongo.errors.DuplicateKeyError": self._handle_duplicate_key_error,
            "motor.core.AgnosticBulkWriteError": self._handle_bulk_write_error,
        })
        
        # Redis error mappings
        self._error_mappings.update({
            "redis.exceptions.ConnectionError": self._handle_redis_connection_error,
            "redis.exceptions.TimeoutError": self._handle_redis_timeout_error,
        })
    
    def intercept(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> BaseError:
        """
        Intercept and convert database exception to unified EVOX error.
        
        Args:
            exception: Original database exception
            context: Additional context information
            
        Returns:
            Unified EVOX BaseError instance
        """
        exception_type = f"{exception.__class__.__module__}.{exception.__class__.__name__}"
        
        # Check for custom mapping
        if exception_type in self._error_mappings:
            handler = self._error_mappings[exception_type]
            return handler(exception, context)
        
        # Check for base class mappings
        for base_class in exception.__class__.__mro__:
            base_type = f"{base_class.__module__}.{base_class.__name__}"
            if base_type in self._error_mappings:
                handler = self._error_mappings[base_type]
                return handler(exception, context)
        
        # Default fallback - wrap as generic DatabaseError
        return self._handle_generic_database_error(exception, context)
    
    def _handle_postgres_integrity_error(self, exc: Exception, context: Optional[Dict] = None) -> DatabaseError:
        """Handle PostgreSQL integrity errors."""
        error_msg = str(exc)
        
        if "duplicate key" in error_msg.lower():
            return DuplicateKeyError(
                f"Duplicate key constraint violation: {error_msg}",
                table=context.get("table") if context else None,
                constraint=self._extract_constraint_name(error_msg)
            )
        elif "foreign key" in error_msg.lower():
            return ForeignKeyViolationError(
                f"Foreign key constraint violation: {error_msg}",
                table=context.get("table") if context else None,
                foreign_key=self._extract_foreign_key_name(error_msg)
            )
        else:
            return DatabaseError(f"PostgreSQL integrity error: {error_msg}")
    
    def _handle_postgres_operational_error(self, exc: Exception, context: Optional[Dict] = None) -> DatabaseError:
        """Handle PostgreSQL operational errors."""
        error_msg = str(exc)
        
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return ConnectionTimeoutError(
                f"PostgreSQL connection error: {error_msg}",
                timeout_seconds=context.get("timeout") if context else None
            )
        else:
            return DatabaseError(f"PostgreSQL operational error: {error_msg}")
    
    def _handle_unique_violation(self, exc: Exception, context: Optional[Dict] = None) -> DuplicateKeyError:
        """Handle unique constraint violations."""
        return DuplicateKeyError(
            f"Unique constraint violation: {str(exc)}",
            table=context.get("table") if context else None,
            constraint=getattr(exc, "constraint_name", None)
        )
    
    def _handle_foreign_key_violation(self, exc: Exception, context: Optional[Dict] = None) -> ForeignKeyViolationError:
        """Handle foreign key violations."""
        return ForeignKeyViolationError(
            f"Foreign key constraint violation: {str(exc)}",
            table=context.get("table") if context else None,
            foreign_key=getattr(exc, "constraint_name", None)
        )
    
    def _handle_connection_error(self, exc: Exception, context: Optional[Dict] = None) -> ConnectionTimeoutError:
        """Handle database connection errors."""
        return ConnectionTimeoutError(
            f"Database connection failed: {str(exc)}",
            timeout_seconds=context.get("timeout") if context else None
        )
    
    def _handle_mysql_integrity_error(self, exc: Exception, context: Optional[Dict] = None) -> DatabaseError:
        """Handle MySQL integrity errors."""
        error_msg = str(exc)
        error_code = getattr(exc, "args", [None])[0] if hasattr(exc, "args") else None
        
        if error_code == 1062:  # Duplicate entry
            return DuplicateKeyError(f"MySQL duplicate entry: {error_msg}")
        elif error_code == 1452:  # Cannot add or update child row
            return ForeignKeyViolationError(f"MySQL foreign key violation: {error_msg}")
        else:
            return DatabaseError(f"MySQL integrity error: {error_msg}")
    
    def _handle_mysql_operational_error(self, exc: Exception, context: Optional[Dict] = None) -> DatabaseError:
        """Handle MySQL operational errors."""
        return DatabaseError(f"MySQL operational error: {str(exc)}")
    
    def _handle_duplicate_key_error(self, exc: Exception, context: Optional[Dict] = None) -> DuplicateKeyError:
        """Handle MongoDB duplicate key errors."""
        return DuplicateKeyError(
            f"MongoDB duplicate key error: {str(exc)}",
            table=context.get("collection") if context else None
        )
    
    def _handle_bulk_write_error(self, exc: Exception, context: Optional[Dict] = None) -> DatabaseError:
        """Handle MongoDB bulk write errors."""
        return DatabaseError(f"MongoDB bulk write error: {str(exc)}")
    
    def _handle_redis_connection_error(self, exc: Exception, context: Optional[Dict] = None) -> ConnectionTimeoutError:
        """Handle Redis connection errors."""
        return ConnectionTimeoutError(f"Redis connection error: {str(exc)}")
    
    def _handle_redis_timeout_error(self, exc: Exception, context: Optional[Dict] = None) -> ConnectionTimeoutError:
        """Handle Redis timeout errors."""
        return ConnectionTimeoutError(
            f"Redis operation timed out: {str(exc)}",
            timeout_seconds=context.get("timeout") if context else None
        )
    
    def _handle_generic_database_error(self, exc: Exception, context: Optional[Dict] = None) -> DatabaseError:
        """Handle generic database errors."""
        return DatabaseError(
            f"Database operation failed: {str(exc)}",
            database_type=context.get("database_type") if context else "unknown",
            query=context.get("query") if context else None
        )
    
    def _extract_constraint_name(self, error_message: str) -> Optional[str]:
        """Extract constraint name from error message."""
        import re
        match = re.search(r"constraint\s+([\w_]+)", error_message, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _extract_foreign_key_name(self, error_message: str) -> Optional[str]:
        """Extract foreign key name from error message."""
        import re
        match = re.search(r"foreign\s+key\s+([\w_]+)", error_message, re.IGNORECASE)
        return match.group(1) if match else None
    
    def register_custom_mapping(self, exception_type: str, handler: Callable):
        """
        Register custom error mapping handler.
        
        Args:
            exception_type: Full exception type name (module.ClassName)
            handler: Function to handle the exception
        """
        self._error_mappings[exception_type] = handler
    
    def get_standardized_response(self, error: BaseError) -> Dict[str, Any]:
        """
        Generate standardized error response for OpenAPI compliance.
        
        Args:
            error: EVOX BaseError instance
            
        Returns:
            Dictionary with standardized error response structure
        """
        return {
            "error": {
                "type": error.__class__.__name__,
                "code": error.error_code,
                "message": error.message,
                "details": error.details,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "documentation_url": f"https://docs.evoid.dev/errors/{error.error_code}"
            }
        }


# Global interceptor instance
db_exception_interceptor = DBExceptionInterceptor()


# Convenience function for error interception
def intercept_database_error(exception: Exception, context: Optional[Dict[str, Any]] = None) -> BaseError:
    """Intercept and convert database exception to unified EVOX error."""
    return db_exception_interceptor.intercept(exception, context)


def get_standardized_error_response(error: BaseError) -> Dict[str, Any]:
    """Generate standardized error response for OpenAPI compliance."""
    return db_exception_interceptor.get_standardized_response(error)


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
    # DATABASE-SPECIFIC EXCEPTIONS
    "DatabaseError",
    "DuplicateKeyError",
    "ForeignKeyViolationError",
    "ConnectionTimeoutError",
    "QueryExecutionError",
    "TransactionError",
    "SchemaValidationError",
    # INTERCEPTOR CLASSES AND FUNCTIONS
    "DBExceptionInterceptor",
    "db_exception_interceptor",
    "intercept_database_error",
    "get_standardized_error_response",
    # CONVENIENCE FUNCTIONS
    "raise_validation_error",
    "raise_storage_connection_error",
    "raise_service_not_found"
]