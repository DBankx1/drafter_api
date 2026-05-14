from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums.widget import WidgetPosition


class WidgetSettingsCreate(BaseModel):
    name: str = Field(default="AI Assistant")
    primary_color: str = Field(default="#0066cc")
    secondary_color: str = Field(default="#ffffff")
    position: WidgetPosition = Field(default=WidgetPosition.BOTTOM_RIGHT)
    logo_url: Optional[str] = None
    welcome_message: str = Field(default="Hi! How can we help you today?")


class WidgetSettingsUpdate(BaseModel):
    name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    position: Optional[WidgetPosition] = None
    logo_url: Optional[str] = None
    welcome_message: Optional[str] = None


class WidgetSettingsResponse(BaseModel):
    id: int
    business_id: str
    name: str
    primary_color: str
    secondary_color: str
    position: WidgetPosition
    logo_url: Optional[str]
    welcome_message: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
