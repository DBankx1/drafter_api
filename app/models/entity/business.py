from sqlalchemy import Index, String, DateTime
from datetime import datetime, timezone
from app.models.entity.base import Base
from sqlalchemy.orm import relationship, mapped_column
from typing import TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from .conversation import ConversationEntity
    from .knowledge_base import KnowledgeBaseEntity
    from .pricing_config import PricingConfigEntity
    from .widget_settings import WidgetSettingsEntity

class BusinessEntity(Base):
    __tablename__ = 'businesses'
    
    id = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = mapped_column(String, unique=True, nullable=False)
    name = mapped_column(String, nullable=False)
    email = mapped_column(String, unique=True, nullable=False)
    subdomain = mapped_column(String, unique=True)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    pricing_config = relationship("PricingConfigEntity", back_populates="business", uselist=False, cascade="all, delete-orphan")
    conversations = relationship("ConversationEntity", back_populates="business", cascade="all, delete-orphan")
    widget_settings = relationship("WidgetSettingsEntity", back_populates="business", uselist=False, cascade="all, delete-orphan")
    knowledge_bases = relationship("KnowledgeBaseEntity", back_populates="business", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_business_id', 'id'),
        Index('idx_business_subdomain', 'subdomain')
    )
    

    
    