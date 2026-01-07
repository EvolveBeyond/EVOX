"""
PostgreSQL Storage Provider for EVOX
Implements the StorageProviderProtocol for PostgreSQL-based storage
"""

import asyncio
from typing import Any, Dict, Optional
import logging

try:
    import asyncpg
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
    asyncpg = None

from evox.core.storage_provider import StorageProviderProtocol
from evox.core.intents import Intent


class PostgresDBProvider(StorageProviderProtocol):
    """PostgreSQL-based storage provider implementing StorageProviderProtocol"""
    
    def __init__(self, host: str = "localhost", port: int = 5432, database: str = "evox", 
                 username: str = "postgres", password: str = ""):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self._connection_pool = None
        self._is_healthy = True
        self.name = "postgres_db"
        
    async def initialize(self):
        """Initialize the PostgreSQL connection pool"""
        if not HAS_POSTGRES:
            logging.error("PostgreSQL not available, asyncpg package not installed")
            self._is_healthy = False
            return
            
        try:
            self._connection_pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                min_size=1,
                max_size=10
            )
            # Test connection
            async with self._connection_pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            logging.info(f"PostgreSQL provider connected to {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {e}")
            self._is_healthy = False
    
    async def read(self, key: str, intent: Intent = Intent.STANDARD) -> Any:
        """Read data by key from PostgreSQL"""
        if not self._is_healthy or not self._connection_pool:
            logging.warning(f"Attempting to read from unhealthy PostgreSQL provider: {key}")
            return None
            
        try:
            async with self._connection_pool.acquire() as conn:
                # Apply intent-based logic (e.g., different handling for critical data)
                if intent == Intent.CRITICAL:
                    # For critical data, ensure strong consistency
                    pass
                    
                row = await conn.fetchrow(
                    'SELECT data FROM storage WHERE key = $1', key
                )
                if row:
                    return row['data']
                return None
        except Exception as e:
            logging.error(f"Error reading from PostgreSQL: {e}")
            self._is_healthy = False
            return None
    
    async def write(self, key: str, value: Any, intent: Intent = Intent.STANDARD) -> bool:
        """Write data with key to PostgreSQL"""
        if not self._is_healthy or not self._connection_pool:
            logging.warning(f"Attempting to write to unhealthy PostgreSQL provider: {key}")
            return False
            
        try:
            async with self._connection_pool.acquire() as conn:
                # Apply intent-based logic (e.g., encryption for CRITICAL data)
                if intent == Intent.CRITICAL:
                    # In real implementation, encrypt data before storing
                    pass
                
                # Use upsert operation
                await conn.execute('''
                    INSERT INTO storage (key, data, created_at, updated_at) 
                    VALUES ($1, $2, NOW(), NOW())
                    ON CONFLICT (key) 
                    DO UPDATE SET data = $2, updated_at = NOW()
                ''', key, value)
                return True
        except Exception as e:
            logging.error(f"Error writing to PostgreSQL: {e}")
            self._is_healthy = False
            return False
    
    async def delete(self, key: str, intent: Intent = Intent.STANDARD) -> bool:
        """Delete data by key from PostgreSQL"""
        if not self._is_healthy or not self._connection_pool:
            logging.warning(f"Attempting to delete from unhealthy PostgreSQL provider: {key}")
            return False
            
        try:
            async with self._connection_pool.acquire() as conn:
                result = await conn.execute(
                    'DELETE FROM storage WHERE key = $1', key
                )
                status = result.split()[-1]  # Get affected row count
                return int(status) > 0
        except Exception as e:
            logging.error(f"Error deleting from PostgreSQL: {e}")
            self._is_healthy = False
            return False
    
    async def check_health(self) -> bool:
        """Check PostgreSQL provider health"""
        if not HAS_POSTGRES:
            self._is_healthy = False
            return False
            
        try:
            if self._connection_pool:
                # Try to execute a simple query
                async with self._connection_pool.acquire() as conn:
                    await conn.fetchval('SELECT 1')
                self._is_healthy = True
                return True
            else:
                # Try to initialize if not already done
                await self.initialize()
                return self._is_healthy
        except Exception as e:
            logging.error(f"PostgreSQL health check failed: {e}")
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
            "type": "postgres",
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "supports_transactions": True,
            "supports_replication": True,
            "volatile": False
        }


# Plugin factory function
async def create_provider():
    """Factory function to create PostgreSQL provider instance"""
    provider = PostgresDBProvider()
    await provider.initialize()
    return provider


if __name__ == "__main__":
    # For testing the PostgreSQL provider directly
    import asyncio
    
    async def test_provider():
        provider = await create_provider()
        print(f"PostgreSQL provider created.")
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
    
    # asyncio.run(test_provider())  # Commented out for safety
    print("PostgreSQL provider created (test disabled for safety).")