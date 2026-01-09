from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class AgentVersionSchema(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    version: str
    package_size_bytes: Optional[int]
    created_at: datetime
    is_latest: bool
    
    class Config:
        from_attributes = True
