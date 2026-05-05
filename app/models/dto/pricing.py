from typing import Optional

from pydantic import BaseModel, Field
from datetime import date, datetime

from sqlalchemy import update

from app.models.entity.pricing_config import PricingService, ServiceConfig, ServiceOption
from app.models.enums.pricing_type import PricingType

class PricingConfigResponse(BaseModel):
    business_id: str = Field(..., description="The business ID")
    config_json: dict = Field(..., description="The pricing configuration")
    created_at: datetime = Field(..., description="The creation timestamp")
    updated_at: datetime = Field(..., description="The last update timestamp")
    
    class Config:
        from_attributes = True
    
class PricingConfigCreate(BaseModel):
    config_json: PricingService = Field(..., description="The pricing configuration")


class PricingServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    pricing_type: PricingType
    base_price: float
    options: list[ServiceOption] = []