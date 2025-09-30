"""
Authentication API - Google OAuth + JWT
HIPAA-compliant authentication flow
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from authlib.integrations.starlette_client import OAuth
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import logging

from db import get_db_session, User, UserRole
from core.config import get_settings
from core.security.audit import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Configure OAuth
oauth = OAuth()
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Get current authenticated user from JWT token.
    Usage: user = Depends(get_current_user)
    """
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]

    try:
        # Decode JWT
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    # Get user from database
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    return user


async def require_role(role: UserRole):
    """
    Require specific user role.
    Usage: user = Depends(require_role(UserRole.ADMIN))
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role != role and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {role}"
            )
        return user

    return role_checker


@router.get("/login")
async def login(request: Request):
    """
    Initiate Google OAuth login flow.
    Redirects to Google consent screen.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
        )

    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Google OAuth callback handler.
    Creates or updates user, returns JWT token.
    """
    try:
        # Exchange authorization code for token
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')

        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            # Update existing user
            user.last_login = datetime.utcnow()
            user.name = name
            user.picture = picture
        else:
            # Create new user
            user = User(
                email=email,
                name=name,
                picture=picture,
                role=UserRole.USER,  # Default role
                last_login=datetime.utcnow()
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

        # Create JWT token
        access_token = create_access_token(
            data={"email": user.email, "role": user.role.value}
        )

        # Log audit event
        await log_audit_event(
            db=db,
            event_type="auth",
            action="login",
            user_id=user.id,
            result="success",
            details={"method": "google_oauth"},
            ip_address=request.client.host
        )

        logger.info(f"User logged in: {user.email}")

        # Return token (frontend will store it)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "role": user.role.value
            }
        }

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """
    Get current user info.
    Requires authentication.
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "role": user.role.value,
        "created_at": user.created_at.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "preferences": user.preferences
    }


@router.post("/logout")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Logout (invalidate token on client side).
    Server doesn't maintain session state.
    """
    # Log audit event
    await log_audit_event(
        db=db,
        event_type="auth",
        action="logout",
        user_id=user.id,
        result="success",
        ip_address=request.client.host
    )

    logger.info(f"User logged out: {user.email}")

    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(user: User = Depends(get_current_user)):
    """
    Refresh JWT token (extend expiration).
    """
    access_token = create_access_token(
        data={"email": user.email, "role": user.role.value}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
