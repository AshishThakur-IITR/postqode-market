from sqlalchemy import String, JSON, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
import uuid
from datetime import datetime
from ..db.base import Base
from .enums import SubscriptionPlan, SubscriptionStatus


class Organization(Base):
    """
    Tenant/Organization model for multi-tenancy.
    Each organization represents a company/team using the marketplace.
    """
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    # Subscription info
    subscription_plan: Mapped[SubscriptionPlan] = mapped_column(
        SAEnum(SubscriptionPlan), default=SubscriptionPlan.NONE
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus), default=SubscriptionStatus.NONE
    )
    
    # Approval tracking
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Organization settings stored as JSON
    settings: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    # Example settings: {"billing_email": "...", "logo_url": "...", "industry": "..."}
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members: Mapped[List["User"]] = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name}, plan={self.subscription_plan})>"
