from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from app.models.entity.base import Base
from sqlalchemy.orm import Mapped, relationship, mapped_column
from typing import TYPE_CHECKING

from app.models.enums.widget import WidgetPosition

if TYPE_CHECKING:
    from .business import BusinessEntity

class WidgetSettingsEntity(Base):
    __tablename__ = "widget_settings"
    
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String, nullable=False, default="AI Assistant")
    business_id = mapped_column(String, ForeignKey("businesses.id"), unique=True)
    primary_color = mapped_column(String, default="#0066cc")
    secondary_color = mapped_column(String, default="#ffffff")
    position: Mapped[WidgetPosition] = mapped_column(Enum(WidgetPosition), default=WidgetPosition.BOTTOM_RIGHT, nullable=False)
    logo_url = mapped_column(String)
    welcome_message = mapped_column(Text, default="Hi! How can we help you today?")
    created_at = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    business = relationship("BusinessEntity", back_populates="widget_settings")