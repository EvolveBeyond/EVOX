"""
Automatic Model Mapping System for EVOX
Maps between API models and core models with validation and transformation.
"""

from typing import Any, Type, TypeVar, Dict, Callable, Optional, Union
import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, ValidationError
from ..models.core_models import CoreMessage, CoreResponse

T = TypeVar('T')
logger = logging.getLogger(__name__)

class MappingDirection(Enum):
    """Direction of model mapping"""
    API_TO_CORE = "api_to_core"
    CORE_TO_API = "core_to_api"
    BIDIRECTIONAL = "bidirectional"

@dataclass
class MappingRule:
    """Defines a mapping rule between models"""
    source_field: str
    target_field: str
    transformer: Optional[Callable] = None
    validator: Optional[Callable] = None
    required: bool = True

class ModelMapper:
    """Automatic model mapping system with validation and transformation"""
    
    def __init__(self):
        self._mapping_rules: Dict[str, Dict[str, MappingRule]] = {}
        self._custom_mappers: Dict[str, Callable] = {}
        self.stats = {
            "mappings_processed": 0,
            "successful_mappings": 0,
            "failed_mappings": 0,
            "validation_errors": 0
        }
    
    def register_mapping(
        self,
        source_model: Type,
        target_model: Type,
        rules: Optional[Dict[str, MappingRule]] = None,
        direction: MappingDirection = MappingDirection.BIDIRECTIONAL
    ):
        """Register mapping rules between two models"""
        source_key = f"{source_model.__name__}_{target_model.__name__}"
        
        if rules is None:
            # Auto-generate rules based on field names
            rules = self._auto_generate_rules(source_model, target_model)
        
        self._mapping_rules[source_key] = rules
        logger.info(f"Registered mapping: {source_model.__name__} → {target_model.__name__}")
    
    def register_custom_mapper(
        self,
        source_model: Type,
        target_model: Type,
        mapper_func: Callable
    ):
        """Register a custom mapping function"""
        key = f"{source_model.__name__}_{target_model.__name__}"
        self._custom_mappers[key] = mapper_func
        logger.info(f"Registered custom mapper: {source_model.__name__} → {target_model.__name__}")
    
    def map_model(
        self,
        source_obj: Any,
        target_model: Type[T],
        source_model: Optional[Type] = None
    ) -> T:
        """Map source object to target model"""
        try:
            self.stats["mappings_processed"] += 1
            
            # Determine source model if not provided
            if source_model is None:
                source_model = type(source_obj)
            
            # Check for custom mapper
            custom_key = f"{source_model.__name__}_{target_model.__name__}"
            if custom_key in self._custom_mappers:
                result = self._custom_mappers[custom_key](source_obj)
                self.stats["successful_mappings"] += 1
                return result
            
            # Apply standard mapping rules
            mapped_data = self._apply_mapping_rules(source_obj, source_model, target_model)
            
            # Validate and create target object
            if issubclass(target_model, BaseModel):
                result = target_model(**mapped_data)
            else:
                # For dataclasses or regular classes
                result = target_model(**mapped_data)
            
            self.stats["successful_mappings"] += 1
            return result
            
        except ValidationError as e:
            self.stats["validation_errors"] += 1
            logger.error(f"Validation error in model mapping: {e}")
            raise
        except Exception as e:
            self.stats["failed_mappings"] += 1
            logger.error(f"Model mapping failed: {e}")
            raise
    
    def _auto_generate_rules(
        self,
        source_model: Type,
        target_model: Type
    ) -> Dict[str, MappingRule]:
        """Auto-generate mapping rules based on field compatibility"""
        rules = {}
        
        # Get fields from both models
        source_fields = self._get_model_fields(source_model)
        target_fields = self._get_model_fields(target_model)
        
        # Match fields by name
        for field_name in source_fields:
            if field_name in target_fields:
                rules[field_name] = MappingRule(
                    source_field=field_name,
                    target_field=field_name
                )
        
        return rules
    
    def _get_model_fields(self, model: Type) -> set:
        """Extract field names from model"""
        if issubclass(model, BaseModel):
            return set(model.model_fields.keys())
        elif hasattr(model, '__dataclass_fields__'):
            return set(model.__dataclass_fields__.keys())
        else:
            # Fallback to __annotations__
            return set(getattr(model, '__annotations__', {}).keys())
    
    def _apply_mapping_rules(
        self,
        source_obj: Any,
        source_model: Type,
        target_model: Type
    ) -> Dict[str, Any]:
        """Apply registered mapping rules to transform data"""
        result = {}
        
        # Get mapping rules
        rules_key = f"{source_model.__name__}_{target_model.__name__}"
        rules = self._mapping_rules.get(rules_key, {})
        
        # Apply each rule
        for rule_name, rule in rules.items():
            try:
                # Extract source value
                if hasattr(source_obj, rule.source_field):
                    value = getattr(source_obj, rule.source_field)
                elif isinstance(source_obj, dict) and rule.source_field in source_obj:
                    value = source_obj[rule.source_field]
                else:
                    if rule.required:
                        raise ValueError(f"Required field '{rule.source_field}' not found")
                    continue
                
                # Apply transformer if provided
                if rule.transformer:
                    value = rule.transformer(value)
                
                # Apply validator if provided
                if rule.validator and not rule.validator(value):
                    raise ValueError(f"Validation failed for field '{rule.target_field}'")
                
                # Set target value
                result[rule.target_field] = value
                
            except Exception as e:
                logger.warning(f"Mapping rule '{rule_name}' failed: {e}")
                if rule.required:
                    raise
        
        return result

# Global mapper instance
model_mapper = ModelMapper()

def map_models(source_obj: Any, target_model: Type[T], source_model: Optional[Type] = None) -> T:
    """Convenience function for model mapping"""
    return model_mapper.map_model(source_obj, target_model, source_model)

# Additional convenience functions for compatibility

def register_mapper(api_model: Type, core_model: Type):
    """Register a mapping between API and core models"""
    model_mapper.register_mapping(api_model, core_model)

def get_mapper():
    """Get the global mapper instance"""
    return model_mapper

def map_api_to_core(api_obj: Any, core_model: Type[T]) -> T:
    """Map API object to core model"""
    return model_mapper.map_model(api_obj, core_model)

def map_core_to_api(core_obj: Any, api_model: Type[T]) -> T:
    """Map core object to API model"""
    return model_mapper.map_model(core_obj, api_model)

# Export public API
__all__ = [
    "ModelMapper",
    "MappingRule",
    "MappingDirection",
    "model_mapper",
    "map_models",
    "register_mapper",
    "get_mapper",
    "map_api_to_core",
    "map_core_to_api"
]