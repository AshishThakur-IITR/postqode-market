from sqlalchemy import String, Integer, JSON, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from ..db.base import Base

class AgentVersion(Base):
    """
    Represents a specific immutable version of an agent package.
    """
    __tablename__ = "agent_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), index=True)
    
    version: Mapped[str] = mapped_column(String, index=True)  # e.g., "1.0.0"
    
    # Package details specific to this version
    package_url: Mapped[str] = mapped_column(String(500))
    package_checksum: Mapped[str] = mapped_column(String(64))
    package_size_bytes: Mapped[int] = mapped_column(Integer)
    manifest_yaml: Mapped[str] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Is this the currently active version for the agent?
    is_latest: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationship
    agent: Mapped["Agent"] = relationship("Agent", back_populates="versions")

    def __repr__(self):
        return f"<AgentVersion(agent_id={self.agent_id}, version={self.version})>"
