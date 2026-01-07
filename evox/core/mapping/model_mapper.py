"""
EVOX Core Model Mapper
======================

Lightweight API ↔ Core model mapping system for the EVOX framework.
Handles bidirectional mapping between external API models and internal core models.

This module provides:
- API to Core mapping (external interface to internal representation)
- Core to API mapping (internal representation to external interface)
- Automatic field mapping with type conversion
- Custom mapping rules support
"""

from typing import Any, Type, TypeVar, Dict, Callable, Optional, Union
from dataclasses import dataclass
import logging
from datetime import datetime

from pydantic import BaseModel

T = TypeVar('T')
logger = logging.getLogger(__name__)


@dataclass
class APIMappingRule:
    """Defines mapping rules for API ↔ Core transformations"""
    api_field: str
    core_field: str
    api_to_core_transformer: Optional[Callable] = None
    core_to_api_transformer: Optional[Callable] = None
    required: bool = True


class CoreModelMapper:
    """Bidirectional model mapper for API ↔ Core conversions"""
    
    def __init__(self):
        self._api_to_core_rules: Dict[str, Dict[str, APIMappingRule]] = {}
        self._core_to_api_rules: Dict[str, Dict[str, APIMappingRule]] = {}
        self._custom_mappers: Dict[str, Dict[str, Callable]] = {
            'api_to_core': {},
            'core_to_api': {}
        }
    
    def register_api_core_mapping(
        self,
        api_model: Type,
        core_model: Type,
        rules: Optional[Dict[str, APIMappingRule]] = None
    ):
        """
        Register bidirectional mapping between API and Core models.
        
        Args:
            api_model: External API model class
            core_model: Internal core model class
            rules: Custom mapping rules (auto-generated if None)
        """
        mapping_key = f"{api_model.__name__}_{core_model.__name__}"
        
        if rules is None:
            rules = self._auto_generate_api_core_rules(api_model, core_model)
        
        # Store rules for both directions
        self._api_to_core_rules[mapping_key] = rules
        self._core_to_api_rules[mapping_key] = rules
        
        logger.info(f"Registered API↔Core mapping: {api_model.__name__} ↔ {core_model.__name__}")
    
    def register_custom_mapper(
        self,
        api_model: Type,
        core_model: Type,
        api_to_core_func: Callable,
        core_to_api_func: Callable
    ):
        """Register custom bidirectional mapping functions"""
        key = f"{api_model.__name__}_{core_model.__name__}"
        self._custom_mappers['api_to_core'][key] = api_to_core_func
        self._custom_mappers['core_to_api'][key] = core_to_api_func
        logger.info(f"Registered custom API↔Core mappers: {api_model.__name__} ↔ {core_model.__name__}")
    
    def map_api_to_core(self, api_obj: Any, core_model: Type[T]) -> T:
        """Map API object to Core model"""
        try:
            api_model = type(api_obj)
            mapping_key = f"{api_model.__name__}_{core_model.__name__}"
            
            # Check for custom mapper
            if mapping_key in self._custom_mappers['api_to_core']:
                return self._custom_mappers['api_to_core'][mapping_key](api_obj)
            
            # Apply standard mapping rules
            mapped_data = self._apply_api_to_core_mapping(api_obj, api_model, core_model)
            
            # Create core model instance
            if issubclass(core_model, BaseModel):
                return core_model(**mapped_data)
            else:
                return core_model(**mapped_data)
                
        except Exception as e:
            logger.error(f"API to Core mapping failed: {e}")
            raise
    
    def map_core_to_api(self, core_obj: Any, api_model: Type[T]) -> T:
        """Map Core object to API model"""
        try:
            core_model = type(core_obj)
            mapping_key = f"{core_model.__name__}_{api_model.__name__}"
            
            # Check for custom mapper
            if mapping_key in self._custom_mappers['core_to_api']:
                return self._custom_mappers['core_to_api'][mapping_key](core_obj)
            
            # Apply standard mapping rules
            mapped_data = self._apply_core_to_api_mapping(core_obj, core_model, api_model)
            
            # Create API model instance
            if issubclass(api_model, BaseModel):
                return api_model(**mapped_data)
            else:
                return api_model(**mapped_data)
                
        except Exception as e:
            logger.error(f"Core to API mapping failed: {e}")
            raise
    
    def _auto_generate_api_core_rules(
        self,
        api_model: Type,
        core_model: Type
    ) -> Dict[str, APIMappingRule]:
        """Auto-generate mapping rules based on field compatibility"""
        rules = {}
        
        api_fields = self._get_model_fields(api_model)
        core_fields = self._get_model_fields(core_model)
        
        # Create bidirectional mappings for matching fields
        for field_name in api_fields:
            if field_name in core_fields:
                rules[field_name] = APIMappingRule(
                    api_field=field_name,
                    core_field=field_name
                )
        
        return rules
    
    def _get_model_fields(self, model: Type) -> set:
        """Extract field names from model"""
        if issubclass(model, BaseModel):
            return set(model.model_fields.keys())
        elif hasattr(model, '__dataclass_fields__'):
            return set(model.__dataclass_fields__.keys())
        else:
            return set(getattr(model, '__annotations__', {}).keys())
    
    def _apply_api_to_core_mapping(
        self,
        api_obj: Any,
        api_model: Type,
        core_model: Type
    ) -> Dict[str, Any]:
        """Apply API to Core mapping rules"""
        result = {}
        mapping_key = f"{api_model.__name__}_{core_model.__name__}"
        rules = self._api_to_core_rules.get(mapping_key, {})
        
        for rule_name, rule in rules.items():
            try:
                # Extract API value
                if hasattr(api_obj, rule.api_field):
                    value = getattr(api_obj, rule.api_field)
                elif isinstance(api_obj, dict) and rule.api_field in api_obj:
                    value = api_obj[rule.api_field]
                else:
                    if rule.required:
                        raise ValueError(f"Required field '{rule.api_field}' not found in API object")
                    continue
                
                # Apply transformer if provided
                if rule.api_to_core_transformer:
                    value = rule.api_to_core_transformer(value)
                
                # Set core value
                result[rule.core_field] = value
                
            except Exception as e:
                logger.warning(f"API to Core mapping rule '{rule_name}' failed: {e}")
                if rule.required:
                    raise
        
        return result
    
    def _apply_core_to_api_mapping(
        self,
        core_obj: Any,
        core_model: Type,
        api_model: Type
    ) -> Dict[str, Any]:
        """Apply Core to API mapping rules"""
        result = {}
        mapping_key = f"{core_model.__name__}_{api_model.__name__}"
        rules = self._core_to_api_rules.get(mapping_key, {})
        
        for rule_name, rule in rules.items():
            try:
                # Extract core value
                if hasattr(core_obj, rule.core_field):
                    value = getattr(core_obj, rule.core_field)
                elif isinstance(core_obj, dict) and rule.core_field in core_obj:
                    value = core_obj[rule.core_field]
                else:
                    if rule.required:
                        raise ValueError(f"Required field '{rule.core_field}' not found in Core object")
                    continue
                
                # Apply transformer if provided
                if rule.core_to_api_transformer:
                    value = rule.core_to_api_transformer(value)
                
                # Set API value
                result[rule.api_field] = value
                
            except Exception as e:
                logger.warning(f"Core to API mapping rule '{rule_name}' failed: {e}")
                if rule.required:
                    raise
        
        return result


# Global mapper instance
model_mapper = CoreModelMapper()


# Convenience functions
def map_api_to_core(api_obj: Any, core_model: Type[T]) -> T:
    """Map API object to Core model"""
    return model_mapper.map_api_to_core(api_obj, core_model)


def map_core_to_api(core_obj: Any, api_model: Type[T]) -> T:
    """Map Core object to API model"""
    return model_mapper.map_core_to_api(core_obj, api_model)


def register_mapper(
    api_model: Type,
    core_model: Type,
    rules: Optional[Dict[str, APIMappingRule]] = None
):
    """Register bidirectional mapping between API and Core models"""
    model_mapper.register_api_core_mapping(api_model, core_model, rules)


def get_mapper() -> CoreModelMapper:
    """Get the global model mapper instance"""
    return model_mapper


# Backward compatibility aliases
map_models = map_api_to_core
register_mapping = register_mapper


__all__ = [
    "CoreModelMapper",
    "APIMappingRule",
    "model_mapper",
    "map_api_to_core",
    "map_core_to_api",
    "register_mapper",
    "get_mapper",
    "map_models",
    "register_mapping"
]