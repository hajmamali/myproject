"""
Authentication Dependencies
===========================
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


async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Require admin role.
    
    Args:
        current_user: Current user
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_analyst(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Require analyst role.
    
    Args:
        current_user: Current user
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user is not analyst
    """
    if current_user.role not in ["admin", "analyst"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst access required"
        )
    return current_user


async def get_optional_user() -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    
    IMPORTANT: In v1.1, authentication is not implemented.
    This dependency raises an exception to prevent misuse.
    
    Returns:
        User object if authenticated, None otherwise
        
    Raises:
        RuntimeError: Always raises in v1.1 (optional auth not ready)
    """
    # v1.1: Optional authentication not yet implemented
    # Endpoints using this must be reviewed before enabling
    raise RuntimeError(
        "Optional authentication dependency not implemented in v1.1. "
        "Endpoints using get_optional_user() must be disabled or refactored."
    )

