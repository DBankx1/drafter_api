from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.models.entity.knowledge_base import DocumentChunk


class DocumentChunkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def insert_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Bulk insert all chunks for a source after embedding."""
        self.db.add_all(chunks)
        await self.db.commit()

    async def similarity_search(
        self,
        query_embedding: list[float],
        business_id: str,
        top_k: int = 5,
        source_ids: list[str] | None = None,  # optionally scope to specific sources
    ) -> list[DocumentChunk]:
        """
        Core RAG retrieval. Always scoped to business_id — never leaks 
        another tenant's data.
        """
        query = (
            select(
                DocumentChunk,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            )
            .where(DocumentChunk.business_id == business_id)  # 🔐 tenant isolation
            .order_by("distance")
            .limit(top_k)
        )

        if source_ids:
            query = query.where(DocumentChunk.source_id.in_(source_ids))

        result = await self.db.execute(query)
        return result.scalars().all() # type: ignore

    async def delete_by_source(self, source_id: str) -> None:
        """Called when a knowledge base source is deleted."""
        await self.db.execute(
            delete(DocumentChunk).where(DocumentChunk.source_id == source_id)
        )
        await self.db.commit()

    async def count_by_source(self, source_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .where(DocumentChunk.source_id == source_id)
        )
        return result.scalar_one()