
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.middlewares.auth import get_current_user
from app.core.middlewares.business_auth import BusinessOwnerChecker, get_user_business
from app.infrastructure.database.db import get_db
from app.models.dto.auth import TokenPayload
from app.models.dto.business import BusinessCreate, BusinessResponse
from app.models.entity.business import BusinessEntity
from app.services.business_service import BusinessService


router = APIRouter(tags=["business"], prefix="/business")

@router.post("/", response_model=BusinessResponse)
async def create_business(
    business_data: BusinessCreate,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(get_current_user)
):
    """Create a new business."""
    service = BusinessService(db)
    user_id = "3"
    business = service.create_business(user_id, business_data)
    return BusinessResponse.model_validate(business)

@router.get("/me")
def my_business(business: BusinessEntity = Depends(get_user_business)):
    return BusinessResponse.model_validate(business)