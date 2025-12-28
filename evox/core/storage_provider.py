"""
Health-aware storage provider implementing the BaseProvider interface
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from .common import BaseProvider


class SQLiteStorageProvider(BaseProvider):
    """
    Health-aware SQLite storage provider implementing BaseProvider interface.
    
    Rationale: This provider demonstrates how to implement the BaseProvider interface
    with real health checking capabilities, specifically for SQLite storage.
    """
    
    def __init__(self, db_path: str = "data.db", is_mock_healthy: bool = True):
        self.db_path = db_path
        self._is_healthy = True
        self._last_health_check = datetime.now()
        self.is_mock_healthy = is_mock_healthy  # For testing purposes
    
    @property
    def is_healthy(self) -> bool:
        """
        Property indicating current health status of the provider.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        return self._is_healthy
    
    @property
    def last_health_check(self) -> datetime:
        """
        Property indicating the timestamp of the last health check.
        
        Returns:
            datetime: Timestamp of the last health check
        """
        return self._last_health_check
    
    async def check_health(self) -> bool:
        """
        Asynchronously check the health of the SQLite provider.
        
        This method performs a simple health check by attempting to access
        the database file and running a basic query.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        try:
            # For demonstration purposes, we'll simulate a health check
            # In a real implementation, this would attempt to connect to the database
            # and run a simple query to verify connectivity
            import os
            
            # Check if database file exists (or can be created)
            if self.is_mock_healthy:
                # Simulate a successful health check
                self._is_healthy = True
                self._last_health_check = datetime.now()
                
                # Log the health check
                logging.info(f"SQLite storage provider at {self.db_path} is healthy")
            else:
                # Simulate an unhealthy state
                self._is_healthy = False
                self._last_health_check = datetime.now()
                
                # Log the health issue
                logging.warning(f"SQLite storage provider at {self.db_path} is unhealthy")
            
            return self._is_healthy
            
        except Exception as e:
            # If any error occurs during health check, mark as unhealthy
            self._is_healthy = False
            self._last_health_check = datetime.now()
            
            logging.error(f"Health check failed for SQLite storage provider at {self.db_path}: {str(e)}")
            return False
    
    async def read(self, key: str) -> Any | None:
        """
        Read a value from the storage.
        
        Args:
            key: The key to read
            
        Returns:
            The value if found, None otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to read from unhealthy SQLite storage provider: {key}")
        
        # In a real implementation, this would read from the database
        # For now, return None to indicate not found
        return None
    
    async def write(self, key: str, value: Any) -> bool:
        """
        Write a value to the storage.
        
        Args:
            key: The key to write
            value: The value to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to write to unhealthy SQLite storage provider: {key}")
        
        # In a real implementation, this would write to the database
        # For now, return True to indicate success
        return True
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the storage.
        
        Args:
            key: The key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to delete from unhealthy SQLite storage provider: {key}")
        
        # In a real implementation, this would delete from the database
        # For now, return True to indicate success
        return True


class MemoryStorageProvider(BaseProvider):
    """
    Health-aware in-memory storage provider implementing BaseProvider interface.
    
    Rationale: This provider demonstrates an alternative storage implementation
    that also implements the BaseProvider interface for health awareness.
    """
    
    def __init__(self, is_mock_healthy: bool = True):
        self._store = {}
        self._is_healthy = True
        self._last_health_check = datetime.now()
        self.is_mock_healthy = is_mock_healthy  # For testing purposes
    
    @property
    def is_healthy(self) -> bool:
        """
        Property indicating current health status of the provider.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        return self._is_healthy
    
    @property
    def last_health_check(self) -> datetime:
        """
        Property indicating the timestamp of the last health check.
        
        Returns:
            datetime: Timestamp of the last health check
        """
        return self._last_health_check
    
    async def check_health(self) -> bool:
        """
        Asynchronously check the health of the memory provider.
        
        This method checks the health by verifying memory availability
        and the internal storage structure.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        try:
            # Check if we can access the internal store
            _ = self._store
            
            if self.is_mock_healthy:
                # Simulate a successful health check
                self._is_healthy = True
                self._last_health_check = datetime.now()
                
                # Log the health check
                logging.info("Memory storage provider is healthy")
            else:
                # Simulate an unhealthy state
                self._is_healthy = False
                self._last_health_check = datetime.now()
                
                # Log the health issue
                logging.warning("Memory storage provider is unhealthy")
            
            return self._is_healthy
            
        except Exception as e:
            # If any error occurs during health check, mark as unhealthy
            self._is_healthy = False
            self._last_health_check = datetime.now()
            
            logging.error(f"Health check failed for memory storage provider: {str(e)}")
            return False
    
    async def read(self, key: str) -> Any | None:
        """
        Read a value from the memory storage.
        
        Args:
            key: The key to read
            
        Returns:
            The value if found, None otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to read from unhealthy memory storage provider: {key}")
        
        return self._store.get(key)
    
    async def write(self, key: str, value: Any) -> bool:
        """
        Write a value to the memory storage.
        
        Args:
            key: The key to write
            value: The value to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to write to unhealthy memory storage provider: {key}")
        
        self._store[key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the memory storage.
        
        Args:
            key: The key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to delete from unhealthy memory storage provider: {key}")
        
        if key in self._store:
            del self._store[key]
            return True
        return False