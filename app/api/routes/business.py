
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.infrastructure.database.db import get_db
from app.models.dto.business import BusinessCreate, BusinessResponse
from app.services.business_service import BusinessService


router = APIRouter(tags=["business"], prefix="/business")

@router.get("/{business_id}", response_model=BusinessResponse)
def get_business(
    business_id: str,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(get_current_user)
):
    """Get business by ID."""
    service = BusinessService(db)
    business = service.get_business(business_id)
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business with id {business_id} not found"
        )
    
    # Authorization check
    # if business.user_id != current_user["id"]:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not authorized to access this business"
    #     )
    
    return BusinessResponse.model_validate(business)

@router.get("/subdomain/{subdomain}", response_model=BusinessResponse)
def get_business_by_subdomain(
    subdomain: str,
    db: Session = Depends(get_db)
):
    """Get business by subdomain (public endpoint for widget)."""
    service = BusinessService(db)
    business = service.get_business_by_subdomain(subdomain)
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business with subdomain '{subdomain}' not found"
        )
    
    return BusinessResponse.model_validate(business)

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