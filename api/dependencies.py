"""
API Dependencies
================
FastAPI dependencies for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from typing import Optional
from api.models import User


async def get_current_user() -> Optional[User]:
    """
    Get current authenticated user.
    
    IMPORTANT: Authentication not implemented for v1.1.
    This dependency will fail loudly if called by protected endpoints.
    
    Returns:
        User object if authenticated, None otherwise
        
    Raises:
        HTTPException: Always raises 401 for v1.1 (auth not ready)
    """
    # v1.1: Authentication system not yet implemented
    # Protected endpoints must not be accessible until auth is ready
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication system not implemented in v1.1. Protected endpoints unavailable.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """
    Get current active user, raising exception if not authenticated.
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user

