"""
Permission constants and utilities for authorization.
Implements OAuth 2.0 scopes and entitlement checking.
"""

from enum import Enum
from typing import Optional
from functools import wraps
from fastapi import HTTPException, status


class Scope(str, Enum):
    """
    OAuth 2.0 scope constants for the marketplace.
    Used in JWT claims for both human and agent tokens.
    """
    # Agent execution scopes
    AGENT_RUN = "agent.run"
    AGENT_CONFIGURE = "agent.configure"
    AGENT_PUBLISH = "agent.publish"
    AGENT_DELETE = "agent.delete"
    
    # Organization scopes
    ORG_READ = "org.read"
    ORG_WRITE = "org.write"
    ORG_ADMIN = "org.admin"
    
    # License/billing scopes
    LICENSE_VIEW = "license.view"
    LICENSE_MANAGE = "license.manage"
    
    # Marketplace owner scopes
    MARKETPLACE_ADMIN = "marketplace.admin"
    
    # Usage limit scopes (examples)
    LIMIT_100_CALLS = "agent.limit.100_calls"
    LIMIT_1000_CALLS = "agent.limit.1000_calls"
    LIMIT_UNLIMITED = "agent.limit.unlimited"


# Role to scope mapping
ROLE_SCOPES = {
    "owner": [
        Scope.AGENT_RUN, Scope.AGENT_CONFIGURE, Scope.AGENT_PUBLISH, Scope.AGENT_DELETE,
        Scope.ORG_READ, Scope.ORG_WRITE, Scope.ORG_ADMIN,
        Scope.LICENSE_VIEW, Scope.LICENSE_MANAGE,
    ],
    "admin": [
        Scope.AGENT_RUN, Scope.AGENT_CONFIGURE, Scope.AGENT_PUBLISH,
        Scope.ORG_READ, Scope.ORG_WRITE,
        Scope.LICENSE_VIEW, Scope.LICENSE_MANAGE,
    ],
    "member": [
        Scope.AGENT_RUN, Scope.AGENT_CONFIGURE,
        Scope.ORG_READ,
        Scope.LICENSE_VIEW,
    ],
    "viewer": [
        Scope.AGENT_RUN,
        Scope.ORG_READ,
        Scope.LICENSE_VIEW,
    ],
}


def get_scopes_for_role(role: str) -> list[str]:
    """Get the scopes associated with a user role."""
    scopes = ROLE_SCOPES.get(role, [])
    return [s.value if isinstance(s, Scope) else s for s in scopes]


def has_scope(user_scopes: list[str], required_scope: str) -> bool:
    """Check if a list of scopes contains the required scope."""
    return required_scope in user_scopes


def has_all_scopes(user_scopes: list[str], required_scopes: list[str]) -> bool:
    """Check if all required scopes are present."""
    return all(scope in user_scopes for scope in required_scopes)


def has_any_scope(user_scopes: list[str], required_scopes: list[str]) -> bool:
    """Check if any of the required scopes are present."""
    return any(scope in user_scopes for scope in required_scopes)


def check_entitlement_limit(
    scope: str,
    current_usage: int,
    max_usage: Optional[int] = None
) -> bool:
    """
    Check if an entitlement limit has been exceeded.
    
    Args:
        scope: The limit scope (e.g., "agent.limit.1000_calls")
        current_usage: Current number of calls/uses
        max_usage: Override for max usage (if not encoded in scope)
    
    Returns:
        True if within limits, False if exceeded
    """
    if scope == Scope.LIMIT_UNLIMITED.value:
        return True
    
    if max_usage is not None:
        return current_usage < max_usage
    
    # Parse limit from scope
    if scope.startswith("agent.limit."):
        limit_str = scope.replace("agent.limit.", "").replace("_calls", "")
        try:
            limit = int(limit_str)
            return current_usage < limit
        except ValueError:
            return True
    
    return True


def enforce_tenant_isolation(user_tenant_id: str, resource_tenant_id: str) -> None:
    """
    Enforce that a user can only access resources in their own tenant.
    
    Raises:
        HTTPException: If tenant IDs don't match
    """
    if str(user_tenant_id) != str(resource_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: resource belongs to different organization"
        )


class PermissionDeniedError(Exception):
    """Raised when a permission check fails."""
    def __init__(self, message: str = "Permission denied"):
        self.message = message
        super().__init__(self.message)
