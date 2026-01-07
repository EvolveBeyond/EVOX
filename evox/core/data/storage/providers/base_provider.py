"""
Common components for EVOX framework including base provider interfaces
"""

from abc import abstractmethod
from datetime import datetime
from typing import Protocol
import typing


@typing.runtime_checkable
class BaseProvider(Protocol):
    """
    Base provider protocol for health-aware components in EVOX.
    
    Rationale: This protocol establishes a standard interface for all providers
    that need to be health-aware in the EVOX framework. By implementing this
    protocol, components can be monitored for health status and participate in
    the degraded mode operations when needed.
    """
    
    @property
    def is_healthy(self) -> bool:
        """
        Property indicating current health status of the provider.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        ...
    
    @property
    def last_health_check(self) -> datetime:
        """
        Property indicating the timestamp of the last health check.
        
        Returns:
            datetime: Timestamp of the last health check
        """
        ...
    
    @abstractmethod
    async def check_health(self) -> bool:
        """
        Asynchronously check the health of the provider.
        
        This method should perform a comprehensive health check on the provider
        and return the result. The implementation should update the is_healthy
        property and last_health_check timestamp.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        ...