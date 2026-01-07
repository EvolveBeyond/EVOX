"""
Unified Intent System for EVOX Framework
=========================================

This module provides backward-compatible access to the new modular intent system.
It integrates both Data Intent (field/model level) and Operation Intent 
(endpoint/function level) systems while maintaining full compatibility with
existing code.

Architecture:
- Data intents: Field-level declarations via Pydantic Field json_schema_extra
- Operation intents: Endpoint-level declarations via decorators
- Central resolver: Single point for all intent processing
- Registry system: Global tracking of custom intent definitions

Backward Compatibility:
- Old Intent enum maps to new BuiltInDataIntent
- Existing Field(json_schema_extra={"intent": Intent.XXX}) continues to work
- All existing examples run unchanged
"""

from enum import Enum
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel
from datetime import timedelta

# Import new modular intent systems
from .data_intents import (
    BuiltInDataIntent, BaseIntentConfig, CustomIntentConfig,
    DataIntentRegistry, IntentResolver, get_data_intent_registry,
    get_intent_resolver, register_custom_data_intent, resolve_data_intent
)
from .operation_intents import (
    OperationIntent, OperationIntentConfig, OperationIntentRegistry,
    OperationIntentDecorator, get_operation_intent_registry,
    operation_intent, get_endpoint_operation_intent, configure_operation_intent
)
from .annotated_intents import (
    IntentMarker, extract_annotated_intents, map_legacy_intent_to_marker
)


# Backward compatibility alias
IntentConfig = BaseIntentConfig


class Intent(str, Enum):
    """
    Backward-compatible Intent enum that maps to new BuiltInDataIntent.
    
    Maintains full compatibility with existing code while delegating
    to the new modular intent system internally.
    """
    EPHEMERAL = "ephemeral"
    STANDARD = "standard" 
    CRITICAL = "critical"
    LAZY = "lazy"  # Additional legacy intent
    SENSITIVE = "sensitive"  # Additional legacy intent
    
    @staticmethod
    def get_config(intent: 'Intent') -> IntentConfig:
        """Get configuration for intent (backward compatibility)"""
        # Map legacy intents to new system
        intent_mapping = {
            Intent.EPHEMERAL: BuiltInDataIntent.EPHEMERAL,
            Intent.STANDARD: BuiltInDataIntent.STANDARD,
            Intent.CRITICAL: BuiltInDataIntent.CRITICAL,
            Intent.LAZY: BuiltInDataIntent.EPHEMERAL,
            Intent.SENSITIVE: BuiltInDataIntent.CRITICAL
        }
        
        mapped_intent = intent_mapping.get(intent, BuiltInDataIntent.STANDARD)
        resolver = get_intent_resolver()
        return resolver.resolve_intent_config(mapped_intent)


class IntentRegistry:
    """
    Unified registry combining data and operation intents.
    
    Backward-compatible wrapper that integrates with new modular systems.
    Delegates to specialized registries internally while maintaining
    the same public interface.
    """
    
    def __init__(self):
        self._data_intent_registry = get_data_intent_registry()
        self._operation_intent_registry = get_operation_intent_registry()
        self._model_intents: dict[type[BaseModel], dict[str, Intent]] = {}
    
    def register_route_intent(self, path: str, method: str, intent: Intent = None, priority: str = "medium"):
        """Register route intent (backward compatibility)"""
        # Map to operation intent if provided
        if intent:
            try:
                op_intent = OperationIntent(intent.value)
                self._operation_intent_registry.register_endpoint_intent(
                    path, method, op_intent
                )
            except ValueError:
                # Not a valid operation intent, treat as data intent context
                pass
        
        # Store for backward compatibility
        route_key = f"{method.upper()} {path}"
        if not hasattr(self, '_route_intents'):
            self._route_intents = {}
        self._route_intents[route_key] = {
            "intent": intent,
            "priority": priority
        }
    
    def get_route_intent(self, path: str, method: str) -> dict[str, Any]:
        """Get route intent information"""
        route_key = f"{method.upper()} {path}"
        
        # Check backward compatibility storage first
        if hasattr(self, '_route_intents') and route_key in self._route_intents:
            return self._route_intents[route_key]
        
        # Check operation intent registry
        op_intent = self._operation_intent_registry.get_endpoint_intent(path, method)
        if op_intent:
            return op_intent
        
        return {}
    
    def register_model_intents(self, model_type: type[BaseModel], field_intents: dict[str, Intent]):
        """Register model field intents"""
        self._model_intents[model_type] = field_intents
    
    def get_model_intents(self, model_type: type[BaseModel]) -> dict[str, Intent]:
        """Get model field intents"""
        return self._model_intents.get(model_type, {})


# Global intent registry instance (backward compatibility)
_legacy_intent_registry = IntentRegistry()


def get_intent_registry() -> IntentRegistry:
    """
    Get the global intent registry instance.
    
    Returns:
        The global IntentRegistry instance (backward compatible wrapper)
    """
    return _legacy_intent_registry


def extract_intents(model: type[BaseModel]) -> dict[str, Union[Intent, BuiltInDataIntent, str, BaseIntentConfig, IntentMarker]]:
    """
    Extract intents from a Pydantic model's field metadata.
    
    Enhanced version that prioritizes modern Annotated-based intents while maintaining
    backward compatibility with legacy json_schema_extra approach.
    
    Args:
        model: The Pydantic model class to extract intents from
        
    Returns:
        Dictionary mapping field names to their declared intents
    """
    field_intents = {}
    resolver = get_intent_resolver()
    
    # First, try to extract from Annotated type hints (new system - preferred)
    annotated_intents = extract_annotated_intents(model)
    field_intents.update(annotated_intents)
    
    # Then, fall back to legacy json_schema_extra for backward compatibility
    for field_name, field_info in model.model_fields.items():
        # Skip if intent already found via Annotated
        if field_name in field_intents:
            continue
            
        intent_declared = None
        
        # Check for intent in json_schema_extra (legacy support)
        if hasattr(field_info, 'json_schema_extra') and field_info.json_schema_extra:
            schema_extra = field_info.json_schema_extra
            if isinstance(schema_extra, dict):
                # Check for intent (legacy)
                if 'intent' in schema_extra:
                    intent_declared = schema_extra['intent']
                # Check for inline config
                elif 'intent_config' in schema_extra:
                    # Handle inline configuration
                    config = schema_extra['intent_config']
                    if isinstance(config, dict):
                        resolved_config = resolver.resolve_intent_config(config)
                        # Store the resolved intent for this field
                        field_intents[field_name] = resolved_config
                        continue
        
        # Also check older Pydantic extra attribute
        elif hasattr(field_info, 'extra') and isinstance(field_info.extra, dict):
            extra = field_info.extra
            if 'intent' in extra:
                intent_declared = extra['intent']
        
        # Process declared intent (legacy)
        if intent_declared is not None:
            # Try to map legacy intent to new marker
            legacy_marker = map_legacy_intent_to_marker(intent_declared)
            if legacy_marker:
                field_intents[field_name] = legacy_marker
            elif isinstance(intent_declared, (Intent, BuiltInDataIntent)):
                field_intents[field_name] = intent_declared
            elif isinstance(intent_declared, str):
                # Try to map to built-in intent first
                try:
                    field_intents[field_name] = BuiltInDataIntent(intent_declared.lower())
                except ValueError:
                    # Treat as custom intent name
                    field_intents[field_name] = intent_declared
            elif isinstance(intent_declared, dict):
                # Inline configuration
                resolved_config = resolver.resolve_intent_config(intent_declared)
                field_intents[field_name] = resolved_config
    
    # Register the extracted intents in the global registry
    get_intent_registry().register_model_intents(model, field_intents)
    
    return field_intents


def get_intent_config(model: type[BaseModel], field_name: str) -> Optional[BaseIntentConfig]:
    """
    Get the intent configuration for a specific field in a model.
    
    Enhanced version supporting both legacy and new intent systems including Annotated markers.
    
    Args:
        model: The Pydantic model class
        field_name: The name of the field
        
    Returns:
        BaseIntentConfig for the field, or None if no intent is declared
    """
    intent = get_field_intent(model, field_name)
    if intent:
        resolver = get_intent_resolver()
        return resolver.resolve_intent_config(intent)
    return None


def get_field_intent(model: type[BaseModel], field_name: str) -> Union[Intent, BuiltInDataIntent, str, BaseIntentConfig, IntentMarker, None]:
    """
    Get the intent for a specific field in a model.
    
    Args:
        model: The Pydantic model class
        field_name: The name of the field
        
    Returns:
        The intent for the field (could be Intent, BuiltInDataIntent, str, BaseIntentConfig, IntentMarker, or None)
    """
    intents = extract_intents(model)
    return intents.get(field_name)


def model_intent_score(model: type[BaseModel]) -> float:
    """
    Calculate an intent importance score for a model based on its fields.
    
    Enhanced version that works with both legacy and new intent systems including Annotated markers.
    
    Args:
        model: The Pydantic model class
        
    Returns:
        A numerical score representing the overall importance of the model
    """
    intents = extract_intents(model)
    resolver = get_intent_resolver()

    score = 0.0
    for field_intent in intents.values():
        if isinstance(field_intent, (Intent, BuiltInDataIntent)):
            # Map to weights
            weight_mapping = {
                BuiltInDataIntent.CRITICAL: 10.0,
                BuiltInDataIntent.STANDARD: 5.0, 
                BuiltInDataIntent.EPHEMERAL: 1.0,
                Intent.CRITICAL: 10.0,
                Intent.STANDARD: 5.0,
                Intent.EPHEMERAL: 1.0
            }
            score += weight_mapping.get(field_intent, 1.0)
        elif isinstance(field_intent, (BaseIntentConfig, IntentMarker)):
            # Score based on config properties
            config_score = 1.0
            if hasattr(field_intent, 'strong_consistency') and field_intent.strong_consistency:
                config_score += 5.0
            if hasattr(field_intent, 'encrypt') and field_intent.encrypt:
                config_score += 5.0
            if hasattr(field_intent, 'audit_logging') and field_intent.audit_logging:
                config_score += 3.0
            if hasattr(field_intent, 'emergency_buffer') and field_intent.emergency_buffer:
                config_score += 2.0
            score += config_score
        else:
            # Custom intent or string
            score += 1.0
    
    return score