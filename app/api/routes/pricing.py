from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.middlewares.business_auth import get_user_business
from app.infrastructure.database.db import get_db
from app.infrastructure.repository.pricing_config_repository import PricingConfigRepository
from app.models.dto.pricing import PricingConfigCreate, PricingConfigResponse, PricingServiceCreate
from app.models.entity.business import BusinessEntity
from app.models.entity.pricing_config import ServiceConfig
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
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    

@router.post("/services", response_model=ServiceConfig)
async def add_service_config(service_config_data: PricingServiceCreate, db: AsyncSession = Depends(get_db), business: BusinessEntity = Depends(get_user_business)) -> ServiceConfig:
    service = PricingConfigService(db)
    try:
        service_config = await service.add_service_config(business.id, service_config_data)
        return service_config
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    

@router.put("/services/{id}", response_model=ServiceConfig)
async def update_service_config(id: str, service_config_data: PricingServiceCreate, db: AsyncSession = Depends(get_db), business: BusinessEntity = Depends(get_user_business)) -> ServiceConfig:
    service = PricingConfigService(db)
    try:
        updated_service_config = await service.update_service_config(business.id, id, service_config_data)
        return updated_service_config
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/services/{id}")
async def delete_service_config(id: str, db: AsyncSession = Depends(get_db), business: BusinessEntity = Depends(get_user_business)):
    service = PricingConfigService(db)
    try:
        await service.delete_service_config(business.id, id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        