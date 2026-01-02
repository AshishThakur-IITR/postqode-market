"""
Agent authentication API endpoints.
Implements OAuth 2.0 Client Credentials flow for AI agents.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_db, get_current_active_user, get_current_org, CurrentUser, OrgContext
from app.services.agent_auth_service import AgentAuthService
from app.schemas.auth import (
    AgentCredentialCreate,
    AgentCredentialResponse,
    AgentTokenResponse,
)
from app.models.user import User
from app.models.enums import UserRole


router = APIRouter()


@router.post("/credentials", response_model=AgentCredentialResponse, status_code=status.HTTP_201_CREATED)
def create_agent_credential(
    credential_data: AgentCredentialCreate,
    current_user: CurrentUser,
    org_id: OrgContext,
    db: Session = Depends(get_db)
):
    """
    Generate new credentials for an AI agent.
    
    Returns client_id and client_secret. The secret is only shown ONCE!
    Store it securely as it cannot be retrieved again.
    
    Requires admin or owner role in the organization.
    """
    # Check user has permission to create credentials
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create agent credentials"
        )
    
    agent_auth_service = AgentAuthService(db)
    
    try:
        credential, client_secret = agent_auth_service.create_credential(
            agent_id=credential_data.agent_id,
            organization_id=str(org_id),
            scopes=credential_data.scopes,
            name=credential_data.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return AgentCredentialResponse(
        id=str(credential.id),
        client_id=credential.client_id,
        client_secret=client_secret,  # Only returned once!
        agent_id=str(credential.agent_id),
        scopes=credential.scopes,
        created_at=credential.created_at,
    )


@router.post("/token", response_model=AgentTokenResponse)
def get_agent_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    scope: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 Client Credentials token endpoint.
    
    Exchange client credentials for an access token.
    This is the standard OAuth 2.0 token endpoint format.
    
    Returns JWT with claims:
    - tenant_id
    - agent_id
    - scopes
    - execution_scope
    - purchased_entitlement (if applicable)
    """
    # Validate grant type
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid grant type. Must be 'client_credentials'"
        )
    
    agent_auth_service = AgentAuthService(db)
    
    # Authenticate agent
    credential = agent_auth_service.authenticate_agent(client_id, client_secret)
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Parse requested scopes
    requested_scopes = scope.split() if scope else None
    
    # Create token
    token_data = agent_auth_service.create_token(credential, requested_scopes)
    
    return AgentTokenResponse(**token_data)


@router.get("/credentials")
def list_agent_credentials(
    current_user: CurrentUser,
    org_id: OrgContext,
    db: Session = Depends(get_db)
):
    """
    List all agent credentials for the organization.
    
    Note: Client secrets are never returned in listings.
    """
    agent_auth_service = AgentAuthService(db)
    credentials = agent_auth_service.list_credentials(str(org_id))
    
    return [
        {
            "id": str(c.id),
            "client_id": c.client_id,
            "agent_id": str(c.agent_id),
            "name": c.name,
            "scopes": c.scopes,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat(),
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
        }
        for c in credentials
    ]


@router.delete("/credentials/{credential_id}")
def revoke_agent_credential(
    credential_id: str,
    current_user: CurrentUser,
    org_id: OrgContext,
    db: Session = Depends(get_db)
):
    """
    Revoke an agent credential.
    
    The credential will be marked as inactive and can no longer be used
    to obtain tokens.
    """
    # Check user has permission
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to revoke credentials"
        )
    
    agent_auth_service = AgentAuthService(db)
    
    success = agent_auth_service.revoke_credential(credential_id, str(org_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    return {"message": "Credential revoked successfully"}
