"""
Intent definitions for EVOX framework - Data-Intent-Aware Architecture

This module defines the standard intent constants and utilities for extracting
intent metadata from Pydantic models. Intents allow developers to declare "what"
the data is for, so EVOX can later decide "how" to handle it.
"""

from enum import Enum
from typing import Any, get_origin, get_args
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo


class Intent(str, Enum):
    """
    Standard intent constants for EVOX framework.
    
    Rationale: These intents allow developers to declare the purpose and 
    importance of their data, enabling EVOX to make intelligent decisions
    about how to handle it (caching, encryption, fallbacks, etc.).
    """
    CRITICAL = "critical"
    """Data that must be saved at all costs (triggers fallback logic)"""
    
    SENSITIVE = "sensitive"
    """Data that requires masking in logs and potentially encryption"""
    
    EPHEMERAL = "ephemeral"
    """Transient data that can be lost without major impact (cache-only)"""
    
    LAZY = "lazy"
    """Data that can be processed asynchronously if the system is under load"""


class IntentRegistry:
    """
    Registry for tracking routes and their associated intents and SLAs.
    
    Rationale: This registry allows the framework to make intelligent decisions
    based on declared intents, such as applying appropriate security measures,
    caching strategies, or fallback mechanisms.
    """
    
    def __init__(self):
        self._route_intents: dict[str, dict[str, Any]] = {}
        self._model_intents: dict[type[BaseModel], dict[str, Intent]] = {}
    
    def register_route_intent(self, path: str, method: str, intent: Intent = None, priority: str = "medium"):
        """
        Register intent and priority for a specific route.
        
        Args:
            path: The route path
            method: The HTTP method
            intent: The intent for this route
            priority: The priority level for this route
        """
        route_key = f"{method.upper()} {path}"
        self._route_intents[route_key] = {
            "intent": intent,
            "priority": priority
        }
    
    def get_route_intent(self, path: str, method: str) -> dict[str, Any]:
        """
        Get the intent and priority for a specific route.
        
        Args:
            path: The route path
            method: The HTTP method
            
        Returns:
            Dictionary with intent and priority information
        """
        route_key = f"{method.upper()} {path}"
        return self._route_intents.get(route_key, {})
    
    def register_model_intents(self, model_type: type[BaseModel], field_intents: dict[str, Intent]):
        """
        Register intents for fields in a Pydantic model.
        
        Args:
            model_type: The Pydantic model class
            field_intents: Dictionary mapping field names to intents
        """
        self._model_intents[model_type] = field_intents
    
    def get_model_intents(self, model_type: type[BaseModel]) -> dict[str, Intent]:
        """
        Get intents for fields in a Pydantic model.
        
        Args:
            model_type: The Pydantic model class
            
        Returns:
            Dictionary mapping field names to intents
        """
        return self._model_intents.get(model_type, {})


# Global intent registry instance
_intent_registry = IntentRegistry()


def get_intent_registry() -> IntentRegistry:
    """
    Get the global intent registry instance.
    
    Returns:
        The global IntentRegistry instance
    """
    return _intent_registry


def extract_intents(model: type[BaseModel]) -> dict[str, Intent]:
    """
    Extract intents from a Pydantic model's field metadata.
    
    Rationale: This utility allows the framework to understand the declared
    intents of data fields at runtime, enabling intelligent processing based
    on the developer's intent declarations.
    
    Args:
        model: The Pydantic model class to extract intents from
        
    Returns:
        Dictionary mapping field names to their declared intents
    """
    field_intents = {}
    
    # Iterate through model fields
    for field_name, field_info in model.model_fields.items():
        # Check if the field has intent metadata
        if hasattr(field_info, 'json_schema_extra') and field_info.json_schema_extra:
            # Check for intent in the extra schema metadata
            if isinstance(field_info.json_schema_extra, dict) and 'intent' in field_info.json_schema_extra:
                intent_value = field_info.json_schema_extra['intent']
                if isinstance(intent_value, Intent):
                    field_intents[field_name] = intent_value
                elif isinstance(intent_value, str):
                    try:
                        field_intents[field_name] = Intent(intent_value)
                    except ValueError:
                        # If it's not a valid intent, skip it
                        pass
        # Also check if field_info has an 'extra' attribute (older Pydantic versions)
        elif hasattr(field_info, 'extra') and isinstance(field_info.extra, dict) and 'intent' in field_info.extra:
            intent_value = field_info.extra['intent']
            if isinstance(intent_value, Intent):
                field_intents[field_name] = intent_value
            elif isinstance(intent_value, str):
                try:
                    field_intents[field_name] = Intent(intent_value)
                except ValueError:
                    # If it's not a valid intent, skip it
                    pass
    
    # Register the extracted intents in the global registry
    get_intent_registry().register_model_intents(model, field_intents)
    
    return field_intents


def get_field_intent(model: type[BaseModel], field_name: str) -> Intent:
    """
    Get the intent for a specific field in a model.
    
    Args:
        model: The Pydantic model class
        field_name: The name of the field
        
    Returns:
        The intent for the field, or None if not declared
    """
    intents = extract_intents(model)
    return intents.get(field_name)


def model_intent_score(model: type[BaseModel]) -> float:
    """
    Calculate an intent importance score for a model based on its fields.
    
    Rationale: This score helps the framework prioritize processing and apply
    appropriate resource allocation based on the declared intents of the data.
    
    Args:
        model: The Pydantic model class
        
    Returns:
        A numerical score representing the overall importance of the model
    """
    intents = extract_intents(model)
    
    # Define importance weights for each intent
    intent_weights = {
        Intent.CRITICAL: 10.0,
        Intent.SENSITIVE: 7.0,
        Intent.LAZY: 3.0,
        Intent.EPHEMERAL: 1.0
    }
    
    score = 0.0
    for field_intent in intents.values():
        score += intent_weights.get(field_intent, 0.0)
    
    return score