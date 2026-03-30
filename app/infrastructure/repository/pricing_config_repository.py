import logging
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.pricing_config import PricingConfigEntity


logger = logging.getLogger(__name__)

class PricingConfigRepository(BaseRepository[PricingConfigEntity]):
    
    def __init__(self, db: AsyncSession):
        super().__init__(PricingConfigEntity, db)
        
    async def get_by_business_id(self, business_id: str) -> Optional[PricingConfigEntity]:
        try:
            stmt = select(PricingConfigEntity).where(PricingConfigEntity.business_id == business_id)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving pricing config for business {business_id}: {str(e)}")
            raise
        
    async def get_services_by_business_id(self, business_id: str) -> dict:
        pricing_config = await self.get_by_business_id(business_id)
        if not pricing_config:
            return {"services": []}
        services = pricing_config.config_json.get("services", [])
        return {"services": services}