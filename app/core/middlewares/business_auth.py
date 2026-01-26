import json
from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import Optional
from .auth import get_current_user, get_optional_user
from app.models.dto.auth import TokenPayload
from app.infrastructure.database.db import get_db
from app.infrastructure.repository.business_repository import BusinessRepository
from app.models.entity import BusinessEntity
import logging

logger = logging.getLogger(__name__)

class BusinessOwnerChecker:
    """
    Dependency to verify user owns/has access to a business.
    """
    
    def __init__(self, param_name: str = "business_id"):
        self.param_name = param_name
    
    async def __call__(
        self,
        business_id: str = Path(...),
        current_user: TokenPayload = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> BusinessEntity:

        repo = BusinessRepository(db)
        business = repo.get_by_id(business_id, include_relations=False)
        
        if not business:
            logger.warning(f"Business {business_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business with id {business_id} not found"
            )
        
        # Check if user owns this business
        if business.user_id != current_user.sub:
            logger.warning(
                f"User {current_user.sub} attempted to access business {business_id} "
                f"owned by {business.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this business"
            )
        
        logger.debug(f"User {current_user.sub} authorized for business {business_id}")
        return business


async def get_user_business(
    current_user: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BusinessEntity:
    repo = BusinessRepository(db)
    business = repo.get_by_user_id(current_user.sub)
    
    if not business:
        logger.info(f"No business found for user {current_user.sub}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business associated with your account. Please create one first."
        )
    
    return business