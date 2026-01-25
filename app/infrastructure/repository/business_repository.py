from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
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
    
    def __init__(self, db: Session):
        super().__init__(BusinessEntity, db)
    
    def get_by_id(self, business_id: str, include_relations: bool = False) -> Optional[BusinessEntity]:
        """
        Retrieve a business by ID with optional eager loading of relationships.
        
        Args:
            business_id: The business UUID
            include_relations: Whether to eager load related entities (pricing, widget settings, etc.)
            
        Returns:
            Business entity if found, None otherwise
            
        Raises:
            SQLAlchemyError: If a database error occurs
        """
        try:
            query = self.db.query(BusinessEntity).filter(BusinessEntity.id == business_id)
            
            if include_relations:
                query = query.options(
                    joinedload(BusinessEntity.pricing_config),
                    joinedload(BusinessEntity.widget_settings),
                    joinedload(BusinessEntity.knowledge_base)
                )
            
            business = query.first()
            
            if business:
                logger.debug(f"Retrieved business: {business_id}")
            else:
                logger.warning(f"Business not found: {business_id}")
            
            return business
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving business {business_id}: {str(e)}")
            raise
    
    def get_by_subdomain(self, subdomain: str) -> Optional[BusinessEntity]:
        """
        Retrieve a business by subdomain.
        Uses indexed column for efficient lookup.
        
        Args:
            subdomain: The business subdomain
            
        Returns:
            Business entity if found, None otherwise
            
        Raises:
            SQLAlchemyError: If a database error occurs
        """
        try:
            business = self.db.query(BusinessEntity).filter(
                BusinessEntity.subdomain == subdomain,
                BusinessEntity.is_active == True
            ).first()
            
            if business:
                logger.debug(f"Retrieved business by subdomain: {subdomain}")
            else:
                logger.warning(f"Business not found for subdomain: {subdomain}")
            
            return business
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving business by subdomain {subdomain}: {str(e)}")
            raise
    
    def get_by_user_id(self, user_id: str) -> Optional[BusinessEntity]:
        """
        Retrieve a business by Supabase user ID.
        
        Args:
            user_id: The Supabase auth user ID
            
        Returns:
            Business entity if found, None otherwise
            
        Raises:
            SQLAlchemyError: If a database error occurs
        """
        try:
            business = self.db.query(BusinessEntity).filter(
                BusinessEntity.user_id == user_id
            ).first()
            
            if business:
                logger.debug(f"Retrieved business by user_id: {user_id}")
            else:
                logger.warning(f"Business not found for user_id: {user_id}")
            
            return business
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving business by user_id {user_id}: {str(e)}")
            raise
    
    def get_by_email(self, email: str) -> Optional[BusinessEntity]:
        """
        Retrieve a business by email address.
        
        Args:
            email: The business email
            
        Returns:
            Business entity if found, None otherwise
            
        Raises:
            SQLAlchemyError: If a database error occurs
        """
        try:
            business = self.db.query(BusinessEntity).filter(
                BusinessEntity.email == email
            ).first()
            
            if business:
                logger.debug(f"Retrieved business by email: {email}")
            
            return business
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving business by email {email}: {str(e)}")
            raise
    
    def subdomain_exists(self, subdomain: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if a subdomain is already taken.
        
        Args:
            subdomain: The subdomain to check
            exclude_id: Optional business ID to exclude from check (for updates)
            
        Returns:
            True if subdomain exists, False otherwise
        """
        try:
            query = self.db.query(BusinessEntity).filter(BusinessEntity.subdomain == subdomain)
            
            if exclude_id:
                query = query.filter(BusinessEntity.id != exclude_id)
            
            return query.first() is not None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error checking subdomain existence {subdomain}: {str(e)}")
            raise
    
    def email_exists(self, email: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if an email is already registered.
        
        Args:
            email: The email to check
            exclude_id: Optional business ID to exclude from check (for updates)
            
        Returns:
            True if email exists, False otherwise
        """
        try:
            query = self.db.query(BusinessEntity).filter(BusinessEntity.email == email)
            
            if exclude_id:
                query = query.filter(BusinessEntity.id != exclude_id)
            
            return query.first() is not None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error checking email existence {email}: {str(e)}")
            raise
    
    def get_active_businesses(self, skip: int = 0, limit: int = 100) -> List[BusinessEntity]:
        """
        Retrieve all active businesses with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active businesses
        """
        try:
            businesses = self.db.query(BusinessEntity).filter(
                BusinessEntity.is_active == True
            ).offset(skip).limit(limit).all()
            
            logger.debug(f"Retrieved {len(businesses)} active businesses")
            return businesses
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving active businesses: {str(e)}")
            raise
    
    def deactivate(self, business_id: str) -> Optional[BusinessEntity]:
        """
        Soft delete a business by marking it as inactive.
        
        Args:
            business_id: The business UUID
            
        Returns:
            The deactivated business if found, None otherwise
        """
        try:
            business = self.get_by_id(business_id)
            if business:
                business.is_active = False
                self.db.commit()
                self.db.refresh(business)
                logger.info(f"Deactivated business: {business_id}")
            return business
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deactivating business {business_id}: {str(e)}")
            raise
    
    def reactivate(self, business_id: str) -> Optional[BusinessEntity]:
        """
        Reactivate a previously deactivated business.
        
        Args:
            business_id: The business UUID
            
        Returns:
            The reactivated business if found, None otherwise
        """
        try:
            business = self.db.query(BusinessEntity).filter(
                BusinessEntity.id == business_id
            ).first()
            
            if business:
                business.is_active = True
                self.db.commit()
                self.db.refresh(business)
                logger.info(f"Reactivated business: {business_id}")
            return business
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error reactivating business {business_id}: {str(e)}")
            raise
    
    def update_subdomain(self, business_id: str, new_subdomain: str) -> Optional[BusinessEntity]:
        """
        Update a business's subdomain with validation.
        
        Args:
            business_id: The business UUID
            new_subdomain: The new subdomain
            
        Returns:
            The updated business if successful, None if business not found
            
        Raises:
            ValueError: If subdomain is already taken
            SQLAlchemyError: If a database error occurs
        """
        try:
            if self.subdomain_exists(new_subdomain, exclude_id=business_id):
                raise ValueError(f"Subdomain '{new_subdomain}' is already taken")
            
            business = self.get_by_id(business_id)
            if business:
                old_subdomain = business.subdomain
                business.subdomain = new_subdomain
                self.db.commit()
                self.db.refresh(business)
                logger.info(f"Updated subdomain for business {business_id}: {old_subdomain} -> {new_subdomain}")
            
            return business
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating subdomain for business {business_id}: {str(e)}")
            raise