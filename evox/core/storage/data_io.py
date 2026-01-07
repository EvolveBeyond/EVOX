"""
Storage module for EVOX framework
Provides data_io and data_intent functions
"""

from typing import Any, Dict, Optional
import asyncio
from ..intents import Intent

# Global data_io instance
class DataIO:
    """Simple data IO class for storage operations"""
    
    def __init__(self):
        self._store: Dict[str, Any] = {}
    
    async def read(self, key: str, intent: Intent = Intent.EPHEMERAL) -> Optional[Any]:
        """Read data by key"""
        return self._store.get(key)
    
    async def write(self, key: str, value: Any, intent: Intent = Intent.EPHEMERAL) -> bool:
        """Write data with key"""
        self._store[key] = value
        return True
    
    async def delete(self, key: str, intent: Intent = Intent.EPHEMERAL) -> bool:
        """Delete data by key"""
        if key in self._store:
            del self._store[key]
            return True
        return False

data_io = DataIO()
data_intent = Intent