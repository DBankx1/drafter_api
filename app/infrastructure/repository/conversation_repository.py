
import logging
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.conversation import ConversationEntity


logger = logging.getLogger(__name__)

class ConversationRepository(BaseRepository[ConversationEntity]):
    """
    Repository for conversation operations.
    """
    
    def __init__(self, db: Session):
        super().__init__(ConversationEntity, db)
        
    def get_by_id(self, conversation_id: str, include_relations: bool = False ) -> Optional[ConversationEntity]:
        try:
            query = self.db.query(ConversationEntity).filter(ConversationEntity.id == conversation_id)
            
            if include_relations:
                query = query.options(
                    joinedload(ConversationEntity.messages)
                )
            
            conversation = query.first()
        
            if conversation:
                logger.debug(f"Retrieved conversation: {conversation_id}")
            else:
                logger.warning(f"Conversation not found: {conversation_id}")
                
            return conversation
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving conversation with ID {conversation_id}: {str(e)}")
            raise