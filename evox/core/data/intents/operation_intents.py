"""
Operation Intent System - Endpoint/Function Level Intent Processing
====================================================================

Provides modular system for declaring operation intents at endpoint/function level
via decorators. Separates concerns from data intents and enables routing,
metrics grouping, and feature activation based on operational context.

Core Components:
- OperationIntent: Enum for operational categories
- OperationIntentDecorator: Decorator for applying operation intents
- OperationIntentRegistry: Tracks endpoint intents for routing/metrics
- IntentBasedRouter: Routes requests based on operation intents
"""

from enum import Enum
from typing import Callable, Dict, Any, Optional, Union
from dataclasses import dataclass
from functools import wraps


class OperationIntent(str, Enum):
    """
    Operational intent categories for endpoints and functions.
    
    Used for routing, metrics grouping, and feature activation based on 
    the operational context of the request.
    """
    USER_MANAGEMENT = "user_management"
    """User creation, modification, deletion operations"""
    
    AUTHENTICATION = "authentication" 
    """Login, logout, token management operations"""
    
    ANALYTICS = "analytics"
    """Data analysis, reporting, dashboard operations"""
    
    DATA_IO = "data_io"
    """Data input/output operations, CRUD operations"""
    
    PAYMENT = "payment"
    """Payment processing, billing, financial operations"""
    
    NOTIFICATION = "notification"
    """Messaging, email, push notification operations"""
    
    SYSTEM_HEALTH = "system_health"
    """Health checks, monitoring, system status operations"""
    
    BACKGROUND_PROCESSING = "background_processing"
    """Async tasks, batch processing, scheduled jobs"""
    
    SEARCH = "search"
    """Search operations, filtering, querying"""
    
    MEDIA_PROCESSING = "media_processing"
    """Image, video, audio processing operations"""
    
    LEGACY = "legacy"
    """Backward compatibility for existing endpoints"""


@dataclass
class OperationIntentConfig:
    """
    Configuration for operation intent behavior.
    
    Defines how different operational intents should be handled by
    various framework components.
    """
    # Routing properties
    queue_priority: str = "normal"
    resource_allocation: str = "standard"
    
    # Metrics properties  
    metrics_group: str = "default"
    sampling_rate: float = 1.0
    
    # Security properties
    auth_required: bool = True
    rate_limiting: bool = True
    
    # Monitoring properties
    detailed_logging: bool = False
    tracing_enabled: bool = False
    
    # Feature activation
    features: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {}


class OperationIntentRegistry:
    """
    Registry for tracking operation intents across endpoints.
    
    Enables centralized management of operational intent metadata
    for routing, metrics, and feature activation decisions.
    """
    
    _instance = None
    _endpoint_intents: Dict[str, Dict[str, Any]] = {}
    _intent_configs: Dict[OperationIntent, OperationIntentConfig] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'OperationIntentRegistry':
        """Get the singleton instance"""
        return cls()
    
    def register_endpoint_intent(
        self, 
        path: str, 
        method: str, 
        intent: OperationIntent,
        config_override: Optional[Dict[str, Any]] = None
    ):
        """Register operation intent for a specific endpoint"""
        route_key = f"{method.upper()} {path}"
        self._endpoint_intents[route_key] = {
            "intent": intent,
            "config_override": config_override or {}
        }
    
    def get_endpoint_intent(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Get operation intent for a specific endpoint"""
        route_key = f"{method.upper()} {path}"
        return self._endpoint_intents.get(route_key)
    
    def register_intent_config(self, intent: OperationIntent, config: OperationIntentConfig):
        """Register custom configuration for an operation intent"""
        self._intent_configs[intent] = config
    
    def get_intent_config(self, intent: OperationIntent) -> OperationIntentConfig:
        """Get configuration for an operation intent"""
        # Return default configs for built-in intents
        default_configs = {
            OperationIntent.USER_MANAGEMENT: OperationIntentConfig(
                queue_priority="high",
                resource_allocation="standard",
                metrics_group="business",
                auth_required=True,
                rate_limiting=True
            ),
            OperationIntent.AUTHENTICATION: OperationIntentConfig(
                queue_priority="highest",
                resource_allocation="high",
                metrics_group="security",
                auth_required=False,  # Authentication endpoints don't require auth
                rate_limiting=True,
                detailed_logging=True
            ),
            OperationIntent.ANALYTICS: OperationIntentConfig(
                queue_priority="low",
                resource_allocation="high",
                metrics_group="analytics",
                sampling_rate=0.1,  # Sample analytics requests
                tracing_enabled=True
            ),
            OperationIntent.DATA_IO: OperationIntentConfig(
                queue_priority="normal",
                resource_allocation="standard",
                metrics_group="data"
            ),
            OperationIntent.PAYMENT: OperationIntentConfig(
                queue_priority="highest",
                resource_allocation="high",
                metrics_group="financial",
                auth_required=True,
                rate_limiting=True,
                detailed_logging=True,
                tracing_enabled=True
            ),
            OperationIntent.NOTIFICATION: OperationIntentConfig(
                queue_priority="low",
                resource_allocation="standard",
                metrics_group="notifications"
            ),
            OperationIntent.SYSTEM_HEALTH: OperationIntentConfig(
                queue_priority="highest",
                resource_allocation="minimum",
                metrics_group="system",
                auth_required=False,
                rate_limiting=False
            ),
            OperationIntent.BACKGROUND_PROCESSING: OperationIntentConfig(
                queue_priority="batch",
                resource_allocation="variable",
                metrics_group="background"
            ),
            OperationIntent.SEARCH: OperationIntentConfig(
                queue_priority="normal",
                resource_allocation="high",
                metrics_group="search"
            ),
            OperationIntent.MEDIA_PROCESSING: OperationIntentConfig(
                queue_priority="normal",
                resource_allocation="high",
                metrics_group="media"
            ),
            OperationIntent.LEGACY: OperationIntentConfig(
                queue_priority="normal",
                resource_allocation="standard",
                metrics_group="legacy"
            )
        }
        
        # Override with custom configs if provided
        base_config = default_configs.get(intent, OperationIntentConfig())
        if intent in self._intent_configs:
            custom_config = self._intent_configs[intent]
            # Merge custom config with base config
            for field in OperationIntentConfig.__dataclass_fields__:
                if hasattr(custom_config, field):
                    setattr(base_config, field, getattr(custom_config, field))
        
        return base_config


class OperationIntentDecorator:
    """
    Decorator for applying operation intents to endpoints.
    
    Provides clean syntax for declaring operational intent while
    maintaining backward compatibility with existing decorators.
    """
    
    def __init__(self, intent: OperationIntent, **kwargs):
        self.intent = intent
        self.kwargs = kwargs
        self.registry = OperationIntentRegistry.get_instance()
    
    def __call__(self, func: Callable) -> Callable:
        """Apply operation intent to decorated function"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Store intent information for framework processing
            if not hasattr(wrapper, '_operation_intent'):
                wrapper._operation_intent = {
                    'intent': self.intent,
                    'config': self.registry.get_intent_config(self.intent),
                    'kwargs': self.kwargs
                }
            return await func(*args, **kwargs)
        
        # Store metadata for endpoint registration
        wrapper._operation_intent_metadata = {
            'intent': self.intent,
            'kwargs': self.kwargs
        }
        
        return wrapper


# Global instances
_operation_intent_registry = OperationIntentRegistry()


def get_operation_intent_registry() -> OperationIntentRegistry:
    """Get the global operation intent registry"""
    return _operation_intent_registry


def operation_intent(intent: OperationIntent, **kwargs):
    """
    Decorator for applying operation intents to endpoints.
    
    Usage:
        @operation_intent(OperationIntent.USER_MANAGEMENT)
        async def create_user(): ...
        
        @operation_intent(OperationIntent.ANALYTICS, sample_rate=0.05)
        async def get_reports(): ...
    """
    return OperationIntentDecorator(intent, **kwargs)


def get_endpoint_operation_intent(path: str, method: str) -> Optional[Dict[str, Any]]:
    """Get operation intent for a specific endpoint"""
    return _operation_intent_registry.get_endpoint_intent(path, method)


def configure_operation_intent(intent: OperationIntent, config: OperationIntentConfig):
    """Configure custom behavior for an operation intent"""
    _operation_intent_registry.register_intent_config(intent, config)


# Convenience decorators for common intents
def user_management(**kwargs):
    """Shortcut for user management operations"""
    return operation_intent(OperationIntent.USER_MANAGEMENT, **kwargs)

def authentication(**kwargs):
    """Shortcut for authentication operations"""
    return operation_intent(OperationIntent.AUTHENTICATION, **kwargs)

def analytics(**kwargs):
    """Shortcut for analytics operations"""
    return operation_intent(OperationIntent.ANALYTICS, **kwargs)

def data_io(**kwargs):
    """Shortcut for data I/O operations"""
    return operation_intent(OperationIntent.DATA_IO, **kwargs)

def payment(**kwargs):
    """Shortcut for payment operations"""
    return operation_intent(OperationIntent.PAYMENT, **kwargs)

def notification(**kwargs):
    """Shortcut for notification operations"""
    return operation_intent(OperationIntent.NOTIFICATION, **kwargs)

def system_health(**kwargs):
    """Shortcut for system health operations"""
    return operation_intent(OperationIntent.SYSTEM_HEALTH, **kwargs)

def background_processing(**kwargs):
    """Shortcut for background processing operations"""
    return operation_intent(OperationIntent.BACKGROUND_PROCESSING, **kwargs)

def search(**kwargs):
    """Shortcut for search operations"""
    return operation_intent(OperationIntent.SEARCH, **kwargs)

def media_processing(**kwargs):
    """Shortcut for media processing operations"""
    return operation_intent(OperationIntent.MEDIA_PROCESSING, **kwargs)