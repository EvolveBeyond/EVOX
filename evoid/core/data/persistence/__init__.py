"""
EVOX Core Persistence Layer
==========================

Provides the persistence gateway that routes database operations based on data intents.
This layer acts as the bridge between service logic and database services.

Components:
- IntentRouter: Routes operations based on data intents
- PersistenceGateway: Main entry point for database operations
- DatabaseServiceManager: Manages database service lifecycle
"""

from .intent_router import IntentRouter, PersistenceGateway, DatabaseServiceManager

__all__ = [
    "IntentRouter",
    "PersistenceGateway", 
    "DatabaseServiceManager"
]