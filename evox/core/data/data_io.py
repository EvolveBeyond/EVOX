"""
Data-IO Resilience Layer - Smart Execution for Data Operations

This module provides a provider-agnostic DataIO class that serves as a high-level API
for read, write, and delete operations. It implements intelligent fallback mechanisms,
circuit breakers, and self-healing capabilities based on data intents and system health.

Design Philosophy:
- Resilient by default: Critical data is never lost even during provider failures
- Intent-aware: Operations adapt based on declared data intent and system status
- Transparent fallback: End-users are unaware of fallback mechanisms
- Self-healing: Automatic re-sync when providers recover
- No Bloat: Maintain the "Nano" philosophy by ensuring the core `DataIO` logic is lightweight.

"""

import asyncio
import json
import sqlite3
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging
from enum import Enum
import threading

from .intents.intent_system import Intent, get_intent_registry
from ..infrastructure.dependency_injection.injector import get_health_registry, get_service_health
from ..monitoring.intelligence.environmental_intelligence import get_current_context_status, SystemStatus
from ..data.storage.providers.base_provider import BaseProvider
from ..data.storage.registry import SQLiteStorageProvider, MemoryStorageProvider, service_registry


class CircuitState(Enum):
    """
    Circuit breaker states for provider failure tracking.
    
    Rationale: Prevents repeated failures to unhealthy providers and enables
    quick fallback decisions.
    """
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Tripped - immediate failure
    HALF_OPEN = "half_open"  # Testing recovery


class DataIO:
    """
    Provider-agnostic DataIO class for resilient data operations.
    
    This class serves as the primary interface for developers to interact with data.
    It uses data intents and provider health to make real-time decisions on where
    and how to store information.
    
    Design Rationale:
    - High-level API: Simple read/write/delete operations for developers
    - Resilient by default: Automatic fallback for critical data
    - Intent-aware: Operations adapt based on data intent
    - Transparent: End-users unaware of fallback mechanisms
    """
    
    def __init__(self):
        self._primary_provider = None
        self._fallback_provider = None
        self._emergency_buffer = EmergencySafetyBuffer()
        self._circuit_breakers = {}  # Provider -> CircuitBreaker
        self._sync_task = None
        self._sync_task_running = False
        self._sync_manager = None
        
        # Initialize providers
        self._initialize_providers()
        
        # Initialize sync manager but don't start it yet
        self._sync_manager = BackgroundSyncManager(self)
    
    def _initialize_providers(self):
        """
        Initialize primary and fallback providers.
        
        Rationale: Establishes the primary and fallback storage providers
        for resilient operations.
        """
        # First try to get providers from service registry
        providers = service_registry.list_providers()
        
        if providers:
            # Try to find a suitable primary provider from registry
            for provider_name in providers:
                provider = service_registry.get_provider(provider_name)
                if provider and isinstance(provider, BaseProvider):
                    # Prefer providers that support transactions for critical data
                    props = getattr(provider, 'provider_properties', {})
                    supports_transactions = props.get('supports_transactions', False)
                    supports_replication = props.get('supports_replication', False)
                    
                    # Prefer providers with transaction/replication support as primary
                    if supports_transactions and supports_replication:
                        self._primary_provider = provider
                        break
                    elif self._primary_provider is None:
                        self._primary_provider = provider
            
            # Set fallback provider from remaining providers
            for provider_name in providers:
                provider = service_registry.get_provider(provider_name)
                if (provider and isinstance(provider, BaseProvider) and 
                    provider != self._primary_provider and self._fallback_provider is None):
                    self._fallback_provider = provider
        
        # If no providers found in registry, fall back to health registry
        if self._primary_provider is None:
            health_registry = get_health_registry()
            for service_name, health_info in health_registry.items():
                instance = health_info.get("instance")
                if isinstance(instance, BaseProvider):
                    if self._primary_provider is None:
                        self._primary_provider = instance
                    elif self._fallback_provider is None:
                        self._fallback_provider = instance
        
        # If no fallback provider found, create a memory-based one
        if self._fallback_provider is None:
            self._fallback_provider = MemoryStorageProvider()
    
    def _get_circuit_breaker(self, provider_name: str):
        """
        Get or create a circuit breaker for a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            CircuitBreaker instance for the provider
        """
        if provider_name not in self._circuit_breakers:
            self._circuit_breakers[provider_name] = CircuitBreaker(provider_name)
        return self._circuit_breakers[provider_name]
    
    async def write(self, key: str, data: Any, intent: Intent = Intent.EPHEMERAL) -> bool:
        """
        Write data with intent-aware resilience.
        
        Rationale: This method implements the core logic for resilient data storage
        based on data intent and provider health.
        
        Args:
            key: Unique identifier for the data
            data: Data to be stored
            intent: Intent of the data (affects storage decisions)
            
        Returns:
            True if write was successful, False otherwise
        """
        # Check system status
        system_status = get_current_context_status()
        
        # Handle sensitive data
        if intent == Intent.SENSITIVE:
            data = self._mask_sensitive_data(data)
        
        # Check if primary provider is healthy
        primary_healthy = await self._is_provider_healthy(self._primary_provider)
        circuit_breaker = self._get_circuit_breaker(self._get_provider_name(self._primary_provider))
        
        # If primary is unhealthy or circuit breaker is open, use fallback
        if not primary_healthy or circuit_breaker.state == CircuitState.OPEN:
            # For critical data, use emergency buffer
            if intent == Intent.CRITICAL:
                logging.warning(f"Primary provider unhealthy, writing critical data to emergency buffer: {key}")
                return await self._emergency_buffer.write(key, data)
            # For other intents, use fallback provider
            else:
                try:
                    result = await self._fallback_provider.write(key, data)
                    if result:
                        circuit_breaker.record_success()
                    else:
                        circuit_breaker.record_failure()
                    return result
                except Exception as e:
                    logging.error(f"Fallback provider failed: {e}")
                    circuit_breaker.record_failure()
                    return False
        else:
            # Primary provider is healthy, attempt write
            try:
                # For ephemeral data during system stress, only cache
                if intent == Intent.EPHEMERAL and system_status != SystemStatus.GREEN:
                    # Skip disk write during stress for ephemeral data
                    logging.info(f"Skipping disk write for ephemeral data during {system_status} status: {key}")
                    return True
                
                result = await self._primary_provider.write(key, data)
                if result:
                    circuit_breaker.record_success()
                else:
                    circuit_breaker.record_failure()
                return result
            except Exception as e:
                logging.error(f"Primary provider write failed: {e}")
                circuit_breaker.record_failure()
                
                # If critical data, try emergency buffer
                if intent == Intent.CRITICAL:
                    logging.warning(f"Primary provider failed, writing critical data to emergency buffer: {key}")
                    return await self._emergency_buffer.write(key, data)
                
                return False
    
    async def read(self, key: str, intent: Intent = Intent.EPHEMERAL) -> Any:
        """
        Read data with fallback capability.
        
        Args:
            key: Unique identifier for the data
            intent: Intent of the data (affects read strategy)
            
        Returns:
            Retrieved data or None if not found
        """
        # First try primary provider
        try:
            primary_healthy = await self._is_provider_healthy(self._primary_provider)
            if primary_healthy:
                data = await self._primary_provider.read(key)
                if data is not None:
                    return data
        except Exception:
            pass  # Primary provider failed, continue to fallback
        
        # Try fallback provider
        try:
            data = await self._fallback_provider.read(key)
            if data is not None:
                return data
        except Exception:
            pass  # Fallback provider failed, continue to emergency buffer
        
        # Try emergency buffer as last resort
        try:
            data = await self._emergency_buffer.read(key)
            if data is not None:
                return data
        except Exception:
            pass  # Emergency buffer failed
        
        return None
    
    async def delete(self, key: str, intent: Intent = Intent.EPHEMERAL) -> bool:
        """
        Delete data with resilience.
        
        Args:
            key: Unique identifier for the data
            intent: Intent of the data (affects delete strategy)
            
        Returns:
            True if delete was successful, False otherwise
        """
        success_count = 0
        
        # Delete from primary provider
        try:
            primary_healthy = await self._is_provider_healthy(self._primary_provider)
            if primary_healthy:
                if await self._primary_provider.delete(key):
                    success_count += 1
        except Exception:
            pass  # Primary provider failed
        
        # Delete from fallback provider
        try:
            if await self._fallback_provider.delete(key):
                success_count += 1
        except Exception:
            pass  # Fallback provider failed
        
        # Delete from emergency buffer
        try:
            if await self._emergency_buffer.delete(key):
                success_count += 1
        except Exception:
            pass  # Emergency buffer failed
        
        # Require at least one successful deletion for non-critical data
        # For critical data, we might want to ensure it's deleted from all locations
        return success_count > 0
    
    def _mask_sensitive_data(self, data: Any) -> Any:
        """
        Mask sensitive data before storage.
        
        Rationale: Implements automatic masking of sensitive fields to protect
        data privacy as per the intent specification.
        
        Args:
            data: Data to be masked
            
        Returns:
            Masked data
        """
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if self._is_sensitive_field(key):
                    # Mask the value (replace with asterisks or hash)
                    if isinstance(value, str):
                        masked_data[key] = "*" * len(value)
                    else:
                        masked_data[key] = "***MASKED***"
                else:
                    masked_data[key] = value
            return masked_data
        elif isinstance(data, str):
            # If the entire data is a sensitive string, mask it
            return "*" * len(data)
        else:
            return data
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """
        Determine if a field is sensitive based on naming patterns.
        
        Args:
            field_name: Name of the field
            
        Returns:
            True if field is considered sensitive, False otherwise
        """
        sensitive_patterns = [
            'password', 'secret', 'token', 'key', 'auth', 'credential',
            'ssn', 'card', 'cvv', 'pin', 'cvv', 'email', 'phone', 'address'
        ]
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in sensitive_patterns)
    
    async def _is_provider_healthy(self, provider: BaseProvider) -> bool:
        """
        Check if a provider is healthy using the health registry.
        
        Args:
            provider: The provider to check
            
        Returns:
            True if healthy, False otherwise
        """
        if provider is None:
            return False
            
        try:
            # Check health registry first
            health_info = get_service_health(self._get_provider_name(provider))
            if health_info and not health_info.get("is_healthy", False):
                return False
            
            # If registry says healthy, double-check with provider
            return await provider.check_health()
        except Exception:
            return False
    
    def _get_provider_name(self, provider: BaseProvider) -> str:
        """
        Get a unique name for a provider instance.
        
        Args:
            provider: The provider instance
            
        Returns:
            Unique name for the provider
        """
        if hasattr(provider, '__class__'):
            return f"{provider.__class__.__name__}_{id(provider)}"
        return f"unknown_provider_{id(provider)}"
    
    def start_background_sync(self):
        """
        Start the background sync task.
        """
        if not self._sync_task_running and self._sync_manager:
            self._sync_task_running = True
            # Run in background without blocking
            self._sync_task = asyncio.create_task(self._sync_manager.start_sync_task())


class CircuitBreaker:
    """
    Circuit breaker implementation for provider failure tracking.
    
    Rationale: Prevents repeated failures to unhealthy providers and enables
    quick fallback decisions based on recent failure history.
    """
    
    def __init__(self, provider_name: str, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # seconds
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
    
    def record_failure(self):
        """
        Record a failure and update circuit breaker state.
        """
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logging.warning(f"Circuit breaker OPEN for provider {self.provider_name}")
    
    def record_success(self):
        """
        Record a success and update circuit breaker state.
        """
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
    
    def can_attempt(self) -> bool:
        """
        Check if an operation can be attempted based on circuit breaker state.
        
        Returns:
            True if operation can be attempted, False otherwise
        """
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if enough time has passed to try again
            if self.last_failure_time is not None:
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            # Allow one attempt in half-open state
            return True
        return False


class EmergencySafetyBuffer:
    """
    Emergency Safety Buffer for critical data during provider failures.
    
    Rationale: Provides a temporary storage location for critical data when
    primary providers are unavailable, ensuring data is not lost.
    """
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._init_db()
    
    def _init_db(self):
        """
        Initialize the SQLite database for the emergency buffer.
        """
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS emergency_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL,
                intent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pending_sync BOOLEAN DEFAULT 1
            )
        ''')
        self.conn.commit()
    
    async def write(self, key: str, data: Any) -> bool:
        """
        Write data to the emergency buffer.
        
        Args:
            key: Unique identifier for the data
            data: Data to be stored
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            data_str = json.dumps(data, default=str)  # Serialize data to JSON
            
            with self.conn:
                self.conn.execute('''
                    INSERT OR REPLACE INTO emergency_buffer 
                    (key, data, intent, pending_sync) 
                    VALUES (?, ?, ?, 1)
                ''', (key, data_str, Intent.CRITICAL.value))
            
            logging.info(f"Data written to emergency buffer: {key}")
            return True
        except Exception as e:
            logging.error(f"Failed to write to emergency buffer: {e}")
            return False
    
    async def read(self, key: str) -> Any:
        """
        Read data from the emergency buffer.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            Retrieved data or None if not found
        """
        try:
            cursor = self.conn.execute(
                'SELECT data FROM emergency_buffer WHERE key = ?', (key,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        except Exception as e:
            logging.error(f"Failed to read from emergency buffer: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """
        Delete data from the emergency buffer.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            True if delete was successful, False otherwise
        """
        try:
            with self.conn:
                cursor = self.conn.execute(
                    'DELETE FROM emergency_buffer WHERE key = ?', (key,)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Failed to delete from emergency buffer: {e}")
            return False
    
    async def get_pending_sync_data(self) -> List[Dict]:
        """
        Get all data marked as pending sync.
        
        Returns:
            List of dictionaries containing pending sync data
        """
        try:
            cursor = self.conn.execute(
                'SELECT key, data, intent FROM emergency_buffer WHERE pending_sync = 1'
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    'key': row[0],
                    'data': json.loads(row[1]),
                    'intent': row[2]
                })
            return result
        except Exception as e:
            logging.error(f"Failed to get pending sync data: {e}")
            return []
    
    async def mark_synced(self, key: str) -> bool:
        """
        Mark a specific key as synced (no longer pending).
        
        Args:
            key: Key to mark as synced
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.conn:
                cursor = self.conn.execute(
                    'UPDATE emergency_buffer SET pending_sync = 0 WHERE key = ?', (key,)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Failed to mark sync status: {e}")
            return False
    
    async def clear_synced_data(self) -> bool:
        """
        Clear data that has been successfully synced.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.conn:
                cursor = self.conn.execute(
                    'DELETE FROM emergency_buffer WHERE pending_sync = 0'
                )
                return True
        except Exception as e:
            logging.error(f"Failed to clear synced data: {e}")
            return False


class BackgroundSyncManager:
    """
    Background task manager for syncing emergency buffer data to primary provider.
    
    Rationale: Automatically re-syncs data from emergency buffer to primary provider
    when it becomes healthy again, ensuring data consistency.
    """
    
    def __init__(self, data_io: DataIO):
        self.data_io = data_io
        self.running = False
        self.sync_interval = 10  # seconds
    
    async def start_sync_task(self):
        """
        Start the background sync task.
        """
        if self.running:
            return
        
        self.running = True
        logging.info("Starting background sync task")
        
        while self.running:
            try:
                await self._sync_pending_data()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logging.error(f"Background sync task error: {e}")
                await asyncio.sleep(self.sync_interval)
    
    async def stop_sync_task(self):
        """
        Stop the background sync task.
        """
        self.running = False
        logging.info("Stopping background sync task")
    
    async def _sync_pending_data(self):
        """
        Sync pending data from emergency buffer to primary provider.
        """
        if not self.data_io._primary_provider:
            return
        
        # Check if primary provider is healthy
        if not await self.data_io._is_provider_healthy(self.data_io._primary_provider):
            return
        
        # Get pending sync data
        pending_data = await self.data_io._emergency_buffer.get_pending_sync_data()
        
        if not pending_data:
            return
        
        logging.info(f"Syncing {len(pending_data)} pending records to primary provider")
        
        for record in pending_data:
            try:
                # Attempt to write to primary provider
                success = await self.data_io.write(
                    record['key'], 
                    record['data'], 
                    Intent(record['intent']) if record['intent'] else Intent.CRITICAL
                )
                
                if success:
                    # Mark as synced in buffer
                    await self.data_io._emergency_buffer.mark_synced(record['key'])
                    logging.info(f"Successfully synced {record['key']} to primary provider")
                else:
                    logging.warning(f"Failed to sync {record['key']} to primary provider")
            except Exception as e:
                logging.error(f"Error syncing record {record['key']}: {e}")
        
        # Clear synced data from buffer after successful sync
        await self.data_io._emergency_buffer.clear_synced_data()


# Global DataIO instance - initialize without starting background sync
_data_io = DataIO()

data_io = _data_io  # Public alias for backward compatibility


def get_data_io() -> DataIO:
    """
    Get the global DataIO instance.
    
    Returns:
        DataIO instance
    """
    return _data_io


def start_data_io_background_sync():
    """
    Start the background sync task for the global DataIO instance.
    This should be called after an event loop is running.
    """
    _data_io.start_background_sync()


__all__ = [
    "DataIO",
    "get_data_io",
    "start_data_io_background_sync",
    "CircuitBreaker",
    "EmergencySafetyBuffer",
    "BackgroundSyncManager"
]