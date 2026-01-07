"""
Multi-Tier Caching System for EVOX
Provides memory, Redis, and disk-based caching with automatic tiering.
"""

from typing import Any, Optional, Dict, Callable, Union, List
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import pickle
from pathlib import Path
from ...data.intents.intent_system import Intent, get_intent_config

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None

logger = logging.getLogger(__name__)

class CacheTier(Enum):
    """Cache tiers in order of speed/cost"""
    MEMORY = "memory"      # Fastest, most expensive
    REDIS = "redis"        # Fast, external
    DISK = "disk"          # Slowest, cheapest

class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"           # Least Recently Used
    FIFO = "fifo"         # First In First Out
    TTL = "ttl"           # Time To Live

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    tier: CacheTier
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    ttl: Optional[timedelta] = None
    size: int = 0

class BaseCacheLayer:
    """Base cache layer interface"""
    
    def __init__(self, tier: CacheTier, max_size: int = 1000):
        self.tier = tier
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        entry = self._cache.get(key)
        if entry is None:
            self.misses += 1
            return None
        
        # Check TTL
        if entry.ttl and datetime.now() - entry.created_at > entry.ttl:
            del self._cache[key]
            self.misses += 1
            return None
        
        # Update access time
        entry.accessed_at = datetime.now()
        self.hits += 1
        return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set value in cache"""
        try:
            # Calculate size (approximate)
            size = len(str(value)) if isinstance(value, (str, bytes)) else len(pickle.dumps(value))
            
            entry = CacheEntry(
                key=key,
                value=value,
                tier=self.tier,
                ttl=ttl,
                size=size
            )
            
            # Evict if necessary
            if len(self._cache) >= self.max_size:
                await self._evict()
            
            self._cache[key] = entry
            return True
        except Exception as e:
            logger.error(f"Error setting cache entry: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self):
        """Clear all entries"""
        self._cache.clear()
    
    async def _evict(self):
        """Evict entries based on policy"""
        # Simple LRU implementation
        if self._cache:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k].accessed_at)
            del self._cache[oldest_key]

class MemoryCache(BaseCacheLayer):
    """In-memory cache layer"""
    
    def __init__(self, max_size: int = 10000):
        super().__init__(CacheTier.MEMORY, max_size)

class RedisCache(BaseCacheLayer):
    """Redis cache layer"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, max_size: int = 50000):
        super().__init__(CacheTier.REDIS, max_size)
        self.host = host
        self.port = port
        self.db = db
        self.redis_client = None
        self.connected = False
        
        if HAS_REDIS:
            self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=False
            )
            # Test connection
            self.redis_client.ping()
            self.connected = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from Redis cache"""
        if not self.connected:
            return await super().get(key)
        
        try:
            data = self.redis_client.get(key)
            if data is None:
                self.misses += 1
                return None
            
            value = pickle.loads(data)
            self.hits += 1
            return value
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return await super().get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set in Redis cache"""
        if not self.connected:
            return await super().set(key, value, ttl)
        
        try:
            data = pickle.dumps(value)
            expire_time = int(ttl.total_seconds()) if ttl else None
            result = self.redis_client.set(key, data, ex=expire_time)
            return result is True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return await super().set(key, value, ttl)

class DiskCache(BaseCacheLayer):
    """Disk-based cache layer"""
    
    def __init__(self, cache_dir: str = ".cache", max_size: int = 100000):
        super().__init__(CacheTier.DISK, max_size)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key"""
        # Hash key to create safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from disk cache"""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            self.misses += 1
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            # Check TTL
            if 'ttl' in data and 'created_at' in data:
                created_at = datetime.fromisoformat(data['created_at'])
                if datetime.now() - created_at > timedelta(seconds=data['ttl']):
                    cache_path.unlink()
                    self.misses += 1
                    return None
            
            self.hits += 1
            return data['value']
        except Exception as e:
            logger.error(f"Disk cache read error: {e}")
            self.misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set in disk cache"""
        try:
            cache_path = self._get_cache_path(key)
            
            data = {
                'value': value,
                'created_at': datetime.now().isoformat(),
                'ttl': ttl.total_seconds() if ttl else None
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            return True
        except Exception as e:
            logger.error(f"Disk cache write error: {e}")
            return False

class CacheLayer:
    """Multi-tier cache system with automatic tiering"""
    
    def __init__(self):
        self.layers: Dict[CacheTier, BaseCacheLayer] = {}
        self.default_ttl: Optional[timedelta] = None
        self.stats = {
            "gets": 0,
            "sets": 0,
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        
        # Initialize default layers
        self.add_layer(MemoryCache(max_size=1000))
        if HAS_REDIS:
            self.add_layer(RedisCache())
        self.add_layer(DiskCache())
    
    def _get_intent_based_config(self, intent: Intent):
        """Get cache configuration based on intent"""
        intent_config = intent.get_config(intent)
        return {
            "ttl": intent_config.cache_ttl,
            "cache_enabled": intent_config.cache_enabled,
            "cache_tier": CacheTier.MEMORY if intent == Intent.EPHEMERAL else \
                        CacheTier.REDIS if intent == Intent.STANDARD else CacheTier.MEMORY  # Critical data in fast memory
        }
    
    def add_layer(self, layer: BaseCacheLayer):
        """Add a cache layer"""
        self.layers[layer.tier] = layer
        logger.info(f"Added cache layer: {layer.tier.value}")
    
    def remove_layer(self, tier: CacheTier):
        """Remove a cache layer"""
        if tier in self.layers:
            del self.layers[tier]
            logger.info(f"Removed cache layer: {tier.value}")
    
    async def get(self, key: str, tier_preference: Optional[List[CacheTier]] = None, intent: Intent = Intent.STANDARD) -> Optional[Any]:
        """Get value from cache, checking tiers in order"""
        self.stats["gets"] += 1
        
        # Get intent-based configuration
        intent_config = self._get_intent_based_config(intent)
        if not intent_config["cache_enabled"]:
            return None  # Don't cache if disabled by intent
        
        # Default tier preference: Memory -> Redis -> Disk
        if tier_preference is None:
            # Adjust tier preference based on intent
            if intent == Intent.EPHEMERAL:
                tier_preference = [CacheTier.MEMORY]
            elif intent == Intent.CRITICAL:
                tier_preference = [CacheTier.MEMORY, CacheTier.REDIS, CacheTier.DISK]
            else:  # STANDARD
                tier_preference = [CacheTier.MEMORY, CacheTier.REDIS, CacheTier.DISK]
        
        # Check each tier in preference order
        for tier in tier_preference:
            if tier in self.layers:
                value = await self.layers[tier].get(key)
                if value is not None:
                    self.stats["hits"] += 1
                    # Promote to higher tiers
                    await self._promote(key, value, tier)
                    return value
        
        self.stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None, tier: Optional[CacheTier] = None, intent: Intent = Intent.STANDARD) -> bool:
        """Set value in cache"""
        self.stats["sets"] += 1
        
        # Get intent-based configuration
        intent_config = self._get_intent_based_config(intent)
        if not intent_config["cache_enabled"]:
            return True  # Return success if caching is disabled by intent
        
        # Use intent-based TTL if not specified
        if ttl is None:
            ttl = intent_config["ttl"]
        
        # Determine tier based on intent if not specified
        if tier is None:
            tier = intent_config["cache_tier"]
        
        # For CRITICAL data, use write-through to all higher tiers
        if intent == Intent.CRITICAL:
            # Set in all tiers for critical data
            tiers_to_set = list(self.layers.keys())
        elif tier:
            # Set in specific tier
            tiers_to_set = [tier]
        else:
            # Set in default tiers
            tiers_to_set = list(self.layers.keys())
        
        success = True
        for cache_tier in tiers_to_set:
            if cache_tier in self.layers:
                layer_success = await self.layers[cache_tier].set(key, value, ttl)
                success = success and layer_success
        
        return success
    
    async def delete(self, key: str):
        """Delete key from all cache layers"""
        for layer in self.layers.values():
            await layer.delete(key)
    
    async def clear(self, tier: Optional[CacheTier] = None):
        """Clear cache"""
        if tier:
            if tier in self.layers:
                await self.layers[tier].clear()
        else:
            for layer in self.layers.values():
                await layer.clear()
    
    async def _promote(self, key: str, value: Any, from_tier: CacheTier):
        """Promote value to higher cache tiers"""
        promotion_order = [CacheTier.MEMORY, CacheTier.REDIS, CacheTier.DISK]
        current_index = promotion_order.index(from_tier)
        
        # Promote to all higher tiers
        for i in range(current_index):
            tier = promotion_order[i]
            if tier in self.layers:
                await self.layers[tier].set(key, value, ttl=timedelta(minutes=5))

# Global cache instance
cache_layer = CacheLayer()

# Convenience functions
async def cache_get(key: str, intent: Intent = Intent.STANDARD) -> Optional[Any]:
    """Get value from cache"""
    return await cache_layer.get(key, intent=intent)

async def cache_set(key: str, value: Any, ttl: Optional[timedelta] = None, intent: Intent = Intent.STANDARD) -> bool:
    """Set value in cache"""
    return await cache_layer.set(key, value, ttl, intent=intent)

async def cache_delete(key: str):
    """Delete key from cache"""
    await cache_layer.delete(key)

# Additional functions for compatibility
def get_cache():
    """Get the global cache instance"""
    return cache_layer

# Decorator for caching function results
def cached(ttl: Optional[timedelta] = None, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = await cache_get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

# Export public API
__all__ = [
    "CacheLayer",
    "CacheTier",
    "EvictionPolicy",
    "cache_layer",
    "cache_get",
    "cache_set",
    "cache_delete",
    "cached",
    "get_cache"
]