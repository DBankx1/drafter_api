import logging

from sqlalchemy.orm import Session
from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.message import MessageEntity


logger = logging.getLogger(__name__)

class MessageRepository(BaseRepository[MessageEntity]):
    
    def __init__(self, db: Session):
        super().__init__(MessageEntity, db)
        
    