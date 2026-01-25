from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.infrastructure.repository.business_repository import BusinessRepository
from app.infrastructure.repository.pricing_config_repository import PricingConfigRepository
from app.models.dto.pricing import PricingConfigCreate
from app.models.entity.pricing_config import PricingConfigEntity

logger = logging.getLogger(__name__)

class PricingConfigService():
    
    def __init__(self, db: Session):
        self.db = db
        self.pricing_config_repo = PricingConfigRepository(db)
        self.business_repo = BusinessRepository(db)
        
    def create_pricing_config(self, business_id: str, pricing_config_data: PricingConfigCreate) -> PricingConfigEntity:
        """Creates pricing config for a business"""
        
        business = self.business_repo.get_by_id(business_id)
        
        if not business:
            raise ValueError(f"Business with id {business_id} not found")
        
        exists = self.pricing_config_repo.get_by_business_id(business_id=business_id) is not None
        
        if exists:
            raise ValueError(f"Pricing config already exists for business with id {business_id}")
        
        pricing_config = self.pricing_config_repo.create(
            business_id=business_id,
            config_json=pricing_config_data.config_json.model_dump(mode="json"),
            created_at = datetime.now(timezone.utc)
        )
        
        logger.info(f"Created pricing config {pricing_config.id} for business with {business_id}")
        
        return pricing_config