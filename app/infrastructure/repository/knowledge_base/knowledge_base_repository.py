import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.knowledge_base import DocumentChunk, KnowledgeBaseEntity
from app.models.enums.knowledge_base_type import KnowledgeBaseStatus, KnowledgeBaseType


logger = logging.getLogger(__name__)

class KnowledgeBaseRepository(BaseRepository[KnowledgeBaseEntity]):
    """
    Repository for KnowledgeBase entity operations.
    Provides knowledge base-specific query methods with proper error handling and logging.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(KnowledgeBaseEntity, db)
    
    async def get_by_id(self, kb_id: str) -> KnowledgeBaseEntity | None:
        result = await self.db.execute(
            select(KnowledgeBaseEntity).where(KnowledgeBaseEntity.id == kb_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_by_business(self, business_id: str) -> list[KnowledgeBaseEntity]:
        result = await self.db.execute(
            select(KnowledgeBaseEntity)
            .where(KnowledgeBaseEntity.business_id == business_id)
            .order_by(KnowledgeBaseEntity.uploaded_at.desc())
        )
        return result.scalars().all() # type: ignore
    
    async def update_status(
        self,
        kb_id: str,
        status: KnowledgeBaseStatus,
        chunk_count: int | None = None
    ) -> None:
        values: dict = {"status": status}
        if chunk_count is not None:
            values["chunk_count"] = chunk_count

        await self.db.execute(
            update(KnowledgeBaseEntity)
            .where(KnowledgeBaseEntity.id == kb_id)
            .values(**values)
        )
        await self.db.commit()

    async def delete(self, kb_id: str, business_id: str) -> None:
        # Chunks are deleted first (no cascade assumed), then the source
        await self.db.execute(
            delete(DocumentChunk).where(DocumentChunk.source_id == kb_id)
        )
        await self.db.execute(
            delete(KnowledgeBaseEntity)
            .where(
                KnowledgeBaseEntity.id == kb_id,
                KnowledgeBaseEntity.business_id == business_id  # 🔐 tenant guard
            )
        )
        await self.db.commit()