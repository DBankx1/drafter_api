from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, String
from app.models.entity.base import Base
from app.models.enums.proposal_status import ProposalStatus
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import Enum

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conversation import ConversationEntity


class ProposalEntity(Base):
    __tablename__ = "proposals"
    
    id = mapped_column(String, primary_key=True)
    conversation_id = mapped_column(String, ForeignKey("conversations.id"), unique=True)
    status: Mapped[ProposalStatus] = mapped_column(Enum(ProposalStatus), nullable=False, default=ProposalStatus.DRAFT)
    content_json = mapped_column(JSON)
    pdf_url = mapped_column(String)
    created_at = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    conversation = relationship("ConversationEntity", back_populates="proposal")
