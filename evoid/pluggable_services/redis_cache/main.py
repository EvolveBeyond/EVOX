"""
Redis Cache Storage Provider for EVOX
Implements the StorageProviderProtocol for Redis-based caching
"""

import asyncio
from typing import Any, Dict, Optional
import logging

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None

from evoid.core.storage_provider import StorageProviderProtocol
from evoid.core.intents import Intent


class RedisCacheProvider(StorageProviderProtocol):
    """Redis-based storage provider implementing StorageProviderProtocol"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._redis_client = None
        self._is_healthy = True
        self.name = "redis_cache"
        
    async def initialize(self):
        """Initialize the Redis connection"""
        if not HAS_REDIS:
            logging.error("Redis not available, redis-py package not installed")
            self._is_healthy = False
            return
            
        try:
            self._redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            # Test connection
            await self._redis_client.ping()
            logging.info(f"Redis cache provider connected to {self.host}:{self.port}")
        except Exception as e:
            logging.error(f"Failed to connect to Redis: {e}")
            self._is_healthy = False
    
    async def read(self, key: str, intent: Intent = Intent.STANDARD) -> Any:
        """Read data by key from Redis"""
        if not self._is_healthy or not self._redis_client:
            logging.warning(f"Attempting to read from unhealthy Redis provider: {key}")
            return None
            
        try:
            # Apply intent-based logic (e.g., different TTL for different intents)
            value = await self._redis_client.get(key)
            if value is not None:
                # For critical data, we might want to validate integrity here
                if intent == Intent.CRITICAL:
                    # In real implementation, verify data integrity
                    pass
            return value
        except Exception as e:
            logging.error(f"Error reading from Redis: {e}")
            self._is_healthy = False
            return None
    
    async def write(self, key: str, value: Any, intent: Intent = Intent.STANDARD) -> bool:
        """Write data with key to Redis"""
        if not self._is_healthy or not self._redis_client:
            logging.warning(f"Attempting to write to unhealthy Redis provider: {key}")
            return False
            
        try:
            # Apply intent-based logic (e.g., encryption for CRITICAL data)
            if intent == Intent.CRITICAL:
                # In real implementation, encrypt data before storing
                pass
            
            # Determine TTL based on intent
            ttl = None
            intent_config = intent.get_config(intent)
            if intent_config.cache_ttl:
                ttl = int(intent_config.cache_ttl.total_seconds())
            
            result = await self._redis_client.set(key, value, ex=ttl)
            return result
        except Exception as e:
            logging.error(f"Error writing to Redis: {e}")
            self._is_healthy = False
            return False
    
    async def delete(self, key: str, intent: Intent = Intent.STANDARD) -> bool:
        """Delete data by key from Redis"""
        if not self._is_healthy or not self._redis_client:
            logging.warning(f"Attempting to delete from unhealthy Redis provider: {key}")
            return False
            
        try:
            result = await self._redis_client.delete(key)
            return result > 0
        except Exception as e:
            logging.error(f"Error deleting from Redis: {e}")
            self._is_healthy = False
            return False
    
    async def check_health(self) -> bool:
        """Check Redis provider health"""
        if not HAS_REDIS:
            self._is_healthy = False
            return False
            
        try:
            if self._redis_client:
                await self._redis_client.ping()
                self._is_healthy = True
                return True
            else:
                # Try to initialize if not already done
                await self.initialize()
                return self._is_healthy
        except Exception as e:
            logging.error(f"Redis health check failed: {e}")
            self._is_healthy = False
            return False
    
    @property
    def is_healthy(self) -> bool:
        """Get health status"""
        return self._is_healthy
    
    @property
    def provider_properties(self) -> Dict[str, Any]:
        """Get provider properties"""
        return {
            "type": "redis",
            "host": self.host,
            "port": self.port,
            "supports_transactions": False,
            "supports_replication": True,
            "volatile": False
        }


# Plugin factory function
async def create_provider():
    """Factory function to create Redis cache provider instance"""
    provider = RedisCacheProvider()
    await provider.initialize()
    return provider


if __name__ == "__main__":
    # For testing the Redis cache provider directly
    import asyncio
    
    async def test_provider():
        provider = await create_provider()
        print(f"Redis cache provider created.")
        print(f"Health: {await provider.check_health()}")
        
        # Test basic operations
        test_key = "test_key"
        test_value = "test_value"
        
        # Write
        success = await provider.write(test_key, test_value)
        print(f"Write success: {success}")
        
        # Read
        value = await provider.read(test_key)
        print(f"Read value: {value}")
        
        # Delete
        deleted = await provider.delete(test_key)
        print(f"Delete success: {deleted}")
    
    asyncio.run(test_provider())