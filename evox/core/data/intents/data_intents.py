"""
Data Intent System - Field/Model Level Intent Processing
========================================================

Provides a clean, modular system for declaring data intents at field/model level
using modern Python 3.13+ Annotated syntax. Maintains backward compatibility
with legacy json_schema_extra approach.

Core Components:
- BuiltInDataIntent: Standard intent levels (EPHEMERAL, STANDARD, CRITICAL)
- BaseIntentConfig: Base configuration class for all intents
- CustomIntentConfig: Extends BaseIntentConfig for custom intents
- DataIntentRegistry: Central registry for custom intent definitions
- IntentResolver: Composes behaviors from configurations
- Annotated support: Modern typing.Annotated-based intent declarations
"""

from enum import Enum
from typing import Any, Dict, Optional, Union, get_type_hints
from dataclasses import dataclass, field
from datetime import timedelta
from pydantic import BaseModel
import json

# Import new Annotated system
from .annotated_intents import (
    IntentMarker, Critical, Standard, Ephemeral,
    critical, standard, ephemeral, custom_intent,
    extract_annotated_intents, get_intent_from_annotation,
    map_legacy_intent_to_marker
)


@dataclass
class BaseIntentConfig:
    """
    Base configuration for all data intents.
    
    Provides sensible defaults that can be overridden by specific intent types.
    Uses composition over inheritance for maximum flexibility.
    """
    # Caching properties
    cache_enabled: bool = True
    cache_ttl: Optional[timedelta] = None
    cache_aggressive: bool = False
    
    # Encryption properties  
    encrypt: bool = False
    
    # Consistency properties
    strong_consistency: bool = False
    replication_required: bool = False
    
    # Audit properties
    audit_logging: bool = False
    
    # Priority properties
    task_priority: str = "normal"
    message_priority: str = "normal"
    
    # Fallback properties
    fallback_enabled: bool = True
    emergency_buffer: bool = False
    
    # Custom properties for extension
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default TTL based on caching strategy"""
        if self.cache_enabled and self.cache_ttl is None:
            if self.cache_aggressive:
                self.cache_ttl = timedelta(minutes=5)
            else:
                self.cache_ttl = timedelta(hours=1)


@dataclass  
class CustomIntentConfig(BaseIntentConfig):
    """
    Custom intent configuration that extends BaseIntentConfig.
    
    Allows arbitrary string intent names with custom configurations.
    Inherits all base properties and adds custom extension capabilities.
    """
    # Custom intent name
    intent_name: str = ""
    
    # Validation rules
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    
    # Processing hooks
    pre_process_hooks: list = field(default_factory=list)
    post_process_hooks: list = field(default_factory=list)


class BuiltInDataIntent(str, Enum):
    """
    Built-in data intent levels for standard use cases.
    
    Each intent provides predefined behavior for common scenarios.
    """
    EPHEMERAL = "ephemeral"
    """Aggressive caching, short TTL, no persistence, low priority"""
    
    STANDARD = "standard" 
    """Balanced caching, normal priority, optional features"""
    
    CRITICAL = "critical"
    """Strong consistency, mandatory encryption, replication, audit logging"""


class DataIntentRegistry:
    """
    Registry for custom data intent definitions.
    
    Manages custom intent configurations and provides lookup capabilities.
    Thread-safe singleton pattern for global access.
    """
    
    _instance = None
    _custom_intents: Dict[str, CustomIntentConfig] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'DataIntentRegistry':
        """Get the singleton instance"""
        return cls()
    
    def register_custom_intent(self, intent_name: str, config: CustomIntentConfig):
        """Register a custom intent configuration"""
        config.intent_name = intent_name
        self._custom_intents[intent_name] = config
    
    def get_custom_intent(self, intent_name: str) -> Optional[CustomIntentConfig]:
        """Get a custom intent configuration by name"""
        return self._custom_intents.get(intent_name)
    
    def get_all_custom_intents(self) -> Dict[str, CustomIntentConfig]:
        """Get all registered custom intents"""
        return self._custom_intents.copy()
    
    def unregister_custom_intent(self, intent_name: str):
        """Remove a custom intent from registry"""
        self._custom_intents.pop(intent_name, None)


class IntentResolver:
    """
    Central intent resolver that composes behaviors from configurations.
    
    Single point of truth for mapping intents to actual framework behaviors.
    Eliminates code duplication by centralizing all intent processing logic.
    """
    
    def __init__(self):
        self.registry = DataIntentRegistry.get_instance()
    
    def resolve_intent_config(self, intent: Union[BuiltInDataIntent, str, Dict, IntentMarker]) -> BaseIntentConfig:
        """
        Resolve intent to configuration, handling built-in, custom, inline configs, and annotated markers.
        
        Args:
            intent: Built-in intent enum, custom intent string, inline config dict, or IntentMarker
            
        Returns:
            BaseIntentConfig with resolved settings
        """
        if isinstance(intent, IntentMarker):
            # Convert IntentMarker to BaseIntentConfig
            return BaseIntentConfig(
                cache_enabled=intent.cache_enabled,
                cache_ttl=intent.cache_ttl,
                cache_aggressive=intent.cache_aggressive,
                encrypt=intent.encrypt,
                strong_consistency=intent.strong_consistency,
                replication_required=intent.replication_required,
                audit_logging=intent.audit_logging,
                task_priority=intent.task_priority,
                message_priority=intent.message_priority,
                fallback_enabled=intent.fallback_enabled,
                emergency_buffer=intent.emergency_buffer,
                custom_properties=intent.custom_properties
            )
        elif isinstance(intent, BuiltInDataIntent):
            return self._get_builtin_config(intent)
        elif isinstance(intent, str):
            # Check for custom intent
            custom_config = self.registry.get_custom_intent(intent)
            if custom_config:
                return custom_config
            # Fall back to built-in if matches
            try:
                builtin_intent = BuiltInDataIntent(intent.lower())
                return self._get_builtin_config(builtin_intent)
            except ValueError:
                # Return default config for unknown string intents
                return BaseIntentConfig()
        elif isinstance(intent, dict):
            # Inline configuration
            return self._create_inline_config(intent)
        else:
            return BaseIntentConfig()
    
    def _get_builtin_config(self, intent: BuiltInDataIntent) -> BaseIntentConfig:
        """Get configuration for built-in intents"""
        configs = {
            BuiltInDataIntent.EPHEMERAL: BaseIntentConfig(
                cache_enabled=True,
                cache_ttl=timedelta(minutes=5),
                cache_aggressive=True,
                encrypt=False,
                strong_consistency=False,
                replication_required=False,
                audit_logging=False,
                task_priority="low",
                message_priority="low",
                fallback_enabled=False,
                emergency_buffer=False
            ),
            BuiltInDataIntent.STANDARD: BaseIntentConfig(
                cache_enabled=True,
                cache_ttl=timedelta(hours=1),
                cache_aggressive=False,
                encrypt=False,
                strong_consistency=False,
                replication_required=False,
                audit_logging=False,
                task_priority="normal",
                message_priority="normal",
                fallback_enabled=True,
                emergency_buffer=False
            ),
            BuiltInDataIntent.CRITICAL: BaseIntentConfig(
                cache_enabled=True,
                cache_ttl=timedelta(minutes=30),
                cache_aggressive=False,
                encrypt=True,
                strong_consistency=True,
                replication_required=True,
                audit_logging=True,
                task_priority="high",
                message_priority="high",
                fallback_enabled=True,
                emergency_buffer=True
            )
        }
        return configs.get(intent, configs[BuiltInDataIntent.STANDARD])
    
    def _create_inline_config(self, config_dict: Dict) -> BaseIntentConfig:
        """Create configuration from inline dictionary"""
        # Extract known properties
        base_props = {
            k: v for k, v in config_dict.items() 
            if k in BaseIntentConfig.__dataclass_fields__
        }
        
        # Extract custom properties
        custom_props = {
            k: v for k, v in config_dict.items()
            if k not in BaseIntentConfig.__dataclass_fields__
        }
        
        config = BaseIntentConfig(**base_props)
        config.custom_properties.update(custom_props)
        return config
    
    def apply_to_feature(self, config: BaseIntentConfig, feature: str) -> Dict[str, Any]:
        """
        Apply intent configuration to a specific framework feature.
        
        Args:
            config: The resolved intent configuration
            feature: Feature name ('cache', 'encryption', 'consistency', etc.)
            
        Returns:
            Feature-specific configuration derived from intent
        """
        feature_configs = {
            'cache': {
                'enabled': config.cache_enabled,
                'ttl': config.cache_ttl,
                'aggressive': config.cache_aggressive
            },
            'encryption': {
                'enabled': config.encrypt
            },
            'consistency': {
                'strong': config.strong_consistency,
                'replication': config.replication_required
            },
            'audit': {
                'logging': config.audit_logging
            },
            'priority': {
                'task': config.task_priority,
                'message': config.message_priority
            },
            'fallback': {
                'enabled': config.fallback_enabled,
                'emergency_buffer': config.emergency_buffer
            }
        }
        
        return feature_configs.get(feature, {})


# Global instances for easy access
_data_intent_registry = DataIntentRegistry()
_intent_resolver = IntentResolver()


def get_data_intent_registry() -> DataIntentRegistry:
    """Get the global data intent registry"""
    return _data_intent_registry


def get_intent_resolver() -> IntentResolver:
    """Get the global intent resolver"""
    return _intent_resolver


def register_custom_data_intent(intent_name: str, config: CustomIntentConfig):
    """Convenience function to register custom data intents"""
    _data_intent_registry.register_custom_intent(intent_name, config)


def resolve_data_intent(intent: Union[BuiltInDataIntent, str, Dict, IntentMarker]) -> BaseIntentConfig:
    """Convenience function to resolve any intent to configuration"""
    return _intent_resolver.resolve_intent_config(intent)