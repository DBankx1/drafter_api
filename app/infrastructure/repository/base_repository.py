from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.entity.base import Base
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base) # type: ignore

class BaseRepository(Generic[T]):
    """
    Base repository providing common database operations.
    All repositories should inherit from this class.
    """
    
    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db
    
    def get_by_id(self, id: Any) -> Optional[T]:
        """
        Retrieve an entity by its primary key.
        
        Args:
            id: The primary key value
            
        Returns:
            The entity if found, None otherwise
            
        Raises:
            SQLAlchemyError: If a database error occurs
        """
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving {self.model.__name__} by id {id}: {str(e)}")
            raise
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Retrieve all entities with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of entities
        """
        try:
            return self.db.query(self.model).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving all {self.model.__name__}: {str(e)}")
            raise
    
    def create(self, **kwargs) -> T:
        """
        Create a new entity.
        
        Args:
            **kwargs: Entity attributes
            
        Returns:
            The created entity
            
        Raises:
            IntegrityError: If unique constraint is violated
            SQLAlchemyError: If a database error occurs
        """
        try:
            entity = self.model(**kwargs)
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            logger.info(f"Created {self.model.__name__} with id {entity.id}")
            return entity
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {str(e)}")
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            raise
    
    def update(self, id: Any, **kwargs) -> Optional[T]:
        """
        Update an entity by its primary key.
        
        Args:
            id: The primary key value
            **kwargs: Attributes to update
            
        Returns:
            The updated entity if found, None otherwise
            
        Raises:
            SQLAlchemyError: If a database error occurs
        """
        try:
            entity = self.get_by_id(id)
            if entity:
                for key, value in kwargs.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                self.db.commit()
                self.db.refresh(entity)
                logger.info(f"Updated {self.model.__name__} with id {id}")
            return entity
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error updating {self.model.__name__} with id {id}: {str(e)}")
            raise
    
    def delete(self, id: Any) -> bool:
        """
        Delete an entity by its primary key.
        
        Args:
            id: The primary key value
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SQLAlchemyError: If a database error occurs
        """
        try:
            entity = self.get_by_id(id)
            if entity:
                self.db.delete(entity)
                self.db.commit()
                logger.info(f"Deleted {self.model.__name__} with id {id}")
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {str(e)}")
            raise
    
    def exists(self, id: Any) -> bool:
        """
        Check if an entity exists by its primary key.
        
        Args:
            id: The primary key value
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return self.db.query(self.model).filter(self.model.id == id).first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model.__name__} with id {id}: {str(e)}")
            raise