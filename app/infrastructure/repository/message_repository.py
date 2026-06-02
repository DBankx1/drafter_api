import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.message import MessageEntity

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository[MessageEntity]):

    def __init__(self, db: AsyncSession):
        super().__init__(MessageEntity, db)

    async def get_by_conversation_id(
        self,
        conversation_id: str,
        ascending: bool = True,
    ) -> list[MessageEntity]:
        """
        Returns all messages for a conversation ordered by timestamp.

        ascending=True  → oldest first (natural chat order, what the cache stores)
        ascending=False → newest first (for reverse-chronological dashboard views)

        The cache layer always stores ascending and reverses in memory for desc
        requests, so this method is primarily used for cache misses.
        """
        try:
            order_clause = (
                MessageEntity.timestamp.asc()
                if ascending
                else MessageEntity.timestamp.desc()
            )
            stmt = (
                select(MessageEntity)
                .where(MessageEntity.conversation_id == conversation_id)
                .order_by(order_clause)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching messages for conversation {conversation_id}: {e}")
            raise
