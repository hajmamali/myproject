"""
MahouN Authentication Router

Provides JWT-based authentication with:
- Login/Logout
- Token refresh
- User management
- Role-based access control integration
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
import os
import logging

logger = logging.getLogger(__name__)

# Router setup
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "mahoun-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ============================================================================
# Models
# ============================================================================

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    permissions: list[str]
    is_active: bool
    created_at: datetime

class UserInDB(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    hashed_password: str
    role: str
    permissions: list[str]
    is_active: bool
    created_at: datetime

# ============================================================================
# Password & Token Utilities
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password for storing"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ============================================================================
# Database Operations (Mock - will be replaced with real DB)
# ============================================================================

# Mock database - در production با PostgreSQL جایگزین می‌شه
MOCK_USERS_DB = {
    "admin": UserInDB(
        id=1,
        username="admin",
        email="admin@mahoun.ai",
        full_name="System Administrator",
        hashed_password=get_password_hash("admin123"),
        role="ADMIN",
        permissions=["READ", "WRITE", "DELETE", "ADMIN"],
        is_active=True,
        created_at=datetime.utcnow()
    ),
    "developer": UserInDB(
        id=2,
        username="developer",
        email="dev@mahoun.ai",
        full_name="Developer User",
        hashed_password=get_password_hash("dev123"),
        role="ANALYST",
        permissions=["READ", "WRITE"],
        is_active=True,
        created_at=datetime.utcnow()
    ),
    "user": UserInDB(
        id=3,
        username="user",
        email="user@mahoun.ai",
        full_name="Regular User",
        hashed_password=get_password_hash("user123"),
        role="USER",
        permissions=["READ"],
        is_active=True,
        created_at=datetime.utcnow()
    )
}

async def get_user_by_username(username: str) -> Optional[UserInDB]:
    """Get user from database by username"""
    return MOCK_USERS_DB.get(username)

async def get_user_by_id(user_id: int) -> Optional[UserInDB]:
    """Get user from database by ID"""
    for user in MOCK_USERS_DB.values():
        if user.id == user_id:
            return user
    return None

# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "access":
            raise credentials_exception
            
        token_data = TokenData(username=username, user_id=user_id)
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    user = await get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """Get current active user (must be active)"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

async def require_admin(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """Require admin role"""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_analyst(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """Require analyst or admin role"""
    if current_user.role not in ["ADMIN", "ANALYST"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst or Admin access required"
        )
    return current_user

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with username and password
    
    Returns JWT access token and refresh token
    
    **Test Users:**
    - admin / admin123 (Full access)
    - developer / dev123 (Analyst access)
    - user / user123 (Read-only access)
    """
    user = await get_user_by_username(form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب کاربری غیرفعال است"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    logger.info(f"User {user.username} logged in successfully")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_username(username)
    if user is None or not user.is_active:
        raise credentials_exception
    
    # Create new tokens
    new_access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Get current authenticated user information
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        permissions=current_user.permissions,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

@router.post("/logout")
async def logout(current_user: UserInDB = Depends(get_current_active_user), token: str = Depends(oauth2_scheme)):
    """
    Logout current user
    
    Revokes the current access token by adding it to the blacklist.
    For production, this uses Redis. In development, uses in-memory storage.
    """
    # Import blacklist manager
    from api.middleware.auth import blacklist_manager
    
    # Revoke token
    await blacklist_manager.revoke_token(token, expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    logger.info(f"User {current_user.username} logged out and token revoked")
    
    return {
        "message": "با موفقیت خارج شدید",
        "success": True
    }

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """
    Register a new user (disabled in production - admin only)
    """
    # Check if username exists
    if await get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نام کاربری قبلاً استفاده شده است"
        )
    
    # Create new user
    new_user = UserInDB(
        id=len(MOCK_USERS_DB) + 1,
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role="USER",
        permissions=["READ"],
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    MOCK_USERS_DB[user_data.username] = new_user
    
    logger.info(f"New user registered: {user_data.username}")
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        permissions=new_user.permissions,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )

@router.get("/test/admin")
async def test_admin_access(current_user: UserInDB = Depends(require_admin)):
    """Test endpoint requiring admin access"""
    return {"message": "Admin access granted", "user": current_user.username}

@router.get("/test/analyst")
async def test_analyst_access(current_user: UserInDB = Depends(require_analyst)):
    """Test endpoint requiring analyst access"""
    return {"message": "Analyst access granted", "user": current_user.username}
