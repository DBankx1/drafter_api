from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import jwt_validator
from app.models.dto.auth import TokenPayload
from app.infrastructure.database.db import get_db
from app.models.entity import BusinessEntity
from app.infrastructure.repository.business_repository import BusinessRepository
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenPayload:
    token = credentials.credentials
    token_data = jwt_validator.verify_token(token)
    
    logger.info(f"Authenticated user: {token_data.sub} ({token_data.email})")
    return token_data

async def get_current_active_user(
    current_user: TokenPayload = Depends(get_current_user)
) -> TokenPayload:
    # Add additional user validation if needed
    # For example, check if user is disabled in your database
    return current_user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[TokenPayload]:
    if credentials is None:
        return None
    
    try:
        return jwt_validator.verify_token(credentials.credentials)
    except HTTPException:
        return None

class RoleChecker:
    """
    Dependency class to check user roles.
    
    Usage:
        @app.get("/admin")
        def admin_route(current_user: TokenPayload = Depends(RoleChecker(["admin"]))):
            return {"message": "Admin access granted"}
    """
    
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if current_user.role not in self.allowed_roles:
            logger.warning(
                f"User {current_user.sub} attempted to access resource requiring roles "
                f"{self.allowed_roles} with role {current_user.role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user