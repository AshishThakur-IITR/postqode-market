"""
FastAPI dependency injection for authentication and authorization.
Provides reusable dependencies for protecting routes.
"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uuid

from ..db.session import SessionLocal
from ..models.user import User
from ..models.enums import UserRole
from .security import decode_token, verify_token_type


# OAuth2 scheme for handling Bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Extract and validate the current user from JWT token.
    
    Returns None if no token provided (for optional auth).
    Raises HTTPException if token is invalid.
    """
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify this is an access token (not refresh or agent)
    if not verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are active.
    This is a required auth dependency (raises if not authenticated).
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if hasattr(current_user, 'is_active') and not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return current_user


async def get_current_org(
    current_user: User = Depends(get_current_active_user)
) -> uuid.UUID:
    """
    Get the organization ID from the current user context.
    Enforces tenant isolation.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization"
        )
    
    return current_user.organization_id


def require_role(required_roles: list[UserRole]):
    """
    Factory for role-based access control dependency.
    
    Usage:
        @router.post("/admin-only")
        def admin_endpoint(user: User = Depends(require_role([UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN]))):
            ...
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in required_roles]}"
            )
        return current_user
    
    return role_checker


def require_marketplace_owner():
    """
    Dependency that requires the user to be a super admin.
    Used for platform-level administration.
    """
    async def owner_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        role = getattr(current_user, 'role_new', None) or getattr(current_user, 'role', None)
        if role != 'super_admin' and str(role) != 'UserRole.SUPER_ADMIN':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super Admin privileges required"
            )
        return current_user
    
    return owner_checker


async def get_agent_context(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> dict:
    """
    Extract and validate agent context from JWT token.
    Used for AI agent execution endpoints.
    
    Returns dict with:
    - agent_id
    - tenant_id
    - scopes
    - execution_scope
    - purchased_entitlement (optional)
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired agent token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify this is an agent token
    if not verify_token_type(payload, "agent"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Agent token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    required_fields = ["agent_id", "tenant_id", "scopes", "execution_scope"]
    for field in required_fields:
        if field not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing required claim: {field}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return {
        "agent_id": payload["agent_id"],
        "tenant_id": payload["tenant_id"],
        "scopes": payload["scopes"],
        "execution_scope": payload["execution_scope"],
        "purchased_entitlement": payload.get("purchased_entitlement"),
    }


def require_agent_scope(required_scopes: list[str]):
    """
    Factory for agent scope-based access control.
    
    Usage:
        @router.post("/execute")
        def execute_agent(ctx: dict = Depends(require_agent_scope(["agent.run"]))):
            ...
    """
    async def scope_checker(
        agent_context: dict = Depends(get_agent_context)
    ) -> dict:
        agent_scopes = set(agent_context.get("scopes", []))
        required = set(required_scopes)
        
        if not required.issubset(agent_scopes):
            missing = required - agent_scopes
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {list(missing)}"
            )
        
        return agent_context
    
    return scope_checker


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
OptionalUser = Annotated[Optional[User], Depends(get_current_user)]
OrgContext = Annotated[uuid.UUID, Depends(get_current_org)]
AgentContext = Annotated[dict, Depends(get_agent_context)]
