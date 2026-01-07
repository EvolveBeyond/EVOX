"""
EVOX Core Serialization System
==============================

High-performance serialization for the EVOX framework.
This module provides fast binary serialization with intent-aware processing.

Features:
- Binary serialization with multiple backends
- Intent-aware processing (encryption, compression based on data intent)
- Performance-optimized for microservices communication
"""

from typing import Any, Type, TypeVar, Optional, Dict, Protocol
import logging
import pickle
import json
from datetime import datetime
from enum import Enum

from ..data.intents.intent_system import Intent

T = TypeVar('T')
logger = logging.getLogger(__name__)


class SerializationBackend(Enum):
    """Supported serialization backends"""
    PICKLE = "pickle"
    JSON = "json"
    CUSTOM = "custom"


class SerializerProtocol(Protocol):
    """Protocol for serialization backends"""
    
    def serialize(self, obj: Any) -> bytes: ...
    def deserialize(self, data: bytes, expected_type: Optional[Type[T]] = None) -> T: ...


class CoreSerializer:
    """Core serialization system with intent-aware processing"""
    
    def __init__(self):
        self.stats = {
            "serializations": 0,
            "deserializations": 0,
            "compression_applied": 0,
            "encryption_applied": 0,
            "errors": 0
        }
        self._backends: Dict[SerializationBackend, SerializerProtocol] = {}
        self._encryption_key: Optional[bytes] = None
    
    def serialize(
        self, 
        obj: Any, 
        intent: Intent = Intent.STANDARD,
        backend: SerializationBackend = SerializationBackend.PICKLE
    ) -> bytes:
        """
        Serialize object with intent-aware processing.
        
        Args:
            obj: Object to serialize
            intent: Intent that determines processing strategy
            backend: Serialization backend to use
            
        Returns:
            Serialized bytes
        """
        try:
            # Select appropriate serializer
            if backend == SerializationBackend.PICKLE:
                serialized_data = pickle.dumps(obj)
            elif backend == SerializationBackend.JSON:
                json_str = json.dumps(obj, default=self._json_serializer)
                serialized_data = json_str.encode('utf-8')
            else:
                raise ValueError(f"Unsupported serialization backend: {backend}")
            
            self.stats["serializations"] += 1
            
            # Apply intent-based processing
            if self._should_compress(intent):
                serialized_data = self._compress_data(serialized_data)
            
            if self._should_encrypt(intent):
                serialized_data = self._encrypt_data(serialized_data)
            
            return serialized_data
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Serialization failed: {e}")
            raise
    
    def deserialize(
        self,
        data: bytes,
        expected_type: Optional[Type[T]] = None,
        intent: Intent = Intent.STANDARD,
        backend: SerializationBackend = SerializationBackend.PICKLE
    ) -> T:
        """
        Deserialize object with intent-aware processing.
        
        Args:
            data: Serialized data
            expected_type: Expected type of deserialized object
            intent: Intent that determines processing strategy
            backend: Serialization backend to use
            
        Returns:
            Deserialized object
        """
        try:
            # Apply intent-based processing (reverse)
            if self._should_encrypt(intent):
                data = self._decrypt_data(data)
            
            if self._should_compress(intent):
                data = self._decompress_data(data)
            
            # Select appropriate deserializer
            if backend == SerializationBackend.PICKLE:
                obj = pickle.loads(data)
            elif backend == SerializationBackend.JSON:
                json_str = data.decode('utf-8')
                obj = json.loads(json_str, object_hook=self._json_deserializer)
            else:
                raise ValueError(f"Unsupported serialization backend: {backend}")
            
            self.stats["deserializations"] += 1
            
            # Validate type if expected
            if expected_type and not isinstance(obj, expected_type):
                logger.warning(f"Deserialized type mismatch: expected {expected_type}, got {type(obj)}")
            
            return obj
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Deserialization failed: {e}")
            raise
    
    def _should_compress(self, intent: Intent) -> bool:
        """Determine if data should be compressed based on intent."""
        return intent in [Intent.EPHEMERAL, Intent.LAZY]
    
    def _should_encrypt(self, intent: Intent) -> bool:
        """Determine if data should be encrypted based on intent."""
        return intent in [Intent.CRITICAL, Intent.SENSITIVE]
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        try:
            import gzip
            compressed = gzip.compress(data)
            self.stats["compression_applied"] += 1
            return compressed
        except ImportError:
            logger.warning("gzip not available, skipping compression")
            return data
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data using gzip."""
        try:
            import gzip
            return gzip.decompress(data)
        except ImportError:
            logger.warning("gzip not available, skipping decompression")
            return data
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data if encryption key is set."""
        if self._encryption_key:
            try:
                from cryptography.fernet import Fernet
                cipher = Fernet(self._encryption_key)
                encrypted = cipher.encrypt(data)
                self.stats["encryption_applied"] += 1
                return encrypted
            except ImportError:
                logger.warning("cryptography package not available, skipping encryption")
        return data
    
    def _decrypt_data(self, data: bytes) -> bytes:
        """Decrypt data if encryption key is set."""
        if self._encryption_key:
            try:
                from cryptography.fernet import Fernet
                cipher = Fernet(self._encryption_key)
                return cipher.decrypt(data)
            except ImportError:
                logger.warning("cryptography package not available, skipping decryption")
        return data
    
    def _json_serializer(self, obj: Any) -> Dict[str, Any]:
        """Custom JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _json_deserializer(self, d: Dict[str, Any]) -> Any:
        """Custom JSON deserializer for non-standard types."""
        if "__datetime__" in d:
            return datetime.fromisoformat(d["__datetime__"])
        return d
    
    def set_encryption_key(self, key: Optional[bytes]):
        """Set encryption key for the serializer."""
        self._encryption_key = key
        if key:
            logger.info("Encryption key set for serializer")


# Global serializer instance
serializer = CoreSerializer()


# Convenience functions
def serialize_object(
    obj: Any, 
    intent: Intent = Intent.STANDARD,
    backend: SerializationBackend = SerializationBackend.PICKLE
) -> bytes:
    """Convenience function for object serialization."""
    return serializer.serialize(obj, intent, backend)


def deserialize_object(
    data: bytes,
    expected_type: Optional[Type[T]] = None,
    intent: Intent = Intent.STANDARD,
    backend: SerializationBackend = SerializationBackend.PICKLE
) -> T:
    """Convenience function for object deserialization."""
    return serializer.deserialize(data, expected_type, intent, backend)


def get_serializer() -> CoreSerializer:
    """Get the global serializer instance."""
    return serializer


__all__ = [
    "CoreSerializer",
    "SerializationBackend",
    "SerializerProtocol",
    "serializer",
    "serialize_object",
    "deserialize_object",
    "get_serializer"
]