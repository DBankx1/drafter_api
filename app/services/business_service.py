from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repository.business_repository import BusinessRepository
from app.models.dto.business import BusinessCreate, BusinessUpdate
from app.models.entity.business import BusinessEntity
import logging

logger = logging.getLogger(__name__)

class BusinessService:
    """
    Business logic layer for business operations.
    Orchestrates repository calls and implements business rules.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.business_repo = BusinessRepository(db)
    
    async def get_business(self, business_id: str, include_relations: bool = False) -> Optional[BusinessEntity]:
        """Get a business by ID."""
        return await self.business_repo.get_by_id(business_id, include_relations)
    
    async def get_business_by_subdomain(self, subdomain: str) -> Optional[BusinessEntity]:
        """Get a business by subdomain."""
        return await self.business_repo.get_by_subdomain(subdomain)
    
    async def create_business(self, user_id: str, business_data: BusinessCreate) -> BusinessEntity:
        """
        Create a new business with validation.
        
        Raises:
            ValueError: If email or subdomain already exists
        """
        # Validate email uniqueness
        if await self.business_repo.email_exists(business_data.email):
            raise ValueError(f"Email '{business_data.email}' is already registered")
        
        # Validate subdomain uniqueness if provided
        if business_data.subdomain and await self.business_repo.subdomain_exists(business_data.subdomain):
            raise ValueError(f"Subdomain '{business_data.subdomain}' is already taken")
        
        # Create business
        business = await self.business_repo.create(
            user_id=user_id,
            name=business_data.name,
            email=business_data.email,
            subdomain=business_data.subdomain
        )
        
        logger.info(f"Created business: {business.id} for user: {user_id}")
        return business
    
    async def update_business(self, business_id: str, business_data: BusinessUpdate) -> Optional[BusinessEntity]:
        """Update business information with validation."""
        business = await self.business_repo.get_by_id(business_id)
        
        if not business:
            return None
        
        # Validate email if being updated
        if business_data.email and business_data.email != business.email:
            if await self.business_repo.email_exists(business_data.email, exclude_id=business_id):
                raise ValueError(f"Email '{business_data.email}' is already registered")
        
        # Validate subdomain if being updated
        if business_data.subdomain and business_data.subdomain != business.subdomain:
            if await self.business_repo.subdomain_exists(business_data.subdomain, exclude_id=business_id):
                raise ValueError(f"Subdomain '{business_data.subdomain}' is already taken")
        
        # Update business
        return await self.business_repo.update(
            business_id,
            **business_data.model_dump(exclude_unset=True)
        )