from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re

class BusinessBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    subdomain: Optional[str] = Field(None, min_length=3, max_length=63)

class BusinessCreate(BusinessBase):
    @field_validator('subdomain')
    @classmethod
    def validate_subdomain(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Subdomain must be lowercase alphanumeric with hyphens
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError('Subdomain must contain only lowercase letters, numbers, and hyphens')
            if v.startswith('-') or v.endswith('-'):
                raise ValueError('Subdomain cannot start or end with a hyphen')
        return v

class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    subdomain: Optional[str] = Field(None, min_length=3, max_length=63)

class BusinessResponse(BusinessBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True