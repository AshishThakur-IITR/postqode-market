"""
Tenant Context Middleware for Multi-Tenancy

This module provides utilities for extracting and managing tenant context
in a multi-tenant marketplace application.
"""

from typing import Optional
from dataclasses import dataclass
import uuid


@dataclass
class TenantContext:
    """
    Holds the current tenant (organization) context for a request.
    In production, this would be extracted from JWT token claims.
    """
    organization_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    user_role: Optional[str] = None
    
    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None
    
    @property
    def has_org(self) -> bool:
        return self.organization_id is not None


def get_tenant_context_from_header(
    x_org_id: Optional[str] = None,
    x_user_id: Optional[str] = None,
    x_user_role: Optional[str] = None
) -> TenantContext:
    """
    Extract tenant context from request headers.
    
    In production, this would:
    1. Validate JWT token from Authorization header
    2. Extract claims: org_id, user_id, role
    3. Return TenantContext
    
    For development, we accept headers directly.
    """
    org_id = uuid.UUID(x_org_id) if x_org_id else None
    user_id = uuid.UUID(x_user_id) if x_user_id else None
    
    return TenantContext(
        organization_id=org_id,
        user_id=user_id,
        user_role=x_user_role
    )


# Dependency for FastAPI
from fastapi import Header, HTTPException


async def require_tenant(
    x_org_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role")
) -> TenantContext:
    """
    FastAPI dependency that requires valid tenant context.
    Use this for endpoints that must be scoped to an organization.
    """
    ctx = get_tenant_context_from_header(x_org_id, x_user_id, x_user_role)
    
    if not ctx.has_org:
        raise HTTPException(
            status_code=401,
            detail="Organization context required. Provide X-Organization-ID header."
        )
    
    if not ctx.is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide X-User-ID header."
        )
    
    return ctx


async def optional_tenant(
    x_org_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role")
) -> TenantContext:
    """
    FastAPI dependency for optional tenant context.
    Use this for endpoints that work with or without org scope.
    """
    return get_tenant_context_from_header(x_org_id, x_user_id, x_user_role)
