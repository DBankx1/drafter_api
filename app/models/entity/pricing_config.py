from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, mapped_column
from app.models.entity.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .business import BusinessEntity

class PricingConfigEntity(Base):
    __tablename__ = "pricing_configs"
    
    id = mapped_column(Integer, primary_key=True)
    business_id = mapped_column(String, ForeignKey("businesses.id"))
    config_json = mapped_column(JSON, nullable=False)
    created_at = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    business = relationship("BusinessEntity", back_populates="pricing_config")