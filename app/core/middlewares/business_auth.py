import json
from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from .auth import get_current_user, get_optional_user
from app.models.dto.auth import TokenPayload
from app.infrastructure.database.db import get_db
from app.infrastructure.repository.business_repository import BusinessRepository
from app.models.entity import BusinessEntity
import logging

logger = logging.getLogger(__name__)


async def get_user_business(
        current_user: TokenPayload = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> BusinessEntity:

    repo = BusinessRepository(db)
    business = await repo.get_by_user_id(current_user.sub)
    
    if not business:
        logger.warning(f"Business not found for user {current_user.sub}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business with user_id {current_user.sub} not found"
        )
    
    # Check if user owns this business
    if business.user_id != current_user.sub:
        logger.warning(
            f"User {current_user.sub} attempted to access business {business.id} "
            f"owned by {business.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this business"
        )
    
    logger.debug(f"User {current_user.sub} authorized for business {business.id}")
    return business
