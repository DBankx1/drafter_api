from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import select
from app.models.entity.base import Base
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base) # type: ignore

class BaseRepository(Generic[T]):
    """
    Base repository providing common database operations.
    All repositories should inherit from this class.
    """
    
    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: Any) -> Optional[T]:
        """
        Retrieve an entity by its primary key.
        """
        try:
            return await self.db.get(self.model, id)
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving {self.model.__name__} by id {id}: {str(e)}")
            raise
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Retrieve all entities with pagination.
        """
        try:
            result = await self.db.execute(
                select(self.model).offset(skip).limit(limit)
            )
            return result.scalars().all() # type: ignore
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving all {self.model.__name__}: {str(e)}")
            raise
    
    async def create(self, **kwargs) -> T:
        """
        Create a new entity.
        """
        try:
            entity = self.model(**kwargs)
            self.db.add(entity)
            await self.db.commit()
            await self.db.refresh(entity)
            logger.info(f"Created {self.model.__name__} with id {entity.id}")
            return entity
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {str(e)}")
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            raise
    
    async def update(self, id: Any, **kwargs) -> Optional[T]:
        """
        Update an entity by its primary key.
        """
        try:
            entity = await self.get_by_id(id)
            if entity:
                for key, value in kwargs.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                await self.db.commit()
                await self.db.refresh(entity)
                logger.info(f"Updated {self.model.__name__} with id {id}")
            return entity
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating {self.model.__name__} with id {id}: {str(e)}")
            raise
    
    async def delete(self, id: Any) -> bool:
        """
        Delete an entity by its primary key.
        """
        try:
            entity = await self.get_by_id(id)
            if entity:
                await self.db.delete(entity)
                await self.db.commit()
                logger.info(f"Deleted {self.model.__name__} with id {id}")
                return True
            return False
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {str(e)}")
            raise
    
    async def exists(self, id: Any) -> bool:
        """
        Check if an entity exists by its primary key.
        """
        try:
            result = await self.db.execute(select(self.model).filter(self.model.id == id).limit(1))
            return result.scalars().first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model.__name__} with id {id}: {str(e)}")
            raise