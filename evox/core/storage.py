"""
Registry-Driven Data IO Interface - Intent-Aware, Unified data input/output

This module provides the Registry-Driven, Intent-Aware core data IO interface for Evox, implementing
intent-aware data operations with support for caching, TTL, and registry-based fallback mechanisms.

The system automatically infers operational behavior (caching, consistency, storage)
based on declared data intents rather than hardcoded backends.
"""

import time
from typing import Any, Callable

import asyncio

from .config import get_config
from .registry import get_service_registry


class DataIOInterface:
    """Multi-Layered Data IO Interface with Intent-Aware Fallback System
    
    This interface provides intent-aware data operations with support for:
    1. Time-to-live (TTL) based caching across multiple layers
    2. Multi-layered fallback (User-defined -> In-Memory -> File/DB-based)
    3. Automatic provider health checking and failover
    4. Namespace isolation for different data contexts
    
    Fallback Priority:
    1. User-defined Cache (e.g., Redis/Memcached from pluggable_services)
    2. In-Memory Cache (high-speed internal dictionary-based)
    3. File/DB-based Cache (persistent storage as fallback)
    
    Design Notes:
    - Multi-layered caching with automatic failover
    - Automatically handles intent-based behavior without explicit configuration
    - Supports graceful degradation with registry-based fallback providers
    - Health-aware provider selection
    
    Good first issue: Add support for custom serialization formats
    """
    
    def __init__(self):
        # In-memory storage for zero-dependency operation with optimized structures
        self._store: dict[str, dict[str, Any]] = {}
        self._namespace = ""
        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._stale_served = 0
    
    async def initialize(self):
        """Initialize the data IO backend"""
        # In a real implementation, this would connect to actual backends
        pass
    
    async def close(self):
        """Close the data IO backend"""
        # In a real implementation, this would close backend connections
        pass
    
    def namespace(self, ns: str):
        """Set the namespace for subsequent operations"""
        self._namespace = ns
        return self
    
    def _should_use_registry_storage(self) -> bool:
        """Determine if we should use registry-based storage instead of in-memory"""
        # Check if there are available registry-based storage providers
        registry = get_service_registry()
        storage_providers = registry.get_services_by_capability("storage")
        return len(storage_providers) > 0

    async def read(self, key: str, fallback: str = "normal", max_stale: str | None = None) -> Any | None:
        """
        Read value by key with multi-layered fallback system.
            
        Follows priority: User-defined Cache -> In-Memory Cache -> File/DB-based Cache
            
        Args:
            key: The key to read
            fallback: Fallback strategy ("normal", "aggressive", or "registry")
            max_stale: Maximum time to serve stale data (e.g., "1h", "24h")
                      If None, uses configuration default
            
        Returns:
            The value if found, None otherwise
            
        Example:
            # Normal read
            user = await data_io.read("user:123")
                
            # Aggressive fallback allowing up to 24h stale data
            user = await data_io.read("user:123", fallback="aggressive", max_stale="24h")
                
            # Registry-based fallback to alternative providers
            user = await data_io.read("user:123", fallback="registry")
        """
        # Use configuration default if max_stale not specified
        if max_stale is None:
            max_stale = get_config("caching.aggressive_fallback.max_stale_duration", "24h")
            
        full_key = f"{self._namespace}:{key}" if self._namespace else key
            
        # Layer 1: Try user-defined cache (registry-based providers)
        registry = get_service_registry()
        storage_providers = registry.get_services_by_capability("storage")
            
        for provider_info in storage_providers:
            if provider_info.name == "data-io":  # Skip self to avoid circular calls
                continue
                
            # Check provider health before using it
            health_info = provider_info.module.get_service_health(provider_info.name) if hasattr(provider_info.module, 'get_service_health') else None
            is_healthy = health_info.get('is_healthy', True) if health_info else True
                
            if not is_healthy:
                print(f"Provider {provider_info.name} is unhealthy, skipping...")
                continue
                
            try:
                # Load the provider module if not already loaded
                if not provider_info.loaded:
                    module = registry.load_service(provider_info.name)
                    if not module:
                        continue
                else:
                    module = provider_info.module
                    
                # Look for a read method in the provider
                if hasattr(module, 'data_io') and hasattr(module.data_io, 'read'):
                    result = await module.data_io.read(full_key, "normal", max_stale)
                    if result is not None:
                        self._cache_hits += 1
                        return result
                elif hasattr(module, 'read'):
                    # Try calling read method directly on the module
                    result = await module.read(full_key, "normal", max_stale)
                    if result is not None:
                        self._cache_hits += 1
                        return result
                        
            except Exception as e:
                # Log the error but continue with other providers
                print(f"Error reading from provider {provider_info.name}: {e}")
                continue
            
        # Layer 2: Fallback to in-memory cache
        if full_key in self._store:
            entry = self._store[full_key]
            now = time.time()
                
            # Check if entry is still fresh
            if entry.get("expires", 0) > now:
                self._cache_hits += 1
                return entry["value"]
                
            # Entry is expired, check fallback strategy
            if fallback == "aggressive":
                # Parse max_stale duration
                max_stale_seconds = self._parse_duration(max_stale)
                # Check if entry is within max_stale window
                if entry.get("created", 0) + max_stale_seconds > now:
                    self._stale_served += 1
                    return entry["value"]
            
        # Layer 3: Try file/DB-based cache as final fallback
        if fallback == "registry":
            # Try each available storage provider as final fallback
            for provider_info in storage_providers:
                if provider_info.name == "data-io":  # Skip self
                    continue
                    
                try:
                    # Load the provider module if not already loaded
                    if not provider_info.loaded:
                        module = registry.load_service(provider_info.name)
                        if not module:
                            continue
                    else:
                        module = provider_info.module
                        
                    # Look for a read method in the provider
                    if hasattr(module, 'data_io') and hasattr(module.data_io, 'read'):
                        result = await module.data_io.read(full_key, "normal", max_stale)
                        if result is not None:
                            self._cache_hits += 1
                            return result
                    elif hasattr(module, 'read'):
                        # Try calling read method directly on the module
                        result = await module.read(full_key, "normal", max_stale)
                        if result is not None:
                            self._cache_hits += 1
                            return result
                            
                except Exception as e:
                    # Log the error but continue with other providers
                    print(f"Error reading from fallback provider {provider_info.name}: {e}")
                    continue
            
        # Count as miss if we've tried everything
        self._cache_misses += 1
        return None
    
    async def write(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Write key-value pair with multi-layered caching system.
        
        Follows priority: User-defined Cache -> In-Memory Cache -> File/DB-based Cache
        
        Args:
            key: The key to write
            value: The value to store
            ttl: Time-to-live in seconds (None for no expiration)
                 If None, uses configuration default
        """
        # Use configuration default if ttl not specified
        if ttl is None:
            ttl = get_config("caching.default_ttl", 300)
                
        full_key = f"{self._namespace}:{key}" if self._namespace else key
        now = time.time()
                
        entry = {
            "value": value,
            "created": now,
            "expires": now + ttl if ttl is not None else float('inf')
        }
                
        # Layer 1: Write to user-defined cache (registry-based providers)
        registry = get_service_registry()
        storage_providers = registry.get_services_by_capability("storage")
        successful_writes = 0
                
        for provider_info in storage_providers:
            if provider_info.name == "data-io":  # Skip self to avoid circular calls
                continue
                    
            # Check provider health before using it
            health_info = provider_info.module.get_service_health(provider_info.name) if hasattr(provider_info.module, 'get_service_health') else None
            is_healthy = health_info.get('is_healthy', True) if health_info else True
                    
            if not is_healthy:
                print(f"Provider {provider_info.name} is unhealthy, skipping...")
                continue
                    
            try:
                # Load the provider module if not already loaded
                if not provider_info.loaded:
                    module = registry.load_service(provider_info.name)
                    if not module:
                        continue
                else:
                    module = provider_info.module
                        
                # Look for a write method in the provider
                if hasattr(module, 'data_io') and hasattr(module.data_io, 'write'):
                    await module.data_io.write(full_key, value, ttl)
                    successful_writes += 1
                elif hasattr(module, 'write'):
                    # Try calling write method directly on the module
                    await module.write(full_key, value, ttl)
                    successful_writes += 1
                            
            except Exception as e:
                # Log the error but continue with other providers
                print(f"Error writing to provider {provider_info.name}: {e}")
                continue
                
        # Layer 2: Write to in-memory cache (always as backup)
        self._store[full_key] = entry
                
        # If no registry providers were successful, log a warning
        if successful_writes == 0 and len(storage_providers) > 0:
            print(f"Warning: No registry-based providers successfully wrote for key {full_key}")
            # Still keep the in-memory copy as fallback
    
    async def delete(self, key: str) -> None:
        """Delete key"""
        full_key = f"{self._namespace}:{key}" if self._namespace else key
        
        # Check if we should delete from registry-based storage instead of in-memory
        if self._should_use_registry_storage():
            registry = get_service_registry()
            storage_providers = registry.get_services_by_capability("storage")
            
            # Try to delete from primary storage providers first
            for provider_info in storage_providers:
                if provider_info.name == "data-io":  # Skip self to avoid circular calls
                    continue
                    
                try:
                    # Load the provider module if not already loaded
                    if not provider_info.loaded:
                        module = registry.load_service(provider_info.name)
                        if not module:
                            continue
                    else:
                        module = provider_info.module
                    
                    # Look for a delete method in the provider
                    if hasattr(module, 'data_io') and hasattr(module.data_io, 'delete'):
                        await module.data_io.delete(full_key)
                        # Also delete from in-memory
                        if full_key in self._store:
                            del self._store[full_key]
                        return
                    elif hasattr(module, 'delete'):
                        # Try calling delete method directly on the module
                        await module.delete(full_key)
                        # Also delete from in-memory
                        if full_key in self._store:
                            del self._store[full_key]
                        return
                        
                except Exception as e:
                    # Log the error but continue with other providers
                    print(f"Error deleting from provider {provider_info.name}: {e}")
                    continue
        
        # Default to in-memory storage
        if full_key in self._store:
            del self._store[full_key]
    
    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern"""
        full_pattern = f"{self._namespace}:{pattern}" if self._namespace else pattern
        
        # Check if we should get keys from registry-based storage
        if self._should_use_registry_storage():
            registry = get_service_registry()
            storage_providers = registry.get_services_by_capability("storage")
            
            # Try to get keys from primary storage providers first
            for provider_info in storage_providers:
                if provider_info.name == "data-io":  # Skip self to avoid circular calls
                    continue
                    
                try:
                    # Load the provider module if not already loaded
                    if not provider_info.loaded:
                        module = registry.load_service(provider_info.name)
                        if not module:
                            continue
                    else:
                        module = provider_info.module
                    
                    # Look for a keys method in the provider
                    if hasattr(module, 'data_io') and hasattr(module.data_io, 'keys'):
                        provider_keys = await module.data_io.keys(full_pattern)
                        # Combine with in-memory keys
                        if "*" in pattern:
                            prefix = pattern.replace("*", "")
                            memory_keys = [k for k in self._store.keys() if k.startswith(prefix)]
                        else:
                            memory_keys = [k for k in self._store.keys() if pattern in k]
                        return list(set(provider_keys + memory_keys))
                    elif hasattr(module, 'keys'):
                        # Try calling keys method directly on the module
                        provider_keys = await module.keys(full_pattern)
                        # Combine with in-memory keys
                        if "*" in pattern:
                            prefix = pattern.replace("*", "")
                            memory_keys = [k for k in self._store.keys() if k.startswith(prefix)]
                        else:
                            memory_keys = [k for k in self._store.keys() if pattern in k]
                        return list(set(provider_keys + memory_keys))
                        
                except Exception as e:
                    # Log the error but continue with other providers
                    print(f"Error getting keys from provider {provider_info.name}: {e}")
                    continue
        
        # Default to in-memory storage
        if "*" in pattern:
            prefix = pattern.replace("*", "")
            return [k for k in self._store.keys() if k.startswith(prefix)]
        return [k for k in self._store.keys() if pattern in k]
    
    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics"""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "stale_served": self._stale_served,
            "hit_rate": self._cache_hits / max(1, self._cache_hits + self._cache_misses)
        }
    
    def _parse_duration(self, duration: str) -> int:
        """
        Parse duration string to seconds.
        
        Args:
            duration: Duration string (e.g., "1h", "30m", "24h")
            
        Returns:
            Duration in seconds
        """
        if not duration:
            return get_config("caching.default_ttl", 300)  # Default to 5 minutes
            
        duration = duration.lower()
        if duration.endswith('s'):
            return int(duration[:-1])
        elif duration.endswith('m'):
            return int(duration[:-1]) * 60
        elif duration.endswith('h'):
            return int(duration[:-1]) * 3600
        elif duration.endswith('d'):
            return int(duration[:-1]) * 86400
        else:
            # Assume seconds if no unit specified
            return int(duration)


# Global data IO instance
data_io = DataIOInterface()


# Data IO accessor for different namespaces
class DataIOAccessor:
    """Dynamic data IO accessor for different namespaces
    
    Allows accessing data IO with different namespaces using attribute access.
    
    Example:
        # Access user namespace
        user_data = await data_io.user.read("profile:123")
        
        # Access cache namespace
        cached_result = await data_io.cache.read("expensive_calculation")
    """
    
    def __getattr__(self, namespace: str) -> DataIOInterface:
        data_io_instance = DataIOInterface()
        data_io_instance.namespace(namespace)
        return data_io_instance


# Global data IO accessor
data_io = DataIOAccessor()


# Data Intent decorator for declaring intent
class DataIntent:
    """Data intent decorator for declaring operational behavior
    
    This decorator allows declaring operational behavior intentions for data,
    which the system automatically interprets to provide appropriate caching,
    consistency, and storage behaviors.
    
    Design Notes:
    - Intent declarations are explicit and declarative
    - System behavior is inferred from intents rather than hardcoded
    - Separates domain concerns from infrastructure concerns
    
    Good first issue: Add support for custom intent handlers
    """
    
    def __init__(self, **kwargs):
        self.intent_config = kwargs
    
    def __call__(self, cls):
        """Apply intent to a class"""
        cls._data_intent = self.intent_config
        return cls
    
    # Generator-based pattern for creating intent methods
    @staticmethod
    def _create_intent_method(name, **default_kwargs):
        """Create an intent method dynamically"""
        def intent_method(**kwargs):
            intent_config = {**default_kwargs, **kwargs}
            return DataIntent(**intent_config)
        intent_method.__name__ = name
        intent_method.__doc__ = f"""Declare {name.replace('_', ' ')} intent"""
        return staticmethod(intent_method)

# Generate intent methods dynamically
DataIntent.cacheable = DataIntent._create_intent_method(
    "cacheable",
    cacheable=True,
    ttl="1h",
    consistency="eventual",
    fallback="normal",
    max_stale="24h"
)

DataIntent.strong_consistency = DataIntent._create_intent_method(
    "strong_consistency",
    consistency="strong"
)

DataIntent.eventual_ok = DataIntent._create_intent_method(
    "eventual_ok",
    eventual_ok=True
)


# Global data intent decorator
data_intent = DataIntent