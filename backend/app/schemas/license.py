from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class LicenseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class LicenseBase(BaseModel):
    status: LicenseStatus = LicenseStatus.ACTIVE

class LicenseCreate(LicenseBase):
    agent_id: UUID
    user_id: UUID

class License(LicenseBase):
    id: UUID
    user_id: UUID
    agent_id: UUID
    start_date: datetime
    end_date: Optional[datetime] = None
    renewal_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True
