from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String
from app.models.entity.base import Base
from sqlalchemy.orm import relationship, mapped_column
from typing import TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from .business import BusinessEntity
    from .message import MessageEntity
    from .proposal import ProposalEntity


class ConversationEntity(Base):
    __tablename__ = "conversations"
    
    id = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = mapped_column(String, ForeignKey("businesses.id"))
    customer_email = mapped_column(String)
    customer_name = mapped_column(String)
    status = mapped_column(String, default="active")
    started_at = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    business = relationship("BusinessEntity", back_populates="conversations")
    messages = relationship("MessageEntity", back_populates="conversation")
    proposal = relationship("ProposalEntity", back_populates="conversation", uselist=False)