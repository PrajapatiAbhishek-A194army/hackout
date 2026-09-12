from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User corporate email address")
    password: str = Field(..., min_length=6, description="Plaintext password")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    role: str
    user_id: int
    full_name: str
    email: str
    organization: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    organization: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserSignupRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Minimum 6 characters password")
    full_name: str = Field(..., min_length=2, description="Full user name")
    role: str = Field(default="grid-operator", description="Role: grid-operator, utility, plant-owner, energy-trader")
    organization: Optional[str] = Field(default="", description="Operating organization or DISCOM")

class UserCreateRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6, description="Password")
    full_name: str = Field(..., min_length=2)
    role: str = Field(default="grid-operator", description="Role")
    organization: Optional[str] = Field(default="National Grid Operations")

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    details_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogListResponse(BaseModel):
    total_count: int
    logs: List[AuditLogResponse]
