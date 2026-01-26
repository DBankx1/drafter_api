from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class TokenPayload(BaseModel):
    """JWT Token Payload Structure"""
    sub: str  # user_id
    email: str
    role: str
    aud: str
    exp: int
    iat: int

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = None

class SignUpResponse(BaseModel):
    user: UserResponse
    message: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str