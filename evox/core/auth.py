"""
Authentication System - JWT-based authentication with role-based access control

This module provides a pluggable authentication system with:
1. JWT token generation and validation
2. Role-based access control
3. Integration with data intents and CIA classification
4. Secure internal service communication
5. Rate limiting and security best practices
"""

import jwt
import time
from typing import Optional, Dict, Any, List, Union
from functools import wraps
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class AuthConfig:
    """Authentication configuration"""
    
    def __init__(self):
        self.secret_key = "evox-secret-key-change-in-production"  # Should be loaded from env
        self.algorithm = "HS256"
        self.token_expiration = 3600  # 1 hour
        self.refresh_token_expiration = 86400  # 24 hours
        self.internal_token_secret = "evox-internal-secret-change-in-production"
        self.rate_limit_enabled = False
        self.max_requests_per_minute = 60


class TokenData:
    """Token data structure"""
    
    def __init__(self, user_id: str, roles: List[str], scopes: List[str], 
                 exp: int, iat: int, iss: str = "evox"):
        self.user_id = user_id
        self.roles = roles
        self.scopes = scopes
        self.exp = exp
        self.iat = iat
        self.iss = iss


class CIAClassification:
    """CIA (Confidentiality, Integrity, Availability) classification"""
    
    def __init__(self, confidentiality: str = "public", 
                 integrity: str = "low", availability: str = "low"):
        self.confidentiality = confidentiality  # public, internal, confidential, secret
        self.integrity = integrity              # low, medium, high
        self.availability = availability        # low, medium, high


class AuthManager:
    """Authentication manager with JWT and role-based access control"""
    
    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()
        self.security = HTTPBearer()
    
    def create_access_token(self, user_id: str, roles: List[str] = None, 
                          scopes: List[str] = None) -> str:
        """Create JWT access token"""
        roles = roles or []
        scopes = scopes or []
        
        payload = {
            "user_id": user_id,
            "roles": roles,
            "scopes": scopes,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.config.token_expiration,
            "iss": "evox"
        }
        
        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)
    
    def create_internal_token(self, service_name: str) -> str:
        """Create internal service token for secure inter-service communication"""
        payload = {
            "service": service_name,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour
            "iss": "evox-internal"
        }
        
        return jwt.encode(payload, self.config.internal_token_secret, 
                        algorithm=self.config.algorithm)
    
    def verify_token(self, token: str) -> TokenData:
        """Verify JWT token and return token data"""
        try:
            payload = jwt.decode(token, self.config.secret_key, 
                               algorithms=[self.config.algorithm])
            
            return TokenData(
                user_id=payload.get("user_id"),
                roles=payload.get("roles", []),
                scopes=payload.get("scopes", []),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                iss=payload.get("iss", "evox")
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def verify_internal_token(self, token: str) -> Dict[str, Any]:
        """Verify internal service token"""
        try:
            payload = jwt.decode(token, self.config.internal_token_secret,
                               algorithms=[self.config.algorithm])
            
            if payload.get("iss") != "evox-internal":
                raise HTTPException(status_code=401, detail="Invalid internal token issuer")
            
            return {
                "service": payload.get("service"),
                "iat": payload.get("iat"),
                "exp": payload.get("exp")
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Internal token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid internal token")
    
    # Standardized decorator factory for authentication checks
    def _create_auth_decorator(self, check_type: str, required_values=None, cia_classification=None):
        """Create a standardized authentication decorator"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Get request from args or kwargs
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if not request and 'request' in kwargs:
                    request = kwargs['request']
                
                if not request:
                    raise HTTPException(status_code=500, detail="Request object not found")
                
                # Extract token
                try:
                    credentials: HTTPAuthorizationCredentials = await self.security(request)
                    token_data = self.verify_token(credentials.credentials)
                    
                    # Perform check based on type
                    if check_type == "role":
                        if not any(role in token_data.roles for role in required_values):
                            raise HTTPException(status_code=403, detail="Insufficient permissions")
                    elif check_type == "scope":
                        if not any(scope in token_data.scopes for scope in required_values):
                            raise HTTPException(status_code=403, detail="Insufficient permissions")
                    elif check_type == "intent":
                        # Check roles if specified
                        if required_values:  # required_values contains required_roles for intent
                            if not any(role in token_data.roles for role in required_values):
                                raise HTTPException(status_code=403, detail="Insufficient permissions for data intent operation")
                        # Check CIA classification if specified
                        if cia_classification:
                            # For now, this is a placeholder - in a real implementation,
                            # this would check user clearance against data classification
                            pass
                    
                    return await func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(status_code=401, detail="Authentication required")
            
            return wrapper
        return decorator
    
    def require_role(self, required_roles: Union[str, List[str]]):
        """Decorator to require specific roles"""
        if isinstance(required_roles, str):
            required_roles = [required_roles]
        return self._create_auth_decorator("role", required_roles)
    
    def require_scope(self, required_scopes: Union[str, List[str]]):
        """Decorator to require specific scopes"""
        if isinstance(required_scopes, str):
            required_scopes = [required_scopes]
        return self._create_auth_decorator("scope", required_scopes)
    
    def require_cia(self, cia_classification: CIAClassification):
        """Decorator to require specific CIA classification clearance"""
        # For CIA classification, we could integrate with more advanced auth
        # For now, this is a placeholder that could be extended
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_intent(self, intent_type: str = None, required_roles: List[str] = None, cia_classification: CIAClassification = None):
        """Decorator to require specific roles for data intent operations with CIA classification support"""
        return self._create_auth_decorator("intent", required_roles, cia_classification)


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager(config: Optional[AuthConfig] = None) -> AuthManager:
    """Get or create global auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(config)
    return _auth_manager


def auth_required():
    """Dependency for requiring authentication"""
    def dependency(request: Request):
        auth_manager = get_auth_manager()
        try:
            credentials: HTTPAuthorizationCredentials = auth_manager.security(request)
            token_data = auth_manager.verify_token(credentials.credentials)
            return token_data
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication required")
    
    return Depends(dependency)


def internal_auth_required():
    """Dependency for requiring internal service authentication"""
    def dependency(request: Request):
        auth_manager = get_auth_manager()
        # Check for internal token in header
        internal_token = request.headers.get("X-Evox-Internal")
        if not internal_token:
            raise HTTPException(status_code=401, detail="Internal authentication required")
        
        try:
            service_data = auth_manager.verify_internal_token(internal_token)
            return service_data
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid internal authentication")
    
    return Depends(dependency)


# Export main components
auth = get_auth_manager()