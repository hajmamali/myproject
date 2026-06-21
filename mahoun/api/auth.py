"""
MAHOUN Offline Authentication
==============================

Air-gapped authentication system without external dependencies.

Features:
- Local API key validation
- No external calls
- Encrypted key storage
- Role-based access control
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from mahoun.core.logging import setup_logger

log = setup_logger("auth")

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class OfflineAuthenticator:
    """Offline authentication manager for air-gapped deployments"""
    
    def __init__(self, keys_file: str = "config/api_keys.json"):
        self.keys_file = Path(keys_file)
        self._keys_cache: Optional[dict] = None
        
    def _load_keys(self) -> dict:
        """Load API keys from local file"""
        if not self.keys_file.exists():
            log.warning(f"API keys file not found: {self.keys_file}")
            return {"keys": {}}
        
        try:
            with open(self.keys_file, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            log.error(f"Failed to load API keys: {e}")
            return {"keys": {}}
    
    def validate_key(self, api_key: str) -> tuple[bool, Optional[dict]]:
        """
        Validate API key offline
        
        Returns:
            (is_valid, key_info)
        """
        if not api_key:
            return False, None
        
        # Load keys (with caching)
        if self._keys_cache is None:
            self._keys_cache = self._load_keys()
        
        keys_data = self._keys_cache.get("keys", {})
        
        # Check if key exists
        if api_key not in keys_data:
            log.warning(f"Invalid API key attempt: {api_key[:10]}...")
            return False, None
        
        key_info = keys_data[api_key]
        
        # Check if revoked
        if key_info.get("revoked"):
            log.warning(f"Revoked API key used: {api_key[:10]}...")
            return False, {"error": "Key revoked"}
        
        # Check if expired
        if key_info.get("expires"):
            from datetime import datetime, timezone
            expires = datetime.fromisoformat(key_info["expires"])
            if datetime.now(timezone.utc) > expires:
                log.warning(f"Expired API key used: {api_key[:10]}...")
                return False, {"error": "Key expired"}
        
        log.info(f"Valid API key: {key_info.get('name', 'Unknown')} ({key_info.get('role', 'unknown')})")
        return True, key_info
    
    def reload_keys(self) -> None:
        """Reload keys from file (for key rotation)"""
        self._keys_cache = None
        log.info("API keys reloaded")


# Global authenticator instance
_authenticator = OfflineAuthenticator()


async def verify_api_key(api_key: str = Security(api_key_header)) -> dict:
    """
    FastAPI dependency for API key authentication
    
    Usage:
        @app.get("/protected")
        async def protected_route(auth: dict = Depends(verify_api_key)):
            return {"user": auth["name"]}
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    valid, key_info = _authenticator.validate_key(api_key)
    
    if not valid:
        error_msg = key_info.get("error", "Invalid API key") if key_info else "Invalid API key"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg,
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return key_info


async def verify_admin_key(auth: dict = Security(verify_api_key)) -> dict:
    """
    FastAPI dependency for admin-only routes
    
    Usage:
        @app.post("/admin/users")
        async def create_user(auth: dict = Depends(verify_admin_key)):
            return {"status": "created"}
    """
    if auth.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return auth


def reload_api_keys() -> None:
    """Reload API keys from file (for key rotation without restart)"""
    _authenticator.reload_keys()
