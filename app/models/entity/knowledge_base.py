from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from app.models.entity.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING

from app.models.enums.knowledge_base_type import KnowledgeBaseType

if TYPE_CHECKING:
    from .business import BusinessEntity


class KnowledgeBaseEntity(Base):
    __tablename__ = "knowledge_base"
    
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_id = mapped_column(String, ForeignKey("businesses.id"))
    content = mapped_column(Text)
    source_type: Mapped[KnowledgeBaseType] = mapped_column(Enum(KnowledgeBaseType), nullable=False, default=KnowledgeBaseType.MANUAL)
    source_reference = mapped_column(String)
    uploaded_at = mapped_column(DateTime, default=datetime.now(timezone.utc))
    
    business = relationship("BusinessEntity", back_populates="knowledge_base")
