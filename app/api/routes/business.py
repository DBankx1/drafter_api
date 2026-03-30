
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.middlewares.auth import get_current_user
from app.core.middlewares.business_auth import get_user_business
from app.infrastructure.database.db import get_db
from app.models.dto.auth import TokenPayload
from app.models.dto.business import BusinessCreate, BusinessResponse
from app.models.entity.business import BusinessEntity
from app.services.business_service import BusinessService


router = APIRouter(tags=["business"], prefix="/business")

@router.post("/", response_model=BusinessResponse)
async def create_business(
    business_data: BusinessCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Create a new business."""
    service = BusinessService(db)
    business = await service.create_business(current_user.sub, business_data)
    return BusinessResponse.model_validate(business)

@router.get("/me")
def my_business(business: BusinessEntity = Depends(get_user_business)):
    return BusinessResponse.model_validate(business)