"""
Dependency Injection - Lazy provider-based injection system

Provides lazy resolution of dependencies without eager instantiation.
Supports service proxies, database connections, and configuration.
"""
from typing import Optional
from functools import wraps


class Inject:
    """
    Lazy provider-based dependency injection system
    
    Provides lazy resolution of dependencies without eager instantiation.
    """
    
    @staticmethod
    def service(service_name: str):
        """
        Inject a service proxy lazily with zero-cost initialization
        
        Args:
            service_name: Name of the service to inject
            
        Returns:
            Lazy service proxy resolver
        """
        from evox.core.proxy import ServiceProxy
        
        class LazyServiceProxy:
            def __init__(self, service_name):
                self.service_name = service_name
                self._proxy = None
            
            def __getattr__(self, method_name):
                # Check for override first
                override_key = f"service:{self.service_name}"
                if override_key in _overrides:
                    return getattr(_overrides[override_key], method_name)
                
                # Zero-cost until first resolution
                if self._proxy is None:
                    self._proxy = ServiceProxy.get_instance(self.service_name)
                return getattr(self._proxy, method_name)
            
            def __call__(self, *args, **kwargs):
                # Check for override first
                override_key = f"service:{self.service_name}"
                if override_key in _overrides:
                    return _overrides[override_key](*args, **kwargs)
                
                # Zero-cost until first resolution
                if self._proxy is None:
                    self._proxy = ServiceProxy.get_instance(self.service_name)
                return self._proxy(*args, **kwargs)
        
        return LazyServiceProxy(service_name)
    
    @staticmethod
    def db():
        """
        Inject database connection lazily
        
        Returns:
            Lazy database proxy resolver
        """
        # Return a lazy database proxy that resolves at call time
        from evox.core.storage import data_io
        
        class LazyDBProxy:
            def __init__(self):
                self._initialized = False
            
            def __getattr__(self, attr):
                # Check for override first
                if 'db' in _overrides:
                    return getattr(_overrides['db'], attr)
                
                # Lazy initialization on first access
                if not self._initialized:
                    # In a real implementation, this would initialize the DB connection
                    self._initialized = True
                # Delegate to data_io for actual operations
                return getattr(data_io, attr)
        
        return LazyDBProxy()
    
    @staticmethod
    def config(section: Optional[str] = None):
        """
        Inject configuration lazily
        
        Args:
            section: Configuration section to inject
            
        Returns:
            Lazy configuration resolver
        """
        from evox.core.config import get_config as _get_config
        
        class LazyConfigProxy:
            def __init__(self, section=None):
                self.section = section
                self._cache = {}
            
            def __getattr__(self, key):
                # Check for override first
                override_key = f"config:{self.section}" if self.section else "config"
                if override_key in _overrides:
                    config_override = _overrides[override_key]
                    return getattr(config_override, key) if hasattr(config_override, key) else config_override.get(key)
                
                # Return configuration value lazily
                cache_key = f"{self.section}.{key}" if self.section else key
                if cache_key not in self._cache:
                    self._cache[cache_key] = _get_config(cache_key)
                return self._cache[cache_key]
            
            def get(self, key: str, default=None):
                """Get configuration value with default"""
                # Check for override first
                override_key = f"config:{self.section}" if self.section else "config"
                if override_key in _overrides:
                    config_override = _overrides[override_key]
                    return config_override.get(key, default) if hasattr(config_override, 'get') else getattr(config_override, key, default)
                
                cache_key = f"{self.section}.{key}" if self.section else key
                if cache_key not in self._cache:
                    self._cache[cache_key] = _get_config(cache_key, default)
                return self._cache[cache_key]
        
        return LazyConfigProxy(section)


# Global inject instance
inject = Inject()


# Provider override mechanism for testing
_overrides = {}

def override(provider, mock_value):
    """Override a provider for testing"""
    _overrides[provider] = mock_value

def reset_overrides():
    """Reset all overrides"""
    global _overrides
    _overrides.clear()