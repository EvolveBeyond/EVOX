"""
Internal Message Bus System for EVOX
Provides asynchronous messaging between services with pub/sub pattern.
"""

from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..utilities.models.core_models import CoreMessage
from ..data.intents.intent_system import Intent

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages supported by the bus"""
    COMMAND = "command"
    EVENT = "event"
    QUERY = "query"
    RESPONSE = "response"

@dataclass
class Message:
    """Internal message structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.EVENT
    topic: str = ""
    payload: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    intent: Intent = Intent.STANDARD

class Subscription:
    """Represents a subscription to a topic"""
    
    def __init__(self, topic: str, callback: Callable, subscriber_id: str):
        self.topic = topic
        self.callback = callback
        self.subscriber_id = subscriber_id
        self.created_at = datetime.now()

class PriorityMessageQueue:
    """Priority-based message queue"""
    
    def __init__(self):
        self.high_priority: asyncio.Queue = asyncio.Queue()
        self.normal_priority: asyncio.Queue = asyncio.Queue()
        self.low_priority: asyncio.Queue = asyncio.Queue()
    
    async def put(self, message: Message):
        """Put message in appropriate priority queue"""
        intent_config = message.intent.get_config(message.intent)
        priority_level = intent_config.message_priority
        
        if priority_level == "high":
            await self.high_priority.put(message)
        elif priority_level == "low":
            await self.low_priority.put(message)
        else:  # normal
            await self.normal_priority.put(message)
    
    async def get(self):
        """Get message from highest priority queue with messages"""
        # Check high priority first
        if not self.high_priority.empty():
            return await self.high_priority.get()
        # Then normal priority
        elif not self.normal_priority.empty():
            return await self.normal_priority.get()
        # Finally low priority
        else:
            return await self.low_priority.get()
    
    def task_done(self):
        """Mark task as done"""
        # We'll assume the queue that has messages is the one we're getting from
        # In practice, we'd need a more sophisticated approach
        if not self.high_priority.empty():
            self.high_priority.task_done()
        elif not self.normal_priority.empty():
            self.normal_priority.task_done()
        else:
            self.low_priority.task_done()

class MessageBus:
    """Internal asynchronous message bus with pub/sub capabilities"""
    
    def __init__(self):
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._topics: Set[str] = set()
        self._message_queue = PriorityMessageQueue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self.stats = {
            "messages_published": 0,
            "messages_consumed": 0,
            "subscriptions_created": 0,
            "errors": 0
        }
    
    async def start(self):
        """Start the message bus processing"""
        if self._running:
            return
            
        self._running = True
        self._worker_task = asyncio.create_task(self._process_messages())
        logger.info("Message bus started")
    
    async def stop(self):
        """Stop the message bus processing"""
        if not self._running:
            return
            
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Message bus stopped")
    
    def subscribe(
        self,
        topic: str,
        callback: Callable[[Message], Any],
        subscriber_id: Optional[str] = None
    ) -> str:
        """Subscribe to a topic"""
        if subscriber_id is None:
            subscriber_id = str(uuid.uuid4())
        
        subscription = Subscription(topic, callback, subscriber_id)
        
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        
        self._subscriptions[topic].append(subscription)
        self._topics.add(topic)
        self.stats["subscriptions_created"] += 1
        
        logger.info(f"Subscriber {subscriber_id} subscribed to topic '{topic}'")
        return subscriber_id
    
    def unsubscribe(self, topic: str, subscriber_id: str) -> bool:
        """Unsubscribe from a topic"""
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
        message_type: MessageType = MessageType.EVENT,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        intent: Intent = Intent.STANDARD
    ) -> str:
        """Publish a message to a topic"""
        message = Message(
            type=message_type,
            topic=topic,
            payload=payload,
            correlation_id=correlation_id,
            reply_to=reply_to,
            metadata=metadata or {},
            intent=intent
        )
        
        await self._message_queue.put(message)
        self.stats["messages_published"] += 1
        
        logger.debug(f"Published message to topic '{topic}': {message.id}")
        return message.id
    
    async def request_response(
        self,
        topic: str,
        payload: Any,
        timeout: float = 30.0
    ) -> Any:
        """Send request and wait for response"""
        response_topic = f"response.{uuid.uuid4()}"
        result_future = asyncio.Future()
        
        def response_handler(message: Message):
            if not result_future.done():
                result_future.set_result(message.payload)
        
        # Subscribe to response topic
        subscription_id = self.subscribe(response_topic, response_handler)
        
        try:
            # Send request
            await self.publish(
                topic=topic,
                payload=payload,
                message_type=MessageType.QUERY,
                reply_to=response_topic
            )
            
            # Wait for response
            result = await asyncio.wait_for(result_future, timeout=timeout)
            return result
            
        finally:
            # Cleanup subscription
            self.unsubscribe(response_topic, subscription_id)
    
    async def _process_messages(self):
        """Process messages from the queue"""
        while self._running:
            try:
                message = await self._message_queue.get()
                
                # Deliver to subscribers
                await self._deliver_message(message)
                self.stats["messages_consumed"] += 1
                
                self._message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Error processing message: {e}")
    
    async def _deliver_message(self, message: Message):
        """Deliver message to all subscribers of the topic"""
        if message.topic not in self._subscriptions:
            return
        
        subscriptions = self._subscriptions[message.topic]
        
        # Deliver to all subscribers concurrently
        delivery_tasks = []
        for subscription in subscriptions:
            task = asyncio.create_task(
                self._deliver_to_subscriber(subscription, message)
            )
            delivery_tasks.append(task)
        
        # Wait for all deliveries
        if delivery_tasks:
            await asyncio.gather(*delivery_tasks, return_exceptions=True)
    
    async def _deliver_to_subscriber(self, subscription: Subscription, message: Message):
        """Deliver message to a specific subscriber"""
        try:
            result = subscription.callback(message)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Error delivering message to subscriber {subscription.subscriber_id}: {e}")

# Global message bus instance
message_bus = MessageBus()

# Convenience functions
async def publish_message(
    topic: str,
    payload: Any,
    message_type: MessageType = MessageType.EVENT,
    intent: Intent = Intent.STANDARD,
    **kwargs
) -> str:
    """Convenience function to publish message"""
    return await message_bus.publish(topic, payload, message_type, intent=intent, **kwargs)

async def subscribe_to_topic(topic: str, callback: Callable) -> str:
    """Convenience function to subscribe to topic"""
    return message_bus.subscribe(topic, callback)

# Additional functions for compatibility

def get_event_bus():
    """Get the global message bus instance"""
    return message_bus

async def subscribe_to_messages(topic: str, callback: Callable):
    """Subscribe to messages on a topic"""
    return message_bus.subscribe(topic, callback)

def on_message(topic: str, callback: Callable):
    """Decorator to subscribe to messages"""
    def decorator(func):
        message_bus.subscribe(topic, func)
        return func
    return decorator

# Export public API
__all__ = [
    "MessageBus",
    "Message",
    "MessageType",
    "Subscription",
    "message_bus",
    "publish_message",
    "subscribe_to_topic",
    "get_event_bus",
    "subscribe_to_messages",
    "on_message"
]