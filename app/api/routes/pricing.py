from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.middlewares.business_auth import get_user_business
from app.infrastructure.database.db import get_db
from app.infrastructure.repository.pricing_config_repository import PricingConfigRepository
from app.models.dto.pricing import PricingConfigCreate, PricingConfigResponse
from app.models.entity.business import BusinessEntity
from app.services.pricing_config_service import PricingConfigService

router = APIRouter(tags=["pricing"], prefix="/pricing")


@router.get("/", response_model=PricingConfigResponse)
async def get_pricing_config_by_business_id(db: AsyncSession = Depends(get_db), business: BusinessEntity = Depends(get_user_business)) -> PricingConfigResponse:
    pricing_config_repo = PricingConfigRepository(db)
    pricing_config = await pricing_config_repo.get_by_business_id(business.id)
    if not pricing_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing config not found")
    return PricingConfigResponse.model_validate(pricing_config)


@router.post("/", response_model=PricingConfigResponse)
async def create_pricing_model(pricing_config_data: PricingConfigCreate, db: AsyncSession = Depends(get_db), business: BusinessEntity = Depends(get_user_business)) -> PricingConfigResponse:
    service = PricingConfigService(db)
    try:
        pricing_config = await service.create_pricing_config(business.id, pricing_config_data)
        return PricingConfigResponse.model_validate(pricing_config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
