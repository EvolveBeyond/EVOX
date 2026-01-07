"""
EVOX Internal Event Bus
=======================

Lightweight internal messaging system for EVOX framework components.
Provides pub/sub pattern for internal framework events and lifecycle hooks.

This module handles:
- Internal framework events (startup, shutdown, configuration changes)
- Component lifecycle notifications
- Service discovery events
- Performance monitoring events
"""

from typing import Any, Callable, Dict, List, Optional, Set, Union, Awaitable
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
import uuid
from enum import Enum

from ...data.intents.intent_system import Intent

logger = logging.getLogger(__name__)


class EventBusEventType(Enum):
    """Types of internal events supported by the bus"""
    LIFECYCLE_STARTUP = "lifecycle.startup"
    LIFECYCLE_SHUTDOWN = "lifecycle.shutdown"
    LIFECYCLE_HEALTH_CHECK = "lifecycle.health_check"
    CONFIGURATION_CHANGED = "configuration.changed"
    SERVICE_REGISTERED = "service.registered"
    SERVICE_UNREGISTERED = "service.unregistered"
    PERFORMANCE_ALERT = "performance.alert"
    CACHE_EVENT = "cache.event"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class EventBusMessage:
    """Internal event message structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventBusEventType = EventBusEventType.LIFECYCLE_STARTUP
    topic: str = ""
    payload: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    intent: Intent = Intent.STANDARD


class EventBusSubscription:
    """Represents a subscription to an event topic"""
    
    def __init__(self, topic: str, callback: Callable[[EventBusMessage], Union[None, Awaitable[None]]], subscriber_id: str):
        self.topic = topic
        self.callback = callback
        self.subscriber_id = subscriber_id
        self.created_at = datetime.now()
        self.active = True


class InternalEventBus:
    """Internal asynchronous event bus for framework events"""
    
    def __init__(self):
        self._subscriptions: Dict[str, List[EventBusSubscription]] = {}
        self._topics: Set[str] = set()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self.stats = {
            "events_published": 0,
            "events_consumed": 0,
            "subscriptions_created": 0,
            "errors": 0
        }
    
    async def start(self):
        """Start the event bus processing"""
        if self._running:
            return
            
        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())
        logger.info("Internal event bus started")
    
    async def stop(self):
        """Stop the event bus processing"""
        if not self._running:
            return
            
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Internal event bus stopped")
    
    def subscribe(
        self,
        topic: str,
        callback: Callable[[EventBusMessage], Union[None, Awaitable[None]]],
        subscriber_id: Optional[str] = None
    ) -> str:
        """Subscribe to an event topic"""
        if subscriber_id is None:
            subscriber_id = str(uuid.uuid4())
        
        subscription = EventBusSubscription(topic, callback, subscriber_id)
        
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        
        self._subscriptions[topic].append(subscription)
        self._topics.add(topic)
        self.stats["subscriptions_created"] += 1
        
        logger.info(f"Subscriber {subscriber_id} subscribed to topic '{topic}'")
        return subscriber_id
    
    def unsubscribe(self, topic: str, subscriber_id: str) -> bool:
        """Unsubscribe from an event topic"""
        if topic not in self._subscriptions:
            return False
        
        subscriptions = self._subscriptions[topic]
        initial_count = len(subscriptions)
        
        self._subscriptions[topic] = [
            sub for sub in subscriptions 
            if sub.subscriber_id != subscriber_id
        ]
        
        # Clean up empty topic
        if not self._subscriptions[topic]:
            del self._subscriptions[topic]
            self._topics.discard(topic)
        
        removed = len(subscriptions) != initial_count
        if removed:
            logger.info(f"Subscriber {subscriber_id} unsubscribed from topic '{topic}'")
        
        return removed
    
    async def publish(
        self,
        topic: str,
        payload: Any,
        event_type: EventBusEventType = EventBusEventType.LIFECYCLE_STARTUP,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        intent: Intent = Intent.STANDARD
    ) -> str:
        """Publish an event to a topic"""
        message = EventBusMessage(
            type=event_type,
            topic=topic,
            payload=payload,
            correlation_id=correlation_id,
            source=source,
            metadata=metadata or {},
            intent=intent
        )
        
        await self._event_queue.put(message)
        self.stats["events_published"] += 1
        
        logger.debug(f"Published event to topic '{topic}': {message.id}")
        return message.id
    
    async def _process_events(self):
        """Process events from the queue"""
        while self._running:
            try:
                message = await self._event_queue.get()
                
                # Deliver to subscribers
                await self._deliver_event(message)
                self.stats["events_consumed"] += 1
                
                self._event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Error processing event: {e}")
    
    async def _deliver_event(self, message: EventBusMessage):
        """Deliver event to all subscribers of the topic"""
        if message.topic not in self._subscriptions:
            return
        
        subscriptions = self._subscriptions[message.topic]
        
        # Deliver to all subscribers concurrently
        delivery_tasks = []
        for subscription in subscriptions:
            if not subscription.active:
                continue
            task = asyncio.create_task(
                self._deliver_to_subscriber(subscription, message)
            )
            delivery_tasks.append(task)
        
        # Wait for all deliveries
        if delivery_tasks:
            await asyncio.gather(*delivery_tasks, return_exceptions=True)
    
    async def _deliver_to_subscriber(self, subscription: EventBusSubscription, message: EventBusMessage):
        """Deliver event to a specific subscriber"""
        try:
            result = subscription.callback(message)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Error delivering event to subscriber {subscription.subscriber_id}: {e}")


# Global event bus instance
event_bus = InternalEventBus()


# Convenience functions
async def publish_event(
    topic: str,
    payload: Any,
    event_type: EventBusEventType = EventBusEventType.LIFECYCLE_STARTUP,
    intent: Intent = Intent.STANDARD,
    **kwargs
) -> str:
    """Convenience function to publish event"""
    return await event_bus.publish(topic, payload, event_type, intent=intent, **kwargs)


def subscribe_to_events(topic: str, callback: Callable[[EventBusMessage], Union[None, Awaitable[None]]]) -> str:
    """Convenience function to subscribe to events"""
    return event_bus.subscribe(topic, callback)


def get_event_bus():
    """Get the global event bus instance"""
    return event_bus


def on_event(topic: str, callback: Callable):
    """Decorator to subscribe to events"""
    def decorator(func):
        event_bus.subscribe(topic, func)
        return func
    return decorator


__all__ = [
    "InternalEventBus",
    "EventBusMessage",
    "EventBusEventType",
    "EventBusSubscription",
    "event_bus",
    "publish_event",
    "subscribe_to_events",
    "get_event_bus",
    "on_event"
]