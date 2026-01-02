"""
Agent credentials model for OAuth 2.0 Client Credentials flow.
Used for machine-to-machine authentication of AI agents.
"""

from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import uuid
from datetime import datetime
from ..db.base import Base


class AgentCredential(Base):
    """
    Credentials for AI agent authentication.
    
    Implements OAuth 2.0 Client Credentials flow:
    - client_id: Public identifier for the agent
    - client_secret_hash: Hashed secret (never store plain text)
    - scopes: Allowed permissions
    """
    __tablename__ = "agent_credentials"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # The agent this credential belongs to
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"))
    
    # Organization context for tenant isolation
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    
    # OAuth 2.0 Client Credentials
    client_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    client_secret_hash: Mapped[str] = mapped_column(String(255))
    
    # Human-readable name for this credential
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Scopes: JSON array of allowed permissions
    scopes: Mapped[list] = mapped_column(JSON, default=["agent.run"])
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="credentials")
    organization: Mapped["Organization"] = relationship("Organization")
    
    def __repr__(self):
        return f"<AgentCredential(id={self.id}, agent_id={self.agent_id}, client_id={self.client_id})>"
