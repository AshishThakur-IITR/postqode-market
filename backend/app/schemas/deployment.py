"""
Pydantic schemas for Agent Deployments.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class DeploymentTypeEnum(str, Enum):
    CLOUD_MANAGED = "cloud_managed"
    KUBERNETES = "kubernetes"
    VM_STANDALONE = "vm_standalone"
    SERVERLESS = "serverless"
    EDGE = "edge"
    DOCKER = "docker"


class DeploymentStatusEnum(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"
    UPDATING = "updating"


class DeploymentBase(BaseModel):
    deployment_type: DeploymentTypeEnum
    adapter_used: Optional[str] = None
    deployment_config: Optional[Dict[str, Any]] = {}
    environment_name: Optional[str] = None


class DeploymentCreate(DeploymentBase):
    """Schema for creating a new deployment."""
    license_id: UUID
    agent_id: UUID


class DeploymentUpdate(BaseModel):
    """Schema for updating deployment status."""
    status: Optional[DeploymentStatusEnum] = None
    error_message: Optional[str] = None
    deployment_config: Optional[Dict[str, Any]] = None


class DeploymentHealthUpdate(BaseModel):
    """Schema for health check updates."""
    total_invocations: Optional[int] = None
    last_invocation: Optional[datetime] = None


class Deployment(DeploymentBase):
    """Full deployment schema for API responses."""
    id: UUID
    license_id: UUID
    agent_id: UUID
    user_id: UUID
    status: DeploymentStatusEnum = DeploymentStatusEnum.PENDING
    error_message: Optional[str] = None
    deployed_at: datetime
    last_health_check: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    total_invocations: int = 0
    last_invocation: Optional[datetime] = None
    runtime_version: Optional[str] = None
    
    # Embedded agent info
    agent_name: Optional[str] = None
    agent_version: Optional[str] = None
    
    class Config:
        from_attributes = True


class DeploymentBrief(BaseModel):
    """Brief deployment info for lists."""
    id: UUID
    agent_id: UUID
    agent_name: Optional[str] = None
    deployment_type: DeploymentTypeEnum
    status: DeploymentStatusEnum
    deployed_at: datetime
    
    class Config:
        from_attributes = True
