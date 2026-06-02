from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.models.entity.business import BusinessEntity
from app.infrastructure.repository.base_repository import BaseRepository
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class BusinessRepository(BaseRepository[BusinessEntity]):
    """
    Repository for Business entity operations.
    Provides business-specific query methods with proper error handling and logging.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(BusinessEntity, db)
    
    async def get_by_id(self, business_id: str, include_relations: bool = False) -> Optional[BusinessEntity]:
        try:
            stmt = select(BusinessEntity).where(BusinessEntity.id == business_id)
            if include_relations:
                stmt = stmt.options(
                    joinedload(BusinessEntity.pricing_config),
                    joinedload(BusinessEntity.widget_settings),
                    joinedload(BusinessEntity.knowledge_base)
                )

            result = await self.db.execute(stmt)
            business = result.scalars().first()
            
            if business:
                logger.debug(f"Retrieved business: {business_id}")
            else:
                logger.warning(f"Business not found: {business_id}")
            
            return business
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving business {business_id}: {str(e)}")
            raise
    
    async def get_by_subdomain(self, subdomain: str) -> Optional[BusinessEntity]:
        """
        Retrieve a business by subdomain.
        Uses indexed column for efficient lookup.
        """
        try:
            stmt = select(BusinessEntity).where(BusinessEntity.subdomain == subdomain)
            result = await self.db.execute(stmt)
            business = result.scalars().first()
            
            if business:
                logger.debug(f"Retrieved business by subdomain: {subdomain}")
            else:
                logger.warning(f"Business not found for subdomain: {subdomain}")
            
            return business
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving business by subdomain {subdomain}: {str(e)}")
            raise
    
    async def get_by_user_id(self, user_id: str) -> Optional[BusinessEntity]:
        try:
            stmt = select(BusinessEntity).where(BusinessEntity.user_id == user_id)
            result = await self.db.execute(stmt)
            business = result.scalars().first()

            if business:
                logger.debug(f"Retrieved business by user_id: {user_id}")
            else:
                logger.warning(f"Business not found for user_id: {user_id}")

            return business

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving business by user_id {user_id}: {str(e)}")
            raise
    
    async def get_by_email(self, email: str) -> Optional[BusinessEntity]:
        """
        Retrieve a business by email address.
        """
        try:
            stmt = select(BusinessEntity).where(BusinessEntity.email == email)
            result = await self.db.execute(stmt)
            business = result.scalars().first()
            
            if business:
                logger.debug(f"Retrieved business by email: {email}")
            
            return business
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving business by email {email}: {str(e)}")
            raise
    
    async def subdomain_exists(self, subdomain: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if a subdomain is already taken.
        """
        try:
            stmt = select(BusinessEntity).where(BusinessEntity.subdomain == subdomain)
            if exclude_id:
                stmt = stmt.where(BusinessEntity.id != exclude_id)

            result = await self.db.execute(stmt.limit(1))
            return result.scalars().first() is not None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error checking subdomain existence {subdomain}: {str(e)}")
            raise
    
    async def email_exists(self, email: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if an email is already registered.
        """
        try:
            stmt = select(BusinessEntity).where(BusinessEntity.email == email)
            if exclude_id:
                stmt = stmt.where(BusinessEntity.id != exclude_id)

            result = await self.db.execute(stmt.limit(1))
            return result.scalars().first() is not None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error checking email existence {email}: {str(e)}")
            raise
    
    async def update_subdomain(self, business_id: str, new_subdomain: str) -> Optional[BusinessEntity]:
        """
        Update a business's subdomain with validation.
        """
        try:
            if await self.subdomain_exists(new_subdomain, exclude_id=business_id):
                raise ValueError(f"Subdomain '{new_subdomain}' is already taken")
            
            business = await self.get_by_id(business_id)
            if business:
                old_subdomain = business.subdomain
                business.subdomain = new_subdomain
                await self.db.commit()
                await self.db.refresh(business)
                logger.info(f"Updated subdomain for business {business_id}: {old_subdomain} -> {new_subdomain}")
            
            return business
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating subdomain for business {business_id}: {str(e)}")
            raise