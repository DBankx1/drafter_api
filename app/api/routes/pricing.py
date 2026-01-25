from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from app.infrastructure.database.db import get_db
from app.infrastructure.repository.pricing_config_repository import PricingConfigRepository
from app.models.dto.pricing import PricingConfigCreate, PricingConfigResponse
from app.services.pricing_config_service import PricingConfigService

router = APIRouter(tags=["pricing"], prefix="/pricing")


@router.get("/{id}", response_model=PricingConfigResponse)
async def get_pricing_config(id: int, db: Session = Depends(get_db)) -> PricingConfigResponse:
    pricing_config_repo = PricingConfigRepository(db)
    pricing_config = pricing_config_repo.get_by_id(id)
    if not pricing_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing config not found")
    return PricingConfigResponse.model_validate(pricing_config)


@router.post("/{business_id}", response_model=PricingConfigResponse)
async def create_pricing_model(business_id: str, pricing_config_data: PricingConfigCreate, db: Session = Depends(get_db)) -> PricingConfigResponse:
    service = PricingConfigService(db)
    try:
        pricing_config = service.create_pricing_config(business_id, pricing_config_data)
        return PricingConfigResponse.model_validate(pricing_config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
