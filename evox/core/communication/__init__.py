# Communication module exports
from .proxy import proxy
from .message_bus import message_bus, get_event_bus, publish_message, subscribe_to_messages, on_message

__all__ = [
    "proxy",
    "message_bus", "get_event_bus", "publish_message", "subscribe_to_messages", "on_message"
]
