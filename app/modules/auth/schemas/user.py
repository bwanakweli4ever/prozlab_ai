# app/modules/auth/schemas/user.py
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
import uuid

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None

# Properties to receive on user creation
class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

# Properties to receive on user update
class UserUpdate(UserBase):
    password: Optional[str] = None

# Properties to return to client - THIS IS THE KEY FIX
class User(UserBase):
    id: str  # Keep as string for API response
    
    # This validator converts UUID to string automatically
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    model_config = ConfigDict(from_attributes=True)

# Properties for authentication
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None

# Login schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str