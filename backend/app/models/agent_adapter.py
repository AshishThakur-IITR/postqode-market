from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import uuid
from datetime import datetime
from ..db.base import Base


class AgentAdapter(Base):
    """
    Runtime adapters for agents.
    Each agent can have multiple adapters for different LLM providers (OpenAI, Anthropic, etc.)
    """
    __tablename__ = "agent_adapters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    
    # Adapter type (openai, anthropic, azure, local, custom)
    adapter_type: Mapped[str] = mapped_column(String(50), index=True)
    
    # Display name for the adapter
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Full adapter configuration YAML
    config_yaml: Mapped[str] = mapped_column(Text)
    
    # Is this the default adapter for the agent?
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="adapters")

    def __repr__(self):
        return f"<AgentAdapter(id={self.id}, type={self.adapter_type}, agent={self.agent_id})>"
