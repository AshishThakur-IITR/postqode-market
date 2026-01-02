from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
import uuid
from datetime import datetime
import enum
from ..db.base import Base

class LicenseStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class License(Base):
    __tablename__ = "licenses"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"))
    
    status: Mapped[LicenseStatus] = mapped_column(SAEnum(LicenseStatus), default=LicenseStatus.ACTIVE)
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    renewal_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="licenses")
    agent: Mapped["Agent"] = relationship("Agent", back_populates="licenses")
    entitlements: Mapped[List["Entitlement"]] = relationship("Entitlement", back_populates="license")
    deployments: Mapped[List["AgentDeployment"]] = relationship("AgentDeployment", back_populates="license")

    def __repr__(self):
        return f"<License(id={self.id}, user={self.user_id}, agent={self.agent_id})>"
