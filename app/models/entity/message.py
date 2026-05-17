from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.models.entity.base import Base
from sqlalchemy.orm import relationship, mapped_column
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Enum

from app.models.enums.chat_roles import ChatRoles

if TYPE_CHECKING:
    from .conversation import ConversationEntity


class MessageEntity(Base):
    __tablename__ = "messages"

    id = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = mapped_column(String, ForeignKey("conversations.id"))
    role = mapped_column(Enum(ChatRoles), nullable=False, default=ChatRoles.USER)
    content = mapped_column(Text)
    timestamp = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Analytics / long-term memory enrichment — all nullable, safe to add to existing rows
    intent = mapped_column(String(20), nullable=True)      # "rag" | "proposal" | "unknown"
    meta = mapped_column(JSONB, nullable=True)              # {"retrieved_chunk_count": 3, "proposal_id": "..."}
    token_count = mapped_column(Integer, nullable=True)     # LLM usage tracking

    conversation = relationship("ConversationEntity", back_populates="messages")