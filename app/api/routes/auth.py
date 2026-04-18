from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.middlewares.auth import get_current_user
from app.services.auth_service import AuthService
from app.infrastructure.database.db import get_db
from app.models.dto.auth import LoginRequest, RefreshTokenRequest, SignUpRequest, SignUpResponse, TokenPayload, TokenResponse, UserResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"], prefix="/auth")

@router.post("/signup", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    signup_data: SignUpRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with Supabase Auth.
    """
    try:
        auth_service = AuthService(db)
        return await auth_service.signup_user(signup_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    """
    try:
        auth_service = AuthService(db)
        return await auth_service.login_user(login_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token.
    """
    try:
        auth_service = AuthService(db)
        return await auth_service.refresh_token(refresh_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/logout")
async def logout(current_user: TokenPayload = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Logout current user (handled client-side by clearing tokens).
    """
    try:
        auth_service = AuthService(db)
        return await auth_service.logout_user(current_user)
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        # Don't fail logout even if Supabase call fails
        return {"message": "Logged out"}