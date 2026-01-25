from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from app.models.entity.base import Base
from sqlalchemy.orm import relationship, mapped_column
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conversation import ConversationEntity


class MessageEntity(Base):
    __tablename__ = "messages"
    
    id = mapped_column(Integer, primary_key=True)
    conversation_id = mapped_column(String, ForeignKey("conversations.id"))
    role = mapped_column(String)  # 'user', 'assistant'
    content = mapped_column(Text)
    timestamp = mapped_column(DateTime, default=datetime.now(timezone.utc))
    
    conversation = relationship("ConversationEntity", back_populates="messages")