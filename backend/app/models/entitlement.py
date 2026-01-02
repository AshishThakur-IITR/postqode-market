"""
Entitlement model for license-based usage limits.
Implements OAuth 2.0 scopes for billing and access control.
"""

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import uuid
from datetime import datetime
from ..db.base import Base


class Entitlement(Base):
    """
    Usage entitlements tied to licenses.
    
    Controls:
    - Allowed scopes (e.g., agent.run, agent.configure)
    - Usage limits (max calls, rate limits)
    - Validity period
    """
    __tablename__ = "entitlements"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Link to license
    license_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("licenses.id"))
    
    # Scope this entitlement grants
    scope: Mapped[str] = mapped_column(String(100), index=True)
    
    # Usage limits
    max_calls: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # None = unlimited
    used_calls: Mapped[int] = mapped_column(Integer, default=0)
    
    # Rate limiting (calls per time period)
    rate_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate_limit_period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "minute", "hour", "day"
    
    # Validity
    valid_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    license: Mapped["License"] = relationship("License", back_populates="entitlements")
    
    def is_valid(self) -> bool:
        """Check if entitlement is currently valid."""
        if not self.is_active:
            return False
        
        now = datetime.utcnow()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        
        return True
    
    def has_quota_remaining(self) -> bool:
        """Check if usage quota has remaining capacity."""
        if self.max_calls is None:
            return True  # Unlimited
        return self.used_calls < self.max_calls
    
    def increment_usage(self) -> bool:
        """Increment usage counter. Returns True if successful, False if quota exceeded."""
        if not self.has_quota_remaining():
            return False
        self.used_calls += 1
        return True
    
    def __repr__(self):
        return f"<Entitlement(id={self.id}, scope={self.scope}, used={self.used_calls}/{self.max_calls})>"
