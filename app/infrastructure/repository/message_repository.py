import logging

from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.message import MessageEntity


logger = logging.getLogger(__name__)

class MessageRepository(BaseRepository[MessageEntity]):
    
    def __init__(self, db: AsyncSession):
        super().__init__(MessageEntity, db)
        
    