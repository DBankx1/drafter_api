import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.proposal import ProposalEntity

logger = logging.getLogger(__name__)


class ProposalRepository(BaseRepository[ProposalEntity]):
    def __init__(self, db: AsyncSession):
        super().__init__(ProposalEntity, db)

    async def get_by_conversation_id(self, conversation_id: str) -> Optional[ProposalEntity]:
        try:
            stmt = select(ProposalEntity).where(ProposalEntity.conversation_id == conversation_id)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching proposal for conversation {conversation_id}: {e}")
            raise

    async def update_content(self, proposal_id: str, new_content_json: dict) -> Optional[ProposalEntity]:
        """Replaces content_json with an updated proposal while preserving all other fields."""
        return await self.update(proposal_id, content_json=new_content_json)
