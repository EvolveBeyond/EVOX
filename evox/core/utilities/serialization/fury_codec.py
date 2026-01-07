"""
Fury Binary Serialization Codec for EVOX
Provides high-performance binary serialization as optional backend.
"""

from typing import Any, Type, TypeVar, Optional, Dict
import logging
from datetime import datetime
from ...data.intents.intent_system import Intent

try:
    import pyfury as fury
    HAS_FURY = True
except ImportError:
    HAS_FURY = False
    fury = None

from ..models.core_models import CoreMessage

# Optional encryption support
try:
    from cryptography.fernet import Fernet
    HAS_ENCRYPTION = True
except ImportError:
    HAS_ENCRYPTION = False
    Fernet = None

T = TypeVar('T')
logger = logging.getLogger(__name__)

class FuryNotAvailable(Exception):
    """Raised when Fury serialization is requested but not available"""
    pass

class FuryCodec:
    """High-performance binary serialization using Fury/PyFury"""
    
    def __init__(self):
        self.fury_instance = None
        self._registered_classes = set()
        self.stats = {
            "serializations": 0,
            "deserializations": 0,
            "errors": 0,
            "encrypted_serializations": 0,
            "decrypted_deserializations": 0
        }
        
        # Encryption support
        self.encryption_key = None
        self.cipher = None
        
        # Use the module-level HAS_FURY variable
        global HAS_FURY
        if HAS_FURY:
            try:
                self.fury_instance = fury.Fury()
                logger.info("Fury serialization initialized successfully")
            except Exception as e:
                logger.warning(f"Fury initialization failed: {e}")
                HAS_FURY = False  # Update module-level variable
        else:
            logger.info("Fury not available, using fallback serialization")
    
    def set_encryption_key(self, key: Optional[bytes] = None):
        """Set encryption key for the codec"""
        global HAS_ENCRYPTION
        if not HAS_ENCRYPTION:
            logger.warning("Encryption not available, cryptography package not installed")
            return
        
        if key is None:
            key = Fernet.generate_key()
        
        self.encryption_key = key
        self.cipher = Fernet(key)
        logger.info("Encryption key set for Fury codec")
    
    def _should_encrypt(self, intent: Intent) -> bool:
        """Determine if data should be encrypted based on intent"""
        return intent == Intent.CRITICAL
    
    def serialize(self, obj: Any, intent: Intent = Intent.STANDARD) -> bytes:
        """Serialize object to bytes using Fury"""
        global HAS_FURY
        if not HAS_FURY:
            raise FuryNotAvailable("Fury serialization not available")
        
        try:
            data = self.fury_instance.serialize(obj)
            self.stats["serializations"] += 1
            
            # Apply encryption based on intent
            if self._should_encrypt(intent) and self.cipher:
                data = self.cipher.encrypt(data)
                self.stats["encrypted_serializations"] += 1
                
            return data
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes, expected_type: Optional[Type[T]] = None, intent: Intent = Intent.STANDARD) -> T:
        """Deserialize bytes to object using Fury"""
        global HAS_FURY
        if not HAS_FURY:
            raise FuryNotAvailable("Fury deserialization not available")
        
        # Try to decrypt if data was encrypted
        if self._should_encrypt(intent) and self.cipher:
            try:
                data = self.cipher.decrypt(data)
                self.stats["decrypted_deserializations"] += 1
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                raise
        
        try:
            obj = self.fury_instance.deserialize(data)
            self.stats["deserializations"] += 1
            
            if expected_type and not isinstance(obj, expected_type):
                logger.warning(f"Deserialized type mismatch: expected {expected_type}, got {type(obj)}")
            
            return obj
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Deserialization failed: {e}")
            raise
    
    def register_class(self, cls: Type):
        """Register class for optimized serialization"""
        global HAS_FURY
        if not HAS_FURY:
            return
            
        if cls not in self._registered_classes:
            try:
                self.fury_instance.register_class(cls)
                self._registered_classes.add(cls)
                logger.debug(f"Registered class for Fury serialization: {cls.__name__}")
            except Exception as e:
                logger.warning(f"Failed to register class {cls.__name__}: {e}")

# Global codec instance
fury_codec = FuryCodec()

def serialize_object(obj: Any, intent: Intent = Intent.STANDARD) -> bytes:
    """Convenience function for object serialization"""
    return fury_codec.serialize(obj, intent=intent)

def deserialize_object(data: bytes, expected_type: Optional[Type[T]] = None, intent: Intent = Intent.STANDARD) -> T:
    """Convenience function for object deserialization"""
    return fury_codec.deserialize(data, expected_type, intent=intent)

# Export public API
__all__ = [
    "FuryCodec",
    "FuryNotAvailable", 
    "fury_codec",
    "serialize_object",
    "deserialize_object"
]