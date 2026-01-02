from sqlalchemy import String, JSON, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
import uuid
from datetime import datetime
from ..db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)  # Super admin approval
    
    # Platform role (stored as string to avoid enum sync issues)
    role: Mapped[str] = mapped_column(String(50), default="ORG_USER")
    
    # Multi-tenancy: Organization membership
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="members", foreign_keys=[organization_id]
    )
    published_agents: Mapped[List["Agent"]] = relationship("Agent", back_populates="publisher")
    chat_sessions: Mapped[List["ChatSession"]] = relationship("ChatSession", back_populates="user")
    licenses: Mapped[List["License"]] = relationship("License", back_populates="user")
    deployments: Mapped[List["AgentDeployment"]] = relationship("AgentDeployment", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, org={self.organization_id})>"
