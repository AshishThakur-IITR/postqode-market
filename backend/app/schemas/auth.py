"""
Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class UserRegister(BaseModel):
    """User registration payload."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: Optional[str] = Field(None, max_length=255)
    organization_name: Optional[str] = Field(None, max_length=255)
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """User login payload."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""
    sub: str
    type: str
    exp: datetime
    iat: datetime
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    scopes: list[str] = []


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: str
    name: Optional[str] = None
    organization_id: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    is_approved: bool
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User profile update payload."""
    name: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


# Agent Authentication Schemas

class AgentCredentialCreate(BaseModel):
    """Create agent credentials for OAuth 2.0 client credentials flow."""
    agent_id: str
    scopes: list[str] = ["agent.run"]
    name: Optional[str] = Field(None, max_length=255)  # Description for the credential


class AgentCredentialResponse(BaseModel):
    """Agent credential response (only shown once on creation)."""
    id: str
    client_id: str
    client_secret: str  # Only returned on creation, never stored in plain text
    agent_id: str
    scopes: list[str]
    created_at: datetime


class AgentTokenRequest(BaseModel):
    """OAuth 2.0 Client Credentials grant request."""
    grant_type: str = Field(..., pattern="^client_credentials$")
    client_id: str
    client_secret: str
    scope: Optional[str] = None  # Space-separated scopes


class AgentTokenResponse(BaseModel):
    """OAuth 2.0 token response for agents."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: str
