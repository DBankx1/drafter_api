from datetime import datetime, timezone
import uuid
from pydantic import Field, BaseModel
from sqlalchemy import  DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, mapped_column
from app.models.entity.base import Base
from typing import TYPE_CHECKING, Optional

from app.models.enums.pricing_type import PricingType

if TYPE_CHECKING:
    from .business import BusinessEntity

class PricingConfigEntity(Base):
    __tablename__ = "pricing_configs"
    
    id = mapped_column(Integer, primary_key=True)
    business_id = mapped_column(String, ForeignKey("businesses.id"))
    config_json = mapped_column(JSONB, nullable=False)
    created_at = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    business = relationship("BusinessEntity", back_populates="pricing_config")
    
    
class ServiceOption(BaseModel):
    name: str
    price: float


class ServiceConfig(BaseModel):
    id: str = Field(description="The service ID", default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    pricing_type: PricingType
    base_price: float
    options: list[ServiceOption] = []


class PricingService(BaseModel):
    services: list[ServiceConfig]
    
    model_config = {
        "use_enum_values": True
    }