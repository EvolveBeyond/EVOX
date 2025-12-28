"""
Lifecycle Hooks - Event System for EVOX Framework

This module implements a lightweight event system using the Observer Pattern 
to enable pluggable services to hook into key lifecycle events of the EVOX framework.

The system provides hooks for:
1. Service initialization
2. Request dispatch (before and after)
3. Data I/O errors
4. System stress events

This enables core decoupling by allowing non-essential behaviors to be 
moved out of the core and into pluggable modules.
"""

from typing import Any, Callable, Dict, List, Set
import asyncio
from dataclasses import dataclass
from enum import Enum
import logging


class LifecycleEvent(str, Enum):
    """
    Enum for lifecycle events that can be triggered in the EVOX framework.
    """
    ON_SERVICE_INIT = "on_service_init"
    PRE_DISPATCH = "pre_dispatch"
    POST_DISPATCH = "post_dispatch"
    ON_DATA_IO_ERROR = "on_data_io_error"
    ON_SYSTEM_STRESS = "on_system_stress"


@dataclass
class EventContext:
    """
    Context object passed to event handlers containing relevant information
    about the event being triggered.
    """
    event_type: LifecycleEvent
    data: Dict[str, Any] | None = None
    timestamp: float | None = None
    service_name: str | None = None
    request_info: Dict[str, Any] | None = None
    error_info: Dict[str, Any] | None = None
    system_status: str | None = None


class LifecycleHookManager:
    """
    Lifecycle Hook Manager - Implements the Observer Pattern for EVOX events
    
    This class manages subscriptions to lifecycle events and allows pluggable services
    to hook into key moments in the framework's operation.
    """
    
    def __init__(self):
        self._subscribers: Dict[LifecycleEvent, List[Callable]] = {}
        # Track which services are subscribed to which events
        self._service_subscriptions: Dict[str, Set[LifecycleEvent]] = {}
        
        # Initialize all event types
        for event in LifecycleEvent:
            self._subscribers[event] = []
    
    def subscribe(self, event_type: LifecycleEvent, handler: Callable, service_name: str | None = None):
        """
        Subscribe a handler function to a specific lifecycle event.
        
        Args:
            event_type: The event to subscribe to
            handler: The function to call when the event is triggered
            service_name: Optional service name for tracking subscriptions
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        
        # Track which service subscribed to this event
        if service_name:
            if service_name not in self._service_subscriptions:
                self._service_subscriptions[service_name] = set()
            self._service_subscriptions[service_name].add(event_type)
    
    def unsubscribe(self, event_type: LifecycleEvent, handler: Callable):
        """
        Unsubscribe a handler from a specific lifecycle event.
        
        Args:
            event_type: The event to unsubscribe from
            handler: The handler function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                # Handler was not subscribed to this event
                pass
    
    async def trigger_event(self, event_type: LifecycleEvent, context: EventContext | None = None):
        """
        Trigger a lifecycle event and notify all subscribers.
        
        Args:
            event_type: The event to trigger
            context: Optional context object with event information
        """
        if context is None:
            context = EventContext(event_type=event_type)
        else:
            context.event_type = event_type
        
        if event_type not in self._subscribers:
            return
        
        # Call all subscribers for this event type
        tasks = []
        for handler in self._subscribers[event_type]:
            try:
                # If handler is async, await it; otherwise call it directly
                if asyncio.iscoroutinefunction(handler):
                    task = handler(context)
                    if task:
                        tasks.append(task)
                else:
                    handler(context)
            except Exception as e:
                # Log the error but continue with other handlers
                logging.error(f"Error in lifecycle event handler for {event_type}: {e}")
        
        # Wait for all async handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_subscribers(self, event_type: LifecycleEvent) -> List[Callable]:
        """
        Get all subscribers for a specific event type.
        
        Args:
            event_type: The event type to query
            
        Returns:
            List of handler functions subscribed to the event
        """
        return self._subscribers.get(event_type, []).copy()
    
    def get_service_subscriptions(self, service_name: str) -> Set[LifecycleEvent]:
        """
        Get all events that a specific service is subscribed to.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Set of LifecycleEvent that the service is subscribed to
        """
        return self._service_subscriptions.get(service_name, set()).copy()
    
    def get_all_subscriptions(self) -> Dict[str, Set[LifecycleEvent]]:
        """
        Get all service subscriptions.
        
        Returns:
            Dictionary mapping service names to their subscribed events
        """
        return self._service_subscriptions.copy()
    
    # Convenience methods for specific events
    async def on_service_init(self, service_name: str, service_instance: Any = None):
        """
        Trigger the on_service_init event.
        
        Args:
            service_name: Name of the service being initialized
            service_instance: Optional service instance
        """
        context = EventContext(
            event_type=LifecycleEvent.ON_SERVICE_INIT,
            data={"service_instance": service_instance},
            service_name=service_name
        )
        await self.trigger_event(LifecycleEvent.ON_SERVICE_INIT, context)
    
    async def pre_dispatch(self, request_info: Dict[str, Any]):
        """
        Trigger the pre_dispatch event.
        
        Args:
            request_info: Information about the incoming request
        """
        context = EventContext(
            event_type=LifecycleEvent.PRE_DISPATCH,
            request_info=request_info
        )
        await self.trigger_event(LifecycleEvent.PRE_DISPATCH, context)
    
    async def post_dispatch(self, request_info: Dict[str, Any], response: Any = None):
        """
        Trigger the post_dispatch event.
        
        Args:
            request_info: Information about the request
            response: The response that was generated
        """
        context = EventContext(
            event_type=LifecycleEvent.POST_DISPATCH,
            request_info=request_info,
            data={"response": response}
        )
        await self.trigger_event(LifecycleEvent.POST_DISPATCH, context)
    
    async def on_data_io_error(self, error_info: Dict[str, Any]):
        """
        Trigger the on_data_io_error event.
        
        Args:
            error_info: Information about the error
        """
        context = EventContext(
            event_type=LifecycleEvent.ON_DATA_IO_ERROR,
            error_info=error_info
        )
        await self.trigger_event(LifecycleEvent.ON_DATA_IO_ERROR, context)
    
    async def on_system_stress(self, system_status: str, metrics: Dict[str, Any] = None):
        """
        Trigger the on_system_stress event.
        
        Args:
            system_status: Current system status (YELLOW, RED, etc.)
            metrics: Optional system metrics
        """
        context = EventContext(
            event_type=LifecycleEvent.ON_SYSTEM_STRESS,
            system_status=system_status,
            data={"metrics": metrics}
        )
        await self.trigger_event(LifecycleEvent.ON_SYSTEM_STRESS, context)


# Global lifecycle hook manager instance
_lifecycle_manager: LifecycleHookManager | None = None


def get_lifecycle_manager() -> LifecycleHookManager:
    """
    Get the global lifecycle hook manager instance.
    
    Returns:
        LifecycleHookManager instance
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleHookManager()
    return _lifecycle_manager


def subscribe_to_event(event_type: LifecycleEvent, handler: Callable, service_name: str | None = None):
    """
    Subscribe to a lifecycle event using the global manager.
    
    Args:
        event_type: The event to subscribe to
        handler: The function to call when the event is triggered
        service_name: Optional service name for tracking
    """
    manager = get_lifecycle_manager()
    manager.subscribe(event_type, handler, service_name)


def unsubscribe_from_event(event_type: LifecycleEvent, handler: Callable):
    """
    Unsubscribe from a lifecycle event using the global manager.
    
    Args:
        event_type: The event to unsubscribe from
        handler: The handler function to remove
    """
    manager = get_lifecycle_manager()
    manager.unsubscribe(event_type, handler)


def trigger_lifecycle_event(event_type: LifecycleEvent, context: EventContext | None = None):
    """
    Trigger a lifecycle event using the global manager.
    
    Args:
        event_type: The event to trigger
        context: Optional context object with event information
    """
    manager = get_lifecycle_manager()
    return manager.trigger_event(event_type, context)


# Convenience functions for specific events
async def on_service_init(service_name: str, service_instance: Any = None):
    """Trigger the on_service_init event."""
    manager = get_lifecycle_manager()
    await manager.on_service_init(service_name, service_instance)


async def pre_dispatch(request_info: Dict[str, Any]):
    """Trigger the pre_dispatch event."""
    manager = get_lifecycle_manager()
    await manager.pre_dispatch(request_info)


async def post_dispatch(request_info: Dict[str, Any], response: Any = None):
    """Trigger the post_dispatch event."""
    manager = get_lifecycle_manager()
    await manager.post_dispatch(request_info, response)


async def on_data_io_error(error_info: Dict[str, Any]):
    """Trigger the on_data_io_error event."""
    manager = get_lifecycle_manager()
    await manager.on_data_io_error(error_info)


async def on_system_stress(system_status: str, metrics: Dict[str, Any] = None):
    """Trigger the on_system_stress event."""
    manager = get_lifecycle_manager()
    await manager.on_system_stress(system_status, metrics)


__all__ = [
    "LifecycleEvent",
    "EventContext",
    "LifecycleHookManager",
    "get_lifecycle_manager",
    "subscribe_to_event",
    "unsubscribe_from_event",
    "trigger_lifecycle_event",
    "on_service_init",
    "pre_dispatch",
    "post_dispatch",
    "on_data_io_error",
    "on_system_stress"
]