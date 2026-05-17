
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.conversation import ConversationEntity


logger = logging.getLogger(__name__)

class ConversationRepository(BaseRepository[ConversationEntity]):
    """
    Repository for conversation operations.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(ConversationEntity, db)
        
    async def get_by_id(self, conversation_id: str, include_relations: bool = False ) -> Optional[ConversationEntity]:
        try:
            stmt = select(ConversationEntity).where(ConversationEntity.id == conversation_id)
            if include_relations:
                stmt = stmt.options(joinedload(ConversationEntity.messages))

            result = await self.db.execute(stmt)
            conversation = result.scalars().first()

            if conversation:
                logger.debug(f"Retrieved conversation: {conversation_id}")
            else:
                logger.warning(f"Conversation not found: {conversation_id}")
                
            return conversation
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving conversation with ID {conversation_id}: {str(e)}")
            raise

    async def get_by_id_with_proposal(self, conversation_id: str) -> Optional[ConversationEntity]:
        """
        Loads the conversation and its proposal in a single query.
        Used at WebSocket connect time to determine whether a proposal already exists,
        so proposal_id can be seeded into AgentState from the DB (not from Redis alone).
        """
        try:
            stmt = (
                select(ConversationEntity)
                .where(ConversationEntity.id == conversation_id)
                .options(joinedload(ConversationEntity.proposal))
            )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving conversation with proposal for {conversation_id}: {str(e)}")
            raise