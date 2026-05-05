from datetime import datetime, timezone
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repository.business_repository import BusinessRepository
from app.infrastructure.repository.pricing_config_repository import PricingConfigRepository
from app.models.dto.pricing import PricingConfigCreate, PricingServiceCreate
from app.models.entity.pricing_config import PricingConfigEntity, ServiceConfig

logger = logging.getLogger(__name__)

class PricingConfigService():
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_config_repo = PricingConfigRepository(db)
        self.business_repo = BusinessRepository(db)
        
    async def create_pricing_config(self, business_id: str, pricing_config_data: PricingConfigCreate) -> PricingConfigEntity:
        """Creates pricing config for a business"""
        
        exists = (await self.pricing_config_repo.get_by_business_id(business_id=business_id)) is not None
        
        if exists:
            raise ValueError(f"Pricing config already exists for business with id {business_id}")
        
        pricing_config = await self.pricing_config_repo.create(
            business_id=business_id,
            config_json=pricing_config_data.config_json.model_dump(mode="json"),
            created_at = datetime.now(timezone.utc)
        )
        
        logger.info(f"Created pricing config {pricing_config.id} for business with {business_id}")
        
        return pricing_config
    
    async def add_service_config(self, business_id: str, pricing_service_data: PricingServiceCreate) -> ServiceConfig:
        pricing_config = await self.pricing_config_repo.get_by_business_id(business_id)
        
        if pricing_config is None:
            raise ValueError(f"Pricing config does not exist for business with id {business_id}")
        
        service_config = ServiceConfig(
            name=pricing_service_data.name,
            description=pricing_service_data.description,
            pricing_type=pricing_service_data.pricing_type,
            base_price=pricing_service_data.base_price,
            options=pricing_service_data.options,
        )

        service_payload = service_config.model_dump(mode="json")
        updated_services = pricing_config.config_json.get('services', []) + [service_payload]
        updated_config_json = {
            **pricing_config.config_json,
            'services': updated_services,
        }

        await self.pricing_config_repo.update(pricing_config.id, config_json=updated_config_json)
        
        return service_config
    
    async def update_service_config(self, business_id: str, service_config_data_id: str, service_config_data: PricingServiceCreate) -> ServiceConfig:
        pricing_config = await self.pricing_config_repo.get_by_business_id(business_id)
        
        if pricing_config is None:
            raise ValueError(f"Pricing config does not exist for business with id {business_id}")
        
        existing_config = [existing_config for existing_config in pricing_config.config_json.get('services', []) if existing_config['id'] == service_config_data_id]
        
        if not any(existing_config):
            raise ValueError(f"Service config with {service_config_data_id} does not exist for pricing config {pricing_config.id}")
        
        service_config = ServiceConfig(
            id=existing_config[0]['id'],
            name=service_config_data.name,
            description=service_config_data.description,
            pricing_type=service_config_data.pricing_type,
            base_price=service_config_data.base_price,
            options=service_config_data.options,
        )
        
        service_payload = service_config.model_dump(mode="json")
        services = list(pricing_config.config_json.get('services', []))
        index = next((i for i, s in enumerate(services) if s['id'] == service_config_data_id), None)
        if index is not None:
            services[index] = service_payload
        updated_services = services
        updated_config_json = {
            **pricing_config.config_json,
            'services': updated_services,
        }

        await self.pricing_config_repo.update(pricing_config.id, config_json=updated_config_json)
        
        return service_config
    
    async def delete_service_config(self, business_id: str, service_config_data_id: str):
        pricing_config = await self.pricing_config_repo.get_by_business_id(business_id)
        
        if pricing_config is None:
            raise ValueError(f"Pricing config does not exist for business with id {business_id}")
        
        services = list(pricing_config.config_json.get('services', []))
        index = next((i for i, s in enumerate(services) if s['id'] == service_config_data_id), None)
        
        if index is None:
            raise ValueError(f"Service config with {service_config_data_id} does not exist for pricing config {pricing_config.id}")
        
        services.pop(index)
        updated_config_json = {
            **pricing_config.config_json,
            'services': services,
        }
        
        await self.pricing_config_repo.update(pricing_config.id, config_json=updated_config_json)
