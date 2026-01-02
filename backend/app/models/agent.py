from sqlalchemy import String, Integer, JSON, ForeignKey, DateTime, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
import uuid
from datetime import datetime
from ..db.base import Base
from .enums import AgentStatus

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, index=True)
    price_cents: Mapped[int] = mapped_column(Integer)
    prerequisites: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    features: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    version: Mapped[str] = mapped_column(String, default="1.0.0")
    
    # Publishing workflow fields
    status: Mapped[AgentStatus] = mapped_column(
        SAEnum(AgentStatus), default=AgentStatus.PUBLISHED, index=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ========================================
    # PACKAGE MARKETPLACE FIELDS
    # ========================================
    
    # Agent manifest (agent.yaml content)
    manifest_yaml: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Package storage
    package_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    package_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA256
    package_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Runtime configuration
    supported_runtimes: Mapped[Optional[dict]] = mapped_column(JSON, default=[])  # ["openai", "anthropic", "local"]
    required_permissions: Mapped[Optional[dict]] = mapped_column(JSON, default={})  # Parsed from policies/permissions.yaml
    min_runtime_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Agent inputs/outputs schema
    inputs_schema: Mapped[Optional[dict]] = mapped_column(JSON, default=[])  # From manifest spec.inputs
    outputs_schema: Mapped[Optional[dict]] = mapped_column(JSON, default=[])  # From manifest spec.outputs
    
    # ========================================
    
    publisher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    
    # Relationships
    publisher: Mapped["User"] = relationship("User", back_populates="published_agents")
    licenses: Mapped[List["License"]] = relationship("License", back_populates="agent")
    credentials: Mapped[List["AgentCredential"]] = relationship("AgentCredential", back_populates="agent")
    adapters: Mapped[List["AgentAdapter"]] = relationship("AgentAdapter", back_populates="agent", cascade="all, delete-orphan")
    deployments: Mapped[List["AgentDeployment"]] = relationship("AgentDeployment", back_populates="agent")

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, status={self.status})>"


