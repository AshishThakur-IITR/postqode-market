from sqlalchemy import String, Integer, JSON, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import uuid
from datetime import datetime
from ..db.base import Base
from .enums import DeploymentType, DeploymentStatus


class AgentDeployment(Base):
    """
    Track agent installations/deployments in customer environments.
    Each deployment represents a running instance of an agent.
    """
    __tablename__ = "agent_deployments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # References
    license_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("licenses.id"))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    
    # Deployment configuration
    deployment_type: Mapped[DeploymentType] = mapped_column(
        SAEnum(DeploymentType), default=DeploymentType.DOCKER
    )
    adapter_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Which adapter (openai, anthropic, etc.)
    deployment_config: Mapped[Optional[dict]] = mapped_column(JSON, default={})  # User's config overrides
    
    # Environment details
    environment_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "production", "staging"
    runtime_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Status tracking
    status: Mapped[DeploymentStatus] = mapped_column(
        SAEnum(DeploymentStatus), default=DeploymentStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timestamps
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Usage telemetry
    total_invocations: Mapped[int] = mapped_column(Integer, default=0)
    last_invocation: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="deployments")
    license: Mapped["License"] = relationship("License", back_populates="deployments")
    user: Mapped["User"] = relationship("User", back_populates="deployments")

    def __repr__(self):
        return f"<AgentDeployment(id={self.id}, type={self.deployment_type}, status={self.status})>"
