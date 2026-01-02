from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
from app.models.enums import UserRole


class OrganizationBase(BaseModel):
    name: str
    slug: str
    settings: Optional[dict] = {}


class OrganizationCreate(OrganizationBase):
    subscription_plan: str = "STARTER"


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None


class Organization(OrganizationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class UserCreate(UserBase):
    organization_id: Optional[uuid.UUID] = None
    role: UserRole = UserRole.ORG_USER


class User(UserBase):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    role: UserRole

    class Config:
        from_attributes = True


class UserWithOrg(User):
    organization: Optional[Organization] = None
