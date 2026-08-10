"""
Authentication Middleware

Provides JWT token verification, request logging, and CORS configuration.
"""

import time
import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
import os

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "mahoun-secret-key-change-in-production")
ALGORITHM = "HS256"

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/health",
    "/health/detailed",
    "/health/v2",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/metrics/prometheus",
    "/system/health",
    "/api/system/health",
}

# Endpoints that should skip auth check (starts with)
PUBLIC_PREFIXES = [
    "/static/",
    "/assets/",
]


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication Middleware
    
    Verifies JWT tokens on protected endpoints and adds user context to request state.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "توکن احراز هویت یافت نشد",
                    "detail": "Authorization header missing"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate Bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "فرمت توکن نامعتبر است",
                    "detail": "Invalid Authorization header format"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = parts[1]
        
        # Verify token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check token type
            token_type = payload.get("type")
            if token_type != "access":
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "unauthorized",
                        "message": "نوع توکن نامعتبر است",
                        "detail": "Invalid token type"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Add user info to request state
            request.state.user_id = payload.get("user_id")
            request.state.username = payload.get("sub")
            request.state.role = payload.get("role")
            request.state.authenticated = True
            
            logger.debug(f"Authenticated request from user {request.state.username}")
            
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "token_expired",
                    "message": "توکن منقضی شده است",
                    "detail": "Token has expired"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "invalid_token",
                    "message": "توکن نامعتبر است",
                    "detail": "Token validation failed"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Continue with request
        response = await call_next(request)
        return response
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public"""
        # Check exact matches
        if path in PUBLIC_ENDPOINTS:
            return True
        
        # Check prefix matches
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request Logging Middleware
    
    Logs all requests with timing, user info, and response status.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get user info if authenticated
        username = getattr(request.state, "username", "anonymous")
        user_id = getattr(request.state, "user_id", None)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "username": username,
            "user_id": user_id,
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "")[:100],
        }
        
        # Log level based on status code
        if response.status_code >= 500:
            logger.error(f"Request failed: {log_data}")
        elif response.status_code >= 400:
            logger.warning(f"Client error: {log_data}")
        else:
            logger.info(f"Request: {log_data}")
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(duration_ms)
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "")
        
        return response


class CORSConfigMiddleware:
    """
    CORS Configuration Helper
    
    Provides configured CORS settings for frontend integration.
    """
    
    @staticmethod
    def get_cors_config():
        """Get CORS configuration based on environment"""
        env = os.getenv("MAHOUN_ENV", "development")
        
        if env == "production":
            # Production: Strict CORS
            return {
                "allow_origins": [
                    "https://mahoun.ai",
                    "https://studio.mahoun.ai",
                    "https://portal.mahoun.ai",
                ],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Authorization",
                    "Content-Type",
                    "X-Request-ID",
                    "Accept",
                    "Origin",
                ],
                "expose_headers": [
                    "X-Process-Time",
                    "X-Request-ID",
                ],
                "max_age": 600,
            }
        else:
            # Development: Permissive CORS
            return {
                "allow_origins": [
                    "http://localhost:5173",
                    "http://localhost:3000",
                    "http://127.0.0.1:5173",
                    "http://127.0.0.1:3000",
                ],
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
                "expose_headers": [
                    "X-Process-Time",
                    "X-Request-ID",
                ],
                "max_age": 3600,
            }


# Token Blacklist Management (using Redis in production)
class TokenBlacklistManager:
    """
    Token Blacklist Manager
    
    Manages revoked tokens using Redis or in-memory storage.
    """
    
    def __init__(self):
        self._blacklist = set()  # In-memory fallback
        self._redis_client = None
    
    async def initialize(self, redis_client=None):
        """Initialize with Redis client if available"""
        self._redis_client = redis_client
        logger.info("Token blacklist manager initialized")
    
    async def revoke_token(self, token: str, expires_in: int = 86400):
        """
        Revoke a token
        
        Args:
            token: JWT token to revoke
            expires_in: TTL in seconds (default 24 hours)
        """
        if self._redis_client:
            # Store in Redis with TTL
            await self._redis_client.setex(
                f"blacklist:{token}",
                expires_in,
                "1"
            )
            logger.info(f"Token revoked in Redis (TTL: {expires_in}s)")
        else:
            # Fallback to in-memory
            self._blacklist.add(token)
            logger.info("Token revoked in memory")
    
    async def is_revoked(self, token: str) -> bool:
        """Check if token is revoked"""
        if self._redis_client:
            result = await self._redis_client.get(f"blacklist:{token}")
            return result is not None
        else:
            return token in self._blacklist
    
    async def clear_blacklist(self):
        """Clear all revoked tokens (development only)"""
        if self._redis_client:
            # Clear Redis keys
            keys = await self._redis_client.keys("blacklist:*")
            if keys:
                await self._redis_client.delete(*keys)
        else:
            self._blacklist.clear()
        logger.warning("Token blacklist cleared")


# Global blacklist manager instance
blacklist_manager = TokenBlacklistManager()


# Helper functions for dependency injection
async def get_current_user_from_request(request: Request) -> dict:
    """
    Extract current user from request state
    
    To be used as a FastAPI dependency.
    """
    if not getattr(request.state, "authenticated", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="احراز هویت نشده",
        )
    
    return {
        "user_id": request.state.user_id,
        "username": request.state.username,
        "role": request.state.role,
    }


async def require_role(request: Request, required_role: str) -> bool:
    """
    Check if user has required role
    
    Args:
        request: FastAPI request
        required_role: Required role name (ADMIN, ANALYST, USER)
    
    Returns:
        True if user has required role
    
    Raises:
        HTTPException: If user doesn't have required role
    """
    user = await get_current_user_from_request(request)
    
    role_hierarchy = {
        "ADMIN": 3,
        "ANALYST": 2,
        "USER": 1,
    }
    
    user_level = role_hierarchy.get(user["role"], 0)
    required_level = role_hierarchy.get(required_role, 999)
    
    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"نقش {required_role} مورد نیاز است",
        )
    
    return True
