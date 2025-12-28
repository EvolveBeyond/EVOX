"""
Logging Service - Pluggable Logging Module for EVOX Framework

This service implements advanced logging functionality that was moved out of the core.
It subscribes to lifecycle events to log relevant information.
"""

from evox import service, get, post, Body, Intent
from evox.core.inject import inject
from evox.core.lifecycle import (
    LifecycleEvent, 
    subscribe_to_event, 
    EventContext,
    on_service_init,
    pre_dispatch,
    post_dispatch,
    on_data_io_error,
    on_system_stress
)
from pydantic import BaseModel
from typing import Annotated, Dict, Any, Optional
import logging
import json
from datetime import datetime
from pathlib import Path


class LogEntry(BaseModel):
    """Model for a log entry"""
    timestamp: str
    level: str
    message: str
    service: Optional[str] = None
    event_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class LoggingService:
    """Service for handling logging operations"""
    
    def __init__(self):
        self.log_level = logging.INFO
        self.log_file = "evox.log"
        self.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.logger = logging.getLogger("evox-logging-service")
        self.logger.setLevel(self.log_level)
        
        # Create file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(self.log_level)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        
        # Create formatter
        formatter = logging.Formatter(self.log_format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    async def log_event(self, context: EventContext):
        """Log an event based on its type and context"""
        message = self._format_event_message(context)
        self.logger.info(message)
    
    def _format_event_message(self, context: EventContext) -> str:
        """Format an event context into a log message"""
        timestamp = datetime.now().isoformat()
        event_type = context.event_type.value
        
        base_message = f"[{timestamp}] EVENT: {event_type}"
        
        if context.service_name:
            base_message += f" | SERVICE: {context.service_name}"
        
        if context.request_info:
            base_message += f" | REQUEST: {context.request_info.get('path', 'unknown')} {context.request_info.get('method', 'unknown')}"
        
        if context.error_info:
            base_message += f" | ERROR: {context.error_info.get('message', 'unknown error')}"
        
        if context.system_status:
            base_message += f" | STATUS: {context.system_status}"
        
        if context.data:
            base_message += f" | DATA: {json.dumps(context.data, default=str)}"
        
        return base_message
    
    async def get_logs(self, limit: int = 100) -> list:
        """Retrieve recent log entries"""
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                # Return last 'limit' lines
                recent_lines = lines[-limit:] if len(lines) > limit else lines
                return [line.strip() for line in recent_lines]
        except FileNotFoundError:
            return []


# Initialize the service
log_svc = service("logging-service").port(8006).build()
logging_service = LoggingService()


# Subscribe to lifecycle events
async def handle_service_init(context: EventContext):
    await logging_service.log_event(context)

async def handle_pre_dispatch(context: EventContext):
    await logging_service.log_event(context)

async def handle_post_dispatch(context: EventContext):
    await logging_service.log_event(context)

async def handle_data_io_error(context: EventContext):
    await logging_service.log_event(context)

async def handle_system_stress(context: EventContext):
    await logging_service.log_event(context)


# Subscribe to all relevant events
subscribe_to_event(LifecycleEvent.ON_SERVICE_INIT, handle_service_init, "logging-service")
subscribe_to_event(LifecycleEvent.PRE_DISPATCH, handle_pre_dispatch, "logging-service")
subscribe_to_event(LifecycleEvent.POST_DISPATCH, handle_post_dispatch, "logging-service")
subscribe_to_event(LifecycleEvent.ON_DATA_IO_ERROR, handle_data_io_error, "logging-service")
subscribe_to_event(LifecycleEvent.ON_SYSTEM_STRESS, handle_system_stress, "logging-service")


# API endpoints for log management
@get("/logs")
async def get_logs(limit: int = 50):
    """Retrieve recent log entries"""
    logs = await logging_service.get_logs(limit)
    return {"logs": logs, "count": len(logs)}


@get("/logs/health")
async def logging_health():
    """Health check for the logging service"""
    return {
        "status": "healthy",
        "service": "logging-service",
        "log_file": logging_service.log_file
    }


@post("/logs/config")
async def update_log_config(config: Annotated[Dict[str, Any], Body]):
    """Update logging configuration"""
    if "log_level" in config:
        level = config["log_level"].upper()
        logging_service.log_level = getattr(logging, level, logging.INFO)
        logging_service.logger.setLevel(logging_service.log_level)
    
    if "log_file" in config:
        logging_service.log_file = config["log_file"]
    
    return {"status": "updated", "config": config}


# Example startup handler
@log_svc.on_startup
async def startup():
    print("Logging service started")
    # Trigger service init event
    await on_service_init("logging-service", logging_service)


# Example shutdown handler
@log_svc.on_shutdown
async def shutdown():
    print("Logging service stopped")


if __name__ == "__main__":
    log_svc.run(dev=True)