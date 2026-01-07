"""
Modern Annotated-Based Intent System for Python 3.13+
=====================================================

Provides clean, type-safe intent declarations using typing.Annotated.
This replaces the legacy json_schema_extra approach with modern Python syntax.

Core Components:
- IntentMarker: Base class for all intent annotations
- Built-in markers: Critical, Standard, Ephemeral
- Helper functions for clean syntax
- Backward compatibility with json_schema_extra
"""

from typing import Annotated, TypeVar, Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import timedelta
import inspect

# Type variable for generic type support
T = TypeVar('T')


@dataclass
class IntentMarker:
    """
    Base intent marker for Annotated type declarations.
    
    This class serves as the foundation for all intent annotations.
    It stores intent configuration and can be extended for custom intents.
    """
    
    def __init__(self, name: str = "base", **kwargs):
        # Known properties
        known_props = ['cache_enabled', 'cache_ttl', 'cache_aggressive', 'encrypt', 
                      'strong_consistency', 'replication_required', 'audit_logging',
                      'task_priority', 'message_priority', 'fallback_enabled', 
                      'emergency_buffer', 'custom_properties', 'name']
        
        # Set default values first
        self.name = name
        self.cache_enabled = True
        self.cache_ttl = None
        self.cache_aggressive = False
        self.encrypt = False
        self.strong_consistency = False
        self.replication_required = False
        self.audit_logging = False
        self.task_priority = "normal"
        self.message_priority = "normal"
        self.fallback_enabled = True
        self.emergency_buffer = False
        self.custom_properties = {}
        
        # Apply provided values
        for key, value in kwargs.items():
            if key in known_props:
                setattr(self, key, value)
            else:
                # Add unknown properties to custom_properties
                self.custom_properties[key] = value


class Critical(IntentMarker):
    """
    Critical intent marker for high-importance data.
    
    Provides strong consistency, encryption, replication, and audit logging.
    """
    def __init__(self, **kwargs):
        super().__init__(name="CRITICAL", **kwargs)
        # Set critical-specific defaults
        self.encrypt = True
        self.strong_consistency = True
        self.replication_required = True
        self.audit_logging = True
        self.task_priority = "high"
        self.message_priority = "high"
        self.fallback_enabled = True
        self.emergency_buffer = True
        # Set default cache TTL for critical data if not provided
        if self.cache_ttl is None:
            from datetime import timedelta
            self.cache_ttl = timedelta(minutes=30)


class Standard(IntentMarker):
    """
    Standard intent marker for normal data.
    
    Provides balanced caching and standard processing.
    """
    def __init__(self, **kwargs):
        super().__init__(name="STANDARD", **kwargs)
        # Set standard-specific defaults
        self.encrypt = False
        self.strong_consistency = False
        self.replication_required = False
        self.audit_logging = False
        self.task_priority = "normal"
        self.message_priority = "normal"
        self.fallback_enabled = True
        self.emergency_buffer = False
        # Set default cache TTL for standard data if not provided
        if self.cache_ttl is None:
            from datetime import timedelta
            self.cache_ttl = timedelta(hours=1)


class Ephemeral(IntentMarker):
    """
    Ephemeral intent marker for temporary/transient data.
    
    Provides aggressive caching with short TTL and minimal persistence.
    """
    def __init__(self, **kwargs):
        super().__init__(name="EPHEMERAL", **kwargs)
        # Set ephemeral-specific defaults
        self.encrypt = False
        self.strong_consistency = False
        self.replication_required = False
        self.audit_logging = False
        self.task_priority = "low"
        self.message_priority = "low"
        self.fallback_enabled = False
        self.emergency_buffer = False
        self.cache_aggressive = True
        # Set default cache TTL for ephemeral data if not provided
        if self.cache_ttl is None:
            from datetime import timedelta
            self.cache_ttl = timedelta(minutes=5)


# Helper functions for clean syntax
def critical(type_: T, **config) -> Any:
    """
    Create a critical intent annotated type.
    
    Usage: name: critical(str, ttl_minutes=30, audit=True)
    """
    # Handle ttl_minutes parameter specially
    if 'ttl_minutes' in config:
        config['cache_ttl'] = timedelta(minutes=config.pop('ttl_minutes'))
    return Annotated[type_, Critical(**config)]


def standard(type_: T, **config) -> Any:
    """
    Create a standard intent annotated type.
    
    Usage: email: standard(str, encrypt=True)
    """
    # Handle ttl_minutes parameter specially
    if 'ttl_minutes' in config:
        config['cache_ttl'] = timedelta(minutes=config.pop('ttl_minutes'))
    return Annotated[type_, Standard(**config)]


def ephemeral(type_: T, **config) -> Any:
    """
    Create an ephemeral intent annotated type.
    
    Usage: temp_token: ephemeral(str)
    """
    # Handle ttl_minutes parameter specially
    if 'ttl_minutes' in config:
        config['cache_ttl'] = timedelta(minutes=config.pop('ttl_minutes'))
    return Annotated[type_, Ephemeral(**config)]


def custom_intent(type_: T, name: str, **config) -> Any:
    """
    Create a custom intent annotated type.
    
    Usage: password: custom_intent(str, "PASSWORD_MASKED", mask=True, no_display=True)
    """
    # Handle ttl_minutes parameter specially
    if 'ttl_minutes' in config:
        config['cache_ttl'] = timedelta(minutes=config.pop('ttl_minutes'))
    return Annotated[type_, IntentMarker(name, **config)]


# Pre-defined reusable annotated types (most common use cases)
CriticalStr = Annotated[str, Critical()]
StandardStr = Annotated[str, Standard()]
EphemeralStr = Annotated[str, Ephemeral()]

CriticalInt = Annotated[int, Critical()]
StandardInt = Annotated[int, Standard()]
EphemeralInt = Annotated[int, Ephemeral()]

CriticalFloat = Annotated[float, Critical()]
StandardFloat = Annotated[float, Standard()]
EphemeralFloat = Annotated[float, Ephemeral()]

CriticalBool = Annotated[bool, Critical()]
StandardBool = Annotated[bool, Standard()]
EphemeralBool = Annotated[bool, Ephemeral()]


def extract_annotated_intents(model_class) -> Dict[str, Any]:
    """
    Extract intent markers from Annotated type hints in a Pydantic model.
    
    This is the primary extraction method for the new Annotated-based system.
    
    Args:
        model_class: Pydantic model class to extract intents from
        
    Returns:
        Dictionary mapping field names to their intent markers
    """
    intents = {}
    
    # Get the model's type annotations
    annotations = getattr(model_class, '__annotations__', {})
    
    for field_name, annotation in annotations.items():
        # Check if this is an Annotated type by looking for __metadata__
        if hasattr(annotation, '__metadata__'):
            # Extract the metadata (intent markers)
            metadata = annotation.__metadata__
            
            # Look for IntentMarker instances in metadata
            for meta_item in metadata:
                if isinstance(meta_item, (IntentMarker, Critical, Standard, Ephemeral)):
                    intents[field_name] = meta_item
                    break
    
    return intents


def get_intent_from_annotation(annotation) -> Optional[IntentMarker]:
    """
    Extract intent marker from a type annotation.
    
    Args:
        annotation: Type annotation to inspect
        
    Returns:
        IntentMarker if found, None otherwise
    """
    if hasattr(annotation, '__origin__') and annotation.__origin__ is Annotated:
        metadata = annotation.__metadata__
        for meta_item in metadata:
            if isinstance(meta_item, (IntentMarker, Critical, Standard, Ephemeral)):
                return meta_item
    return None


# Backward compatibility utilities
def map_legacy_intent_to_marker(legacy_intent_value) -> Optional[IntentMarker]:
    """
    Map legacy intent values to new IntentMarker instances.
    
    This maintains backward compatibility with json_schema_extra={"intent": ...}.
    
    Args:
        legacy_intent_value: Legacy intent value (string, enum, etc.)
        
    Returns:
        Corresponding IntentMarker or None
    """
    from .intent_system import Intent  # Avoid circular import
    
    intent_mapping = {
        Intent.CRITICAL: Critical(),
        Intent.STANDARD: Standard(),
        Intent.EPHEMERAL: Ephemeral(),
        Intent.SENSITIVE: Critical(encrypt=True),
        Intent.LAZY: Ephemeral(),
        "CRITICAL": Critical(),
        "STANDARD": Standard(),
        "EPHEMERAL": Ephemeral(),
        "SENSITIVE": Critical(encrypt=True),
        "LAZY": Ephemeral(),
        "critical": Critical(),
        "standard": Standard(),
        "ephemeral": Ephemeral(),
        "sensitive": Critical(encrypt=True),
        "lazy": Ephemeral(),
    }
    
    return intent_mapping.get(legacy_intent_value)