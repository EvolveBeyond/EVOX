"""
Intent-Based Database Routing System
===================================

Core routing system that directs database operations based on data intents,
model annotations, and service configurations. This creates a unified
persistence layer that abstracts database complexity from service developers.

Architecture:
- IntentRouter: Analyzes intents and routes to appropriate database services
- PersistenceGateway: Main facade for database operations
- DatabaseServiceManager: Manages database service lifecycle and health
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, Union, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from pydantic import BaseModel
from typing import Annotated, get_type_hints

# Import EVOX core components
from ..intents.annotated_intents import get_intent_from_annotation, IntentMarker
from ..intents.data_intents import BaseIntentConfig
from ...errors.BaseError import (
    DatabaseError, DuplicateKeyError, ForeignKeyViolationError,
    ConnectionTimeoutError, intercept_database_error
)
from ..storage.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """Types of database operations supported by the router"""
    CREATE = "create"
    READ = "read" 
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    TRANSACTION = "transaction"


@dataclass
class RoutingContext:
    """Context information for routing decisions"""
    model_type: Type[BaseModel]
    operation: OperationType
    intent: Union[IntentMarker, BaseIntentConfig, str]
    data: Optional[Any] = None
    query_params: Optional[Dict[str, Any]] = None
    transaction_context: Optional[Dict[str, Any]] = None


@dataclass  
class RoutingResult:
    """Result of routing decision"""
    service_name: str
    service_instance: BaseProvider
    operation_method: str
    transformed_data: Any
    routing_metadata: Dict[str, Any]


class IntentRouter:
    """
    Intent-Based Database Router
    
    Analyzes data intents and model annotations to route database operations
    to the most appropriate database services. Handles automatic failover,
    load balancing, and intent-specific optimizations.
    
    Key Features:
    - Intent-aware routing based on data sensitivity and requirements
    - Automatic service discovery and health checking
    - Fallback mechanisms for service failures
    - Performance optimization based on operation patterns
    """
    
    def __init__(self, service_manager: 'DatabaseServiceManager'):
        self.service_manager = service_manager
        self._routing_cache: Dict[str, RoutingResult] = {}
        self._intent_routing_rules: Dict[str, Callable] = {}
        self._setup_default_routing_rules()
    
    def _setup_default_routing_rules(self):
        """Setup default routing rules based on intent types"""
        self._intent_routing_rules.update({
            "CRITICAL": self._route_critical_intent,
            "STANDARD": self._route_standard_intent,
            "EPHEMERAL": self._route_ephemeral_intent,
            "SQL_STORAGE": self._route_sql_storage,
            "NOSQL_STORAGE": self._route_nosql_storage,
            "CACHE_STORAGE": self._route_cache_storage,
            "ANALYTICS_STORAGE": self._route_analytics_storage,
            "DOCUMENT_STORAGE": self._route_document_storage,
        })
    
    async def route_operation(self, context: RoutingContext) -> RoutingResult:
        """
        Route database operation based on context and intents.
        
        Args:
            context: Routing context containing model, operation, and intent info
            
        Returns:
            RoutingResult with service and operation details
        """
        cache_key = self._generate_cache_key(context)
        
        # Check cache first
        if cache_key in self._routing_cache:
            return self._routing_cache[cache_key]
        
        # Analyze intent from model annotations
        intent_marker = self._extract_intent_from_model(context.model_type)
        if not intent_marker and hasattr(context, 'intent'):
            intent_marker = context.intent
            
        # Determine routing strategy
        routing_strategy = self._determine_routing_strategy(intent_marker, context.operation)
        
        # Execute routing strategy
        result = await routing_strategy(context, intent_marker)
        
        # Cache the result
        self._routing_cache[cache_key] = result
        
        return result
    
    def _extract_intent_from_model(self, model_type: Type[BaseModel]) -> Optional[IntentMarker]:
        """Extract intent information from model annotations"""
        try:
            field_annotations = get_type_hints(model_type)
            
            # Look for intent markers in field annotations
            for field_name, annotation in field_annotations.items():
                intent_marker = get_intent_from_annotation(annotation)
                if intent_marker:
                    return intent_marker
                    
            return None
        except Exception as e:
            logger.debug(f"Could not extract intent from model {model_type}: {e}")
            return None
    
    def _determine_routing_strategy(self, intent: Any, operation: OperationType) -> Callable:
        """Determine appropriate routing strategy based on intent and operation"""
        intent_name = getattr(intent, 'name', str(intent)).upper()
        
        # Check for specific intent routing rule
        if intent_name in self._intent_routing_rules:
            return self._intent_routing_rules[intent_name]
        
        # Default routing based on operation type
        if operation == OperationType.READ:
            return self._route_read_operation
        elif operation in [OperationType.CREATE, OperationType.UPDATE, OperationType.DELETE]:
            return self._route_write_operation
        else:
            return self._route_generic_operation
    
    async def _route_critical_intent(self, context: RoutingContext, intent: IntentMarker) -> RoutingResult:
        """Route operations with critical intent (high durability, ACID compliance)"""
        # Find SQL services with strong consistency
        sql_services = await self.service_manager.get_services_by_type("sql")
        healthy_sql_services = [s for s in sql_services if await s.check_health()]
        
        if not healthy_sql_services:
            # Fallback to any healthy service
            healthy_services = await self.service_manager.get_healthy_services()
            if not healthy_services:
                raise DatabaseError("No healthy database services available for critical operation")
            service = healthy_services[0]
        else:
            service = healthy_sql_services[0]  # Use first healthy SQL service
        
        return RoutingResult(
            service_name=service.name,
            service_instance=service,
            operation_method=self._get_operation_method(context.operation, service),
            transformed_data=self._transform_for_critical_storage(context.data, intent),
            routing_metadata={
                "intent": "CRITICAL",
                "consistency": "STRONG",
                "durability": "HIGH",
                "service_type": getattr(service, 'type', 'unknown')
            }
        )
    
    async def _route_standard_intent(self, context: RoutingContext, intent: IntentMarker) -> RoutingResult:
        """Route operations with standard intent (balanced performance/durability)"""
        # Prefer services that match the intent's storage preference
        preferred_type = getattr(intent, 'storage_engine', 'auto')
        if preferred_type == 'auto':
            preferred_type = 'nosql'  # Default for standard operations
        
        services = await self.service_manager.get_services_by_type(preferred_type)
        healthy_services = [s for s in services if await s.check_health()]
        
        if not healthy_services:
            # Fallback to any healthy service
            healthy_services = await self.service_manager.get_healthy_services()
            if not healthy_services:
                raise DatabaseError("No healthy database services available")
            service = healthy_services[0]
        else:
            service = healthy_services[0]
        
        return RoutingResult(
            service_name=service.name,
            service_instance=service,
            operation_method=self._get_operation_method(context.operation, service),
            transformed_data=self._transform_for_standard_storage(context.data, intent),
            routing_metadata={
                "intent": "STANDARD",
                "consistency": "EVENTUAL",
                "durability": "NORMAL",
                "service_type": getattr(service, 'type', 'unknown')
            }
        )
    
    async def _route_ephemeral_intent(self, context: RoutingContext, intent: IntentMarker) -> RoutingResult:
        """Route operations with ephemeral intent (high performance, low durability)"""
        # Prefer cache/key-value services for ephemeral data
        cache_services = await self.service_manager.get_services_by_type("key_value")
        healthy_cache_services = [s for s in cache_services if await s.check_health()]
        
        if not healthy_cache_services:
            # Fallback to memory services
            memory_services = await self.service_manager.get_services_by_type("memory")
            healthy_memory_services = [s for s in memory_services if await s.check_health()]
            
            if healthy_memory_services:
                service = healthy_memory_services[0]
            elif healthy_cache_services:
                service = healthy_cache_services[0]
            else:
                # Last resort: any healthy service
                healthy_services = await self.service_manager.get_healthy_services()
                if not healthy_services:
                    raise DatabaseError("No healthy database services available for ephemeral operation")
                service = healthy_services[0]
        else:
            service = healthy_cache_services[0]
        
        return RoutingResult(
            service_name=service.name,
            service_instance=service,
            operation_method=self._get_operation_method(context.operation, service),
            transformed_data=self._transform_for_ephemeral_storage(context.data, intent),
            routing_metadata={
                "intent": "EPHEMERAL",
                "consistency": "NONE",
                "durability": "LOW",
                "ttl": getattr(intent, 'cache_ttl', None),
                "service_type": getattr(service, 'type', 'unknown')
            }
        )
    
    # Storage-type specific routing methods
    async def _route_sql_storage(self, context: RoutingContext, intent: IntentMarker) -> RoutingResult:
        """Route to SQL storage services"""
        return await self._route_to_specific_type(context, intent, "sql")
    
    async def _route_nosql_storage(self, context: RoutingContext, intent: IntentMarker) -> RoutingResult:
        """Route to NoSQL storage services"""
        return await self._route_to_specific_type(context, intent, "nosql")
    
    async def _route_cache_storage(self, context: RoutingContext, intent: IntentMarker) -> RoutingResult:
        """Route to cache storage services"""
        return await self._route_to_specific_type(context, intent, "key_value")
    
    async def _route_analytics_storage(self, context: RoutingContext, intent: IntentMarker) -> RoutingResult:
        """Route to analytics/columnar storage services"""
        return await self._route_to_specific_type(context, intent, "columnar")
    
    async def _route_document_storage(self, context: RoutingContext, intent: IntentMarker) -> RoutingResult:
        """Route to document storage services"""
        return await self._route_to_specific_type(context, intent, "document")
    
    async def _route_to_specific_type(self, context: RoutingContext, intent: IntentMarker, service_type: str) -> RoutingResult:
        """Generic method to route to specific service type"""
        services = await self.service_manager.get_services_by_type(service_type)
        healthy_services = [s for s in services if await s.check_health()]
        
        if not healthy_services:
            raise DatabaseError(f"No healthy {service_type} services available")
        
        service = healthy_services[0]  # Use first healthy service of type
        
        return RoutingResult(
            service_name=service.name,
            service_instance=service,
            operation_method=self._get_operation_method(context.operation, service),
            transformed_data=context.data,  # Pass through for specific types
            routing_metadata={
                "intent": getattr(intent, 'name', 'CUSTOM'),
                "service_type": service_type,
                "storage_engine": service_type
            }
        )
    
    # Operation-type routing methods
    async def _route_read_operation(self, context: RoutingContext, intent: Any) -> RoutingResult:
        """Route read operations (prefer faster, eventually consistent services)"""
        # For reads, prefer cache services first, then others
        cache_services = await self.service_manager.get_services_by_type("key_value")
        healthy_cache = [s for s in cache_services if await s.check_health()]
        
        if healthy_cache:
            service = healthy_cache[0]
        else:
            # Fallback to any healthy service
            healthy_services = await self.service_manager.get_healthy_services()
            if not healthy_services:
                raise DatabaseError("No healthy database services available for read operation")
            service = healthy_services[0]
        
        return RoutingResult(
            service_name=service.name,
            service_instance=service,
            operation_method="read",
            transformed_data=context.data,
            routing_metadata={"operation": "READ", "service_type": getattr(service, 'type', 'unknown')}
        )
    
    async def _route_write_operation(self, context: RoutingContext, intent: Any) -> RoutingResult:
        """Route write operations (consider durability and consistency requirements)"""
        # For writes, consider intent requirements
        if hasattr(intent, 'strong_consistency') and intent.strong_consistency:
            return await self._route_critical_intent(context, intent)
        else:
            return await self._route_standard_intent(context, intent)
    
    async def _route_generic_operation(self, context: RoutingContext, intent: Any) -> RoutingResult:
        """Route generic operations (fallback strategy)"""
        healthy_services = await self.service_manager.get_healthy_services()
        if not healthy_services:
            raise DatabaseError("No healthy database services available")
        
        service = healthy_services[0]
        
        return RoutingResult(
            service_name=service.name,
            service_instance=service,
            operation_method=self._get_operation_method(context.operation, service),
            transformed_data=context.data,
            routing_metadata={"operation": str(context.operation), "service_type": getattr(service, 'type', 'unknown')}
        )
    
    def _get_operation_method(self, operation: OperationType, service: BaseProvider) -> str:
        """Map operation type to service method name"""
        method_mapping = {
            OperationType.CREATE: "write",
            OperationType.READ: "read",
            OperationType.UPDATE: "write", 
            OperationType.DELETE: "delete",
            OperationType.QUERY: "read",
            OperationType.TRANSACTION: "execute_transaction"
        }
        return method_mapping.get(operation, "read")
    
    def _transform_for_critical_storage(self, data: Any, intent: IntentMarker) -> Any:
        """Transform data for critical storage (encryption, validation)"""
        # Apply encryption if required
        if getattr(intent, 'encrypt', False):
            # Would call encryption transformer here
            pass
        return data
    
    def _transform_for_standard_storage(self, data: Any, intent: IntentMarker) -> Any:
        """Transform data for standard storage"""
        return data
    
    def _transform_for_ephemeral_storage(self, data: Any, intent: IntentMarker) -> Any:
        """Transform data for ephemeral storage (may add TTL, compression)"""
        return data
    
    def _generate_cache_key(self, context: RoutingContext) -> str:
        """Generate cache key for routing results"""
        model_name = context.model_type.__name__ if context.model_type else "unknown"
        return f"{model_name}_{context.operation}_{hash(str(context.intent))}"
    
    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate routing cache entries"""
        if pattern:
            keys_to_remove = [k for k in self._routing_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._routing_cache[key]
        else:
            self._routing_cache.clear()


class DatabaseServiceManager:
    """
    Database Service Manager
    
    Manages the lifecycle, health, and discovery of database services.
    Handles service registration, health checking, and failover coordination.
    """
    
    def __init__(self):
        self._services: Dict[str, BaseProvider] = {}
        self._service_health: Dict[str, Dict[str, Any]] = {}
        self._service_types: Dict[str, List[str]] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def register_service(self, name: str, service: BaseProvider, service_type: str = "generic"):
        """Register a database service"""
        self._services[name] = service
        if service_type not in self._service_types:
            self._service_types[service_type] = []
        self._service_types[service_type].append(name)
        
        # Initialize health status
        self._service_health[name] = {
            "healthy": True,
            "last_check": datetime.now(),
            "type": service_type
        }
        
        logger.info(f"Registered database service: {name} ({service_type})")
    
    async def get_services_by_type(self, service_type: str) -> List[BaseProvider]:
        """Get all services of a specific type"""
        if service_type not in self._service_types:
            return []
        
        service_names = self._service_types[service_type]
        return [self._services[name] for name in service_names if name in self._services]
    
    async def get_healthy_services(self) -> List[BaseProvider]:
        """Get all currently healthy services"""
        healthy_names = [
            name for name, health in self._service_health.items() 
            if health.get("healthy", False)
        ]
        return [self._services[name] for name in healthy_names if name in self._services]
    
    async def start_health_monitoring(self):
        """Start periodic health checking of all services"""
        if self._health_check_task and not self._health_check_task.done():
            return  # Already running
        
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started database service health monitoring")
    
    async def stop_health_monitoring(self):
        """Stop health checking"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Stopped database service health monitoring")
    
    async def _health_check_loop(self):
        """Periodic health checking loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _perform_health_checks(self):
        """Perform health checks on all registered services"""
        for name, service in self._services.items():
            try:
                is_healthy = await service.check_health()
                self._service_health[name] = {
                    "healthy": is_healthy,
                    "last_check": datetime.now(),
                    "type": self._service_health[name].get("type", "unknown")
                }
                
                if not is_healthy:
                    logger.warning(f"Database service {name} is unhealthy")
                    
            except Exception as e:
                logger.error(f"Health check failed for service {name}: {e}")
                self._service_health[name] = {
                    "healthy": False,
                    "last_check": datetime.now(),
                    "error": str(e),
                    "type": self._service_health[name].get("type", "unknown")
                }


class PersistenceGateway:
    """
    Main Persistence Gateway
    
    Unified entry point for all database operations. Provides a clean,
    intent-aware interface that abstracts database complexity from service developers.
    
    Usage:
        gateway = PersistenceGateway()
        await gateway.initialize()
        
        # Save model with automatic intent routing
        await gateway.save(user_model)
        
        # Query with intent-aware optimization
        users = await gateway.query(UserModel).filter(name="John").all()
    """
    
    def __init__(self):
        self.service_manager = DatabaseServiceManager()
        self.intent_router = IntentRouter(self.service_manager)
        self._initialized = False
    
    async def initialize(self, database_services: Optional[Dict[str, BaseProvider]] = None):
        """Initialize the persistence gateway"""
        if self._initialized:
            return
        
        # Register provided services
        if database_services:
            for name, service in database_services.items():
                service_type = getattr(service, 'type', 'generic')
                await self.service_manager.register_service(name, service, service_type)
        
        # Start health monitoring
        await self.service_manager.start_health_monitoring()
        
        self._initialized = True
        logger.info("Persistence gateway initialized")
    
    async def save(self, model: BaseModel, intent: Optional[Any] = None) -> Any:
        """Save model with intent-aware routing"""
        context = RoutingContext(
            model_type=type(model),
            operation=OperationType.CREATE,
            intent=intent or "STANDARD",
            data=model
        )
        
        routing_result = await self.intent_router.route_operation(context)
        
        try:
            # Execute the routed operation
            result = await routing_result.service_instance.write(
                key=str(hash(str(model))),  # Generate key from model
                value=routing_result.transformed_data
            )
            return result
        except Exception as e:
            intercepted_error = intercept_database_error(e, {
                "operation": "SAVE",
                "model_type": type(model).__name__,
                "service": routing_result.service_name
            })
            raise intercepted_error
    
    async def get(self, model_type: Type[BaseModel], key: str, intent: Optional[Any] = None) -> Any:
        """Get model by key with intent-aware routing"""
        context = RoutingContext(
            model_type=model_type,
            operation=OperationType.READ,
            intent=intent or "STANDARD",
            data={"key": key}
        )
        
        routing_result = await self.intent_router.route_operation(context)
        
        try:
            result = await routing_result.service_instance.read(key=key)
            return result
        except Exception as e:
            intercepted_error = intercept_database_error(e, {
                "operation": "GET",
                "model_type": model_type.__name__,
                "key": key,
                "service": routing_result.service_name
            })
            raise intercepted_error
    
    async def delete(self, model_type: Type[BaseModel], key: str, intent: Optional[Any] = None) -> bool:
        """Delete model by key with intent-aware routing"""
        context = RoutingContext(
            model_type=model_type,
            operation=OperationType.DELETE,
            intent=intent or "STANDARD",
            data={"key": key}
        )
        
        routing_result = await self.intent_router.route_operation(context)
        
        try:
            result = await routing_result.service_instance.delete(key=key)
            return result
        except Exception as e:
            intercepted_error = intercept_database_error(e, {
                "operation": "DELETE",
                "model_type": model_type.__name__,
                "key": key,
                "service": routing_result.service_name
            })
            raise intercepted_error
    
    async def query(self, model_type: Type[BaseModel], intent: Optional[Any] = None) -> 'QueryExecutor':
        """Create query executor with intent-aware optimization"""
        return QueryExecutor(self, model_type, intent)
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.service_manager.stop_health_monitoring()
        self._initialized = False
        logger.info("Persistence gateway cleaned up")


class QueryExecutor:
    """Query execution helper with intent-aware optimization"""
    
    def __init__(self, gateway: PersistenceGateway, model_type: Type[BaseModel], intent: Optional[Any] = None):
        self.gateway = gateway
        self.model_type = model_type
        self.intent = intent
        self._filters = {}
        self._limit = None
        self._offset = None
    
    def filter(self, **kwargs) -> 'QueryExecutor':
        """Add filters to query"""
        self._filters.update(kwargs)
        return self
    
    def limit(self, count: int) -> 'QueryExecutor':
        """Limit query results"""
        self._limit = count
        return self
    
    def offset(self, count: int) -> 'QueryExecutor':
        """Offset query results"""
        self._offset = count
        return self
    
    async def all(self) -> List[Any]:
        """Execute query and return all results"""
        # This would implement actual query execution based on filters
        # For now, return empty list as placeholder
        return []
    
    async def first(self) -> Optional[Any]:
        """Execute query and return first result"""
        results = await self.all()
        return results[0] if results else None


# Global persistence gateway instance
persistence_gateway = PersistenceGateway()


# Convenience functions
async def save_model(model: BaseModel, intent: Optional[Any] = None) -> Any:
    """Save model using global persistence gateway"""
    await persistence_gateway.initialize()  # Ensure initialization
    return await persistence_gateway.save(model, intent)


async def get_model(model_type: Type[BaseModel], key: str, intent: Optional[Any] = None) -> Any:
    """Get model using global persistence gateway"""
    await persistence_gateway.initialize()
    return await persistence_gateway.get(model_type, key, intent)


async def delete_model(model_type: Type[BaseModel], key: str, intent: Optional[Any] = None) -> bool:
    """Delete model using global persistence gateway"""
    await persistence_gateway.initialize()
    return await persistence_gateway.delete(model_type, key, intent)


async def query_models(model_type: Type[BaseModel], intent: Optional[Any] = None) -> QueryExecutor:
    """Query models using global persistence gateway"""
    await persistence_gateway.initialize()
    return await persistence_gateway.query(model_type, intent)


__all__ = [
    "IntentRouter",
    "DatabaseServiceManager", 
    "PersistenceGateway",
    "RoutingContext",
    "RoutingResult",
    "OperationType",
    "QueryExecutor",
    "persistence_gateway",
    "save_model",
    "get_model",
    "delete_model",
    "query_models"
]