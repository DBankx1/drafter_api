
import logging
from datetime import datetime
from typing import Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select, tuple_
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

    async def get_conversations_by_business(
        self,
        business_id: str,
        limit: int,
        sort: Literal["asc", "desc"],
        search: Optional[str] = None,
        started_at_from: Optional[datetime] = None,
        started_at_to: Optional[datetime] = None,
        cursor_ts: Optional[datetime] = None,
        cursor_id: Optional[str] = None,
    ) -> tuple[list[ConversationEntity], bool]:
        """
        Cursor-paginated conversation list for a business.

        Fetches limit+1 rows — if the result exceeds limit, has_more=True and the
        extra row is dropped. Cursor uses keyset pagination on (started_at, id) so
        the DB can satisfy it with an index seek rather than an offset scan.
        """
        try:
            stmt = select(ConversationEntity).where(
                ConversationEntity.business_id == business_id
            )

            if search:
                pattern = f"%{search}%"
                stmt = stmt.where(
                    or_(
                        ConversationEntity.customer_email.ilike(pattern),
                        ConversationEntity.customer_name.ilike(pattern),
                    )
                )

            if started_at_from:
                stmt = stmt.where(ConversationEntity.started_at >= started_at_from)
            if started_at_to:
                stmt = stmt.where(ConversationEntity.started_at <= started_at_to)

            if cursor_ts is not None and cursor_id is not None:
                keyset = tuple_(ConversationEntity.started_at, ConversationEntity.id)
                if sort == "asc":
                    stmt = stmt.where(keyset > (cursor_ts, cursor_id))
                else:
                    stmt = stmt.where(keyset < (cursor_ts, cursor_id))

            if sort == "asc":
                stmt = stmt.order_by(
                    ConversationEntity.started_at.asc(), ConversationEntity.id.asc()
                )
            else:
                stmt = stmt.order_by(
                    ConversationEntity.started_at.desc(), ConversationEntity.id.desc()
                )

            stmt = stmt.limit(limit + 1)

            result = await self.db.execute(stmt)
            rows = list(result.scalars().all())

            has_more = len(rows) > limit
            return rows[:limit], has_more

        except SQLAlchemyError as e:
            logger.error(f"Error fetching conversations for business={business_id}: {e}")
            raise

    async def count_conversations_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        started_at_from: Optional[datetime] = None,
        started_at_to: Optional[datetime] = None,
    ) -> int:
        """
        Total count matching the given filters (no cursor/limit).
        Called only on cache miss — the result is cached by the service layer.
        """
        try:
            stmt = (
                select(func.count())
                .select_from(ConversationEntity)
                .where(ConversationEntity.business_id == business_id)
            )

            if search:
                pattern = f"%{search}%"
                stmt = stmt.where(
                    or_(
                        ConversationEntity.customer_email.ilike(pattern),
                        ConversationEntity.customer_name.ilike(pattern),
                    )
                )

            if started_at_from:
                stmt = stmt.where(ConversationEntity.started_at >= started_at_from)
            if started_at_to:
                stmt = stmt.where(ConversationEntity.started_at <= started_at_to)

            result = await self.db.execute(stmt)
            return result.scalar_one()

        except SQLAlchemyError as e:
            logger.error(f"Error counting conversations for business={business_id}: {e}")
            raise

    async def get_by_ids(self, conv_ids: list[str]) -> list[ConversationEntity]:
        """Batch-fetch conversations by ID. Used to warm individual caches after a page cache hit."""
        if not conv_ids:
            return []
        try:
            stmt = select(ConversationEntity).where(ConversationEntity.id.in_(conv_ids))
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error batch-fetching conversations by ids: {e}")
            raise