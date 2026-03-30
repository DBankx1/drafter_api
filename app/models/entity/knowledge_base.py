from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON, UUID, DateTime, ForeignKey, Index, Integer, String, Text
from app.models.entity.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING
from pgvector.sqlalchemy import Vector
from app.core.config import settings

from app.models.enums.knowledge_base_type import KnowledgeBaseType, KnowledgeBaseStatus

if TYPE_CHECKING:
    from .business import BusinessEntity


class KnowledgeBaseEntity(Base):
    __tablename__ = "knowledge_bases"
    
    id = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = mapped_column(String, ForeignKey("businesses.id"))
    source_type: Mapped[KnowledgeBaseType] = mapped_column(Enum(KnowledgeBaseType), nullable=False, default=KnowledgeBaseType.TEXT)
    status: Mapped[KnowledgeBaseStatus] = mapped_column(Enum(KnowledgeBaseStatus), nullable=False, default=KnowledgeBaseStatus.PENDING)
    source_reference = mapped_column(String)
    chunk_count = mapped_column(Integer, default=0)
    meta = mapped_column(JSON, default=dict)
    uploaded_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    business = relationship("BusinessEntity", back_populates="knowledge_bases")


class DocumentChunk(Base):
    """One row per chunk — this is what pgvector searches"""
    __tablename__ = "document_chunks"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = mapped_column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    source_id = mapped_column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    content = mapped_column(String, nullable=False)          # raw text of the chunk
    embedding = mapped_column(Vector(settings.EMBEDDING_DIM))
    chunk_index = mapped_column(Integer)
    meta = mapped_column(JSON, default=dict)               # page_num, section, url, etc.

    __table_args__ = (
        # HNSW index for fast approximate nearest-neighbor search
        Index(
            "ix_document_chunks_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
        # Composite index: always filter by business_id first
        Index("ix_chunks_business_id", "business_id"),
    )