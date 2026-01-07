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

from typing import Any, Type, TypeVar, Dict, Callable, Optional, Union, get_type_hints
from dataclasses import dataclass
import logging
from datetime import datetime

from pydantic import BaseModel
from typing import Annotated

# Import intent system for database-aware mapping
from ..data.intents.annotated_intents import get_intent_from_annotation, IntentMarker

T = TypeVar('T')
logger = logging.getLogger(__name__)


@dataclass
class APIMappingRule:
    """Defines mapping rules for API ↔ Core transformations with database awareness"""
    api_field: str
    core_field: str
    api_to_core_transformer: Optional[Callable] = None
    core_to_api_transformer: Optional[Callable] = None
    required: bool = True
    
    # DATABASE TRANSFORMATION EXTENSIONS
    # Intent-aware database operations
    database_transformer: Optional[Callable] = None
    encryption_required: bool = False
    masking_required: bool = False
    
    # Database field properties
    database_column: Optional[str] = None
    index_required: bool = False
    unique_constraint: bool = False
    
    # Query optimization hints
    query_hint: Optional[str] = None
    partition_key: Optional[str] = None


class CoreModelMapper:
    """Bidirectional model mapper for API ↔ Core conversions with database awareness"""
    
    def __init__(self):
        self._api_to_core_rules: Dict[str, Dict[str, APIMappingRule]] = {}
        self._core_to_api_rules: Dict[str, Dict[str, APIMappingRule]] = {}
        self._custom_mappers: Dict[str, Dict[str, Callable]] = {
            'api_to_core': {},
            'core_to_api': {}
        }
        
        # DATABASE-AWARE EXTENSIONS
        self._database_transformers: Dict[str, Dict[str, Callable]] = {
            'encrypt': {},
            'decrypt': {},
            'mask': {},
            'unmask': {}
        }
        self._intent_processors: Dict[str, Callable] = {}
        self._query_optimizers: Dict[str, Callable] = {}
    
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
    
    def register_database_transformer(
        self,
        field_name: str,
        encrypt_func: Optional[Callable] = None,
        decrypt_func: Optional[Callable] = None,
        mask_func: Optional[Callable] = None,
        unmask_func: Optional[Callable] = None
    ):
        """
        Register database transformation functions for sensitive fields.
        
        Args:
            field_name: Name of the field to transform
            encrypt_func: Function to encrypt data before storage
            decrypt_func: Function to decrypt data after retrieval
            mask_func: Function to mask data for display
            unmask_func: Function to unmask data for processing
        """
        if encrypt_func:
            self._database_transformers['encrypt'][field_name] = encrypt_func
        if decrypt_func:
            self._database_transformers['decrypt'][field_name] = decrypt_func
        if mask_func:
            self._database_transformers['mask'][field_name] = mask_func
        if unmask_func:
            self._database_transformers['unmask'][field_name] = unmask_func
        
        logger.info(f"Registered database transformers for field: {field_name}")
    
    def register_intent_processor(
        self,
        intent_type: str,
        processor_func: Callable
    ):
        """
        Register intent-aware processors for database operations.
        
        Args:
            intent_type: Type of intent (e.g., "CRITICAL", "CACHE")
            processor_func: Function to process data based on intent
        """
        self._intent_processors[intent_type] = processor_func
        logger.info(f"Registered intent processor for: {intent_type}")
    
    def register_query_optimizer(
        self,
        model_type: Type,
        optimizer_func: Callable
    ):
        """
        Register query optimization functions for specific models.
        
        Args:
            model_type: Model class to optimize queries for
            optimizer_func: Function to optimize database queries
        """
        model_key = model_type.__name__
        self._query_optimizers[model_key] = optimizer_func
        logger.info(f"Registered query optimizer for model: {model_key}")
    
    def apply_database_transformations(
        self,
        obj: Any,
        model_type: Type,
        operation: str = "read"
    ) -> Any:
        """
        Apply database-aware transformations based on field intents.
        
        Args:
            obj: Object to transform
            model_type: Type of the model
            operation: Operation type ("read", "write", "display")
            
        Returns:
            Transformed object with appropriate database operations applied
        """
        if not hasattr(obj, '__dict__'):
            return obj
        
        # Get field annotations to check for intents
        field_annotations = get_type_hints(model_type)
        
        transformed_obj = obj.__class__() if hasattr(obj, '__class__') else {}
        
        for field_name, value in obj.__dict__.items():
            # Check if field has intent annotation
            if field_name in field_annotations:
                annotation = field_annotations[field_name]
                intent_marker = get_intent_from_annotation(annotation)
                
                if intent_marker:
                    # Apply intent-specific transformations
                    transformed_value = self._apply_intent_transformations(
                        field_name, value, intent_marker, operation
                    )
                    setattr(transformed_obj, field_name, transformed_value)
                else:
                    setattr(transformed_obj, field_name, value)
            else:
                setattr(transformed_obj, field_name, value)
        
        return transformed_obj
    
    def _apply_intent_transformations(
        self,
        field_name: str,
        value: Any,
        intent_marker: IntentMarker,
        operation: str
    ) -> Any:
        """
        Apply transformations based on intent marker.
        
        Args:
            field_name: Name of the field
            value: Field value
            intent_marker: Intent marker for the field
            operation: Operation being performed
            
        Returns:
            Transformed value
        """
        transformed_value = value
        
        # Apply encryption for critical/sensitive data
        if intent_marker.encrypt and operation == "write":
            encrypt_func = self._database_transformers['encrypt'].get(field_name)
            if encrypt_func:
                transformed_value = encrypt_func(transformed_value)
            
        # Apply decryption for critical/sensitive data
        elif intent_marker.encrypt and operation == "read":
            decrypt_func = self._database_transformers['decrypt'].get(field_name)
            if decrypt_func:
                transformed_value = decrypt_func(transformed_value)
            
        # Apply masking for display operations
        elif intent_marker.encrypt and operation == "display":
            mask_func = self._database_transformers['mask'].get(field_name)
            if mask_func:
                transformed_value = mask_func(transformed_value)
            
        # Apply intent-specific processors
        if intent_marker.name in self._intent_processors:
            processor = self._intent_processors[intent_marker.name]
            transformed_value = processor(transformed_value, operation)
            
        return transformed_value
    
    def generate_database_schema(
        self,
        model_type: Type[BaseModel]
    ) -> Dict[str, Any]:
        """
        Generate database schema based on model annotations and intents.
        
        Args:
            model_type: Pydantic model class
            
        Returns:
            Dictionary representing database schema with intent-aware properties
        """
        schema = {
            "table_name": model_type.__name__.lower() + "s",
            "columns": {},
            "indexes": [],
            "constraints": []
        }
        
        field_annotations = get_type_hints(model_type)
        
        for field_name, field_info in model_type.model_fields.items():
            column_def = {
                "name": field_name,
                "type": self._get_database_type(field_info.annotation),
                "nullable": field_info.is_required() == False,
                "primary_key": field_name == "id"
            }
            
            # Check for intent annotations
            if field_name in field_annotations:
                annotation = field_annotations[field_name]
                intent_marker = get_intent_from_annotation(annotation)
                
                if intent_marker:
                    # Add intent-specific database properties
                    if intent_marker.unique_constraint:
                        column_def["unique"] = True
                        schema["constraints"].append({
                            "type": "unique",
                            "columns": [field_name]
                        })
                    
                    if intent_marker.index_required:
                        schema["indexes"].append({
                            "name": f"idx_{field_name}",
                            "columns": [field_name]
                        })
                    
                    if intent_marker.encrypt:
                        column_def["encrypted"] = True
                    
                    if intent_marker.partition_key:
                        column_def["partition_key"] = intent_marker.partition_key
            
            schema["columns"][field_name] = column_def
        
        return schema
    
    def _get_database_type(self, annotation) -> str:
        """
        Map Python type annotations to database types.
        
        Args:
            annotation: Type annotation
            
        Returns:
            Database type string
        """
        # Handle Annotated types
        if hasattr(annotation, '__origin__') and annotation.__origin__ is Annotated:
            base_type = annotation.__args__[0]
            return self._get_database_type(base_type)
        
        # Map basic types
        type_mapping = {
            int: "INTEGER",
            str: "VARCHAR",
            float: "FLOAT",
            bool: "BOOLEAN",
            datetime: "TIMESTAMP",
            bytes: "BLOB"
        }
        
        # Handle Optional types
        if hasattr(annotation, '__origin__') and annotation.__origin__ is Union:
            args = annotation.__args__
            non_none_types = [arg for arg in args if arg is not type(None)]
            if non_none_types:
                return self._get_database_type(non_none_types[0])
        
        return type_mapping.get(annotation, "TEXT")
    
    def optimize_query(
        self,
        model_type: Type,
        query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize database queries based on model and parameters.
        
        Args:
            model_type: Model class
            query_params: Query parameters
            
        Returns:
            Optimized query parameters
        """
        model_key = model_type.__name__
        
        if model_key in self._query_optimizers:
            optimizer = self._query_optimizers[model_key]
            return optimizer(query_params)
        
        # Default optimizations
        optimized = query_params.copy()
        
        # Add pagination if not present
        if "limit" not in optimized:
            optimized["limit"] = 100
        
        # Add sorting for better performance
        if "order_by" not in optimized:
            optimized["order_by"] = "id"
            
        return optimized
    
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

# DATABASE-AWARE MAPPING FUNCTIONS
def register_database_transformer(
    field_name: str,
    encrypt_func: Optional[Callable] = None,
    decrypt_func: Optional[Callable] = None,
    mask_func: Optional[Callable] = None,
    unmask_func: Optional[Callable] = None
):
    """Register database transformation functions for sensitive fields"""
    model_mapper.register_database_transformer(
        field_name, encrypt_func, decrypt_func, mask_func, unmask_func
    )


def register_intent_processor(intent_type: str, processor_func: Callable):
    """Register intent-aware processors for database operations"""
    model_mapper.register_intent_processor(intent_type, processor_func)


def register_query_optimizer(model_type: Type, optimizer_func: Callable):
    """Register query optimization functions for specific models"""
    model_mapper.register_query_optimizer(model_type, optimizer_func)


def apply_database_transformations(obj: Any, model_type: Type, operation: str = "read") -> Any:
    """Apply database-aware transformations based on field intents"""
    return model_mapper.apply_database_transformations(obj, model_type, operation)


def generate_database_schema(model_type: Type[BaseModel]) -> Dict[str, Any]:
    """Generate database schema based on model annotations and intents"""
    return model_mapper.generate_database_schema(model_type)


def optimize_query(model_type: Type, query_params: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize database queries based on model and parameters"""
    return model_mapper.optimize_query(model_type, query_params)


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
    "register_mapping",
    # DATABASE-AWARE FUNCTIONS
    "register_database_transformer",
    "register_intent_processor",
    "register_query_optimizer",
    "apply_database_transformations",
    "generate_database_schema",
    "optimize_query"
]