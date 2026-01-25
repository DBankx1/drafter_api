import logging
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.pricing_config import PricingConfigEntity


logger = logging.getLogger(__name__)

class PricingConfigRepository(BaseRepository[PricingConfigEntity]):
    
    def __init__(self, db: Session):
        super().__init__(PricingConfigEntity, db)
        
    def get_by_business_id(self, business_id: str) -> Optional[PricingConfigEntity]:
        try:
            query = self.db.query(PricingConfigEntity).filter(
                PricingConfigEntity.business_id == business_id
            )
            pricing_config = query.first()
            return pricing_config
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving pricing config for business {business_id}: {str(e)}")
            raise
        
    def get_services_by_business_id(self, business_id: str) -> dict:
        pricing_config = self.get_by_business_id(business_id)
        if not pricing_config:
            return {"services": []}
        services = pricing_config.config_json.get("services", [])
        return {"services": services}