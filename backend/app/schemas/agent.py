from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class AgentStatusEnum(str, Enum):
    """Agent publishing lifecycle states (for API responses)."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AgentBase(BaseModel):
    name: str
    description: str
    category: str
    price_cents: int
    prerequisites: Optional[Dict] = {}
    features: Optional[Dict] = {}
    version: str = "1.0.0"


class AgentCreate(AgentBase):
    """Schema for creating a new agent (publisher submission)."""
    pass


class AgentUpdate(BaseModel):
    """Schema for updating an agent (only allowed in DRAFT/REJECTED status)."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price_cents: Optional[int] = None
    prerequisites: Optional[Dict] = None
    features: Optional[Dict] = None
    version: Optional[str] = None


class AgentSubmit(BaseModel):
    """Schema for submitting an agent for review."""
    notes: Optional[str] = None


class AgentReject(BaseModel):
    """Schema for rejecting an agent (admin action)."""
    reason: str


class Agent(AgentBase):
    """Full agent schema for API responses."""
    id: UUID
    publisher_id: UUID
    status: AgentStatusEnum = AgentStatusEnum.DRAFT
    submitted_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Package marketplace fields
    manifest_yaml: Optional[str] = None
    package_url: Optional[str] = None
    package_checksum: Optional[str] = None
    package_size_bytes: Optional[int] = None
    supported_runtimes: Optional[List[str]] = []
    required_permissions: Optional[Dict] = {}
    min_runtime_version: Optional[str] = None
    inputs_schema: Optional[List[Dict]] = []
    outputs_schema: Optional[List[Dict]] = []
    
    class Config:
        from_attributes = True


class AgentPublisherView(Agent):
    """Extended view for publishers to see their own agents."""
    pass


class AgentBrief(BaseModel):
    """Minimal agent info for lists."""
    id: UUID
    name: str
    category: str
    status: AgentStatusEnum
    
    class Config:
        from_attributes = True


class AgentMarketplaceView(BaseModel):
    """Agent view for marketplace browsing."""
    id: UUID
    name: str
    description: str
    category: str
    price_cents: int
    version: str
    publisher_id: UUID
    supported_runtimes: Optional[List[str]] = []
    package_size_bytes: Optional[int] = None
    inputs_schema: Optional[List[Dict]] = []
    outputs_schema: Optional[List[Dict]] = []
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AgentAdapterSchema(BaseModel):
    """Schema for agent adapters."""
    id: UUID
    agent_id: UUID
    adapter_type: str
    display_name: Optional[str] = None
    config_yaml: str
    is_default: bool = False
    
    class Config:
        from_attributes = True


class AgentAdapterCreate(BaseModel):
    """Schema for creating an adapter."""
    adapter_type: str
    display_name: Optional[str] = None
    config_yaml: str
    is_default: bool = False


