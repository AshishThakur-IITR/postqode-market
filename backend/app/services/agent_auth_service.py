"""
Agent authentication service for OAuth 2.0 Client Credentials flow.
Handles agent credential creation and token generation.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
import uuid
import secrets

from ..models.agent import Agent
from ..models.agent_credential import AgentCredential
from ..models.license import License
from ..models.entitlement import Entitlement
from ..core.security import (
    get_password_hash,
    verify_password,
    create_agent_token,
)
from ..core.config import settings


class AgentAuthService:
    """Service for handling AI agent authentication."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_credential(
        self,
        agent_id: str,
        organization_id: str,
        scopes: list[str] = None,
        name: Optional[str] = None,
    ) -> tuple[AgentCredential, str]:
        """
        Create new credentials for an agent.
        
        Args:
            agent_id: The agent's ID
            organization_id: Organization/tenant ID
            scopes: Permission scopes (defaults to ["agent.run"])
            name: Optional human-readable name for the credential
        
        Returns:
            Tuple of (AgentCredential, plain_text_secret)
            Note: The plain text secret is only returned once!
        
        Raises:
            ValueError: If agent doesn't exist or doesn't belong to org
        """
        # Verify agent exists and belongs to org
        agent = self.db.query(Agent).filter(Agent.id == uuid.UUID(agent_id)).first()
        if not agent:
            raise ValueError("Agent not found")
        
        # Generate client ID and secret
        client_id = f"agent_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)
        
        # Create credential
        credential = AgentCredential(
            agent_id=uuid.UUID(agent_id),
            organization_id=uuid.UUID(organization_id),
            client_id=client_id,
            client_secret_hash=get_password_hash(client_secret),
            scopes=scopes or ["agent.run"],
            name=name,
            is_active=True,
        )
        
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        return credential, client_secret
    
    def authenticate_agent(self, client_id: str, client_secret: str) -> Optional[AgentCredential]:
        """
        Authenticate an agent using client credentials.
        
        Args:
            client_id: The agent's client ID
            client_secret: The agent's client secret
        
        Returns:
            AgentCredential if valid, None otherwise
        """
        credential = self.db.query(AgentCredential).filter(
            AgentCredential.client_id == client_id,
            AgentCredential.is_active == True
        ).first()
        
        if not credential:
            return None
        
        if not verify_password(client_secret, credential.client_secret_hash):
            return None
        
        # Update last used timestamp
        credential.last_used_at = datetime.utcnow()
        self.db.commit()
        
        return credential
    
    def create_token(self, credential: AgentCredential, requested_scopes: list[str] = None) -> dict:
        """
        Create a JWT token for an authenticated agent.
        
        Args:
            credential: Authenticated AgentCredential
            requested_scopes: Optional subset of scopes to include
        
        Returns:
            Dict with access_token, token_type, expires_in, scope
        """
        # Determine final scopes (intersection of requested and allowed)
        allowed_scopes = set(credential.scopes)
        if requested_scopes:
            scopes = list(allowed_scopes.intersection(set(requested_scopes)))
        else:
            scopes = list(allowed_scopes)
        
        # Find entitlement for execution scope
        execution_scope = self._get_execution_scope(credential)
        
        # Find entitlement ID if exists
        entitlement_id = self._get_entitlement_id(credential)
        
        # Create agent token
        access_token = create_agent_token(
            agent_id=str(credential.agent_id),
            tenant_id=str(credential.organization_id),
            scopes=scopes,
            execution_scope=execution_scope,
            entitlement_id=entitlement_id,
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.AGENT_TOKEN_EXPIRE_HOURS * 3600,
            "scope": " ".join(scopes),
        }
    
    def _get_execution_scope(self, credential: AgentCredential) -> str:
        """Determine execution scope based on entitlements."""
        # Check for limit scopes in entitlements
        license_obj = self.db.query(License).filter(
            License.agent_id == credential.agent_id,
        ).first()
        
        if license_obj:
            entitlement = self.db.query(Entitlement).filter(
                Entitlement.license_id == license_obj.id,
                Entitlement.scope.like("agent.limit.%"),
                Entitlement.is_active == True,
            ).first()
            
            if entitlement:
                return entitlement.scope
        
        # Default execution scope
        return "agent.limit.unlimited"
    
    def _get_entitlement_id(self, credential: AgentCredential) -> Optional[str]:
        """Get the primary entitlement ID for the agent."""
        license_obj = self.db.query(License).filter(
            License.agent_id == credential.agent_id,
        ).first()
        
        if license_obj:
            entitlement = self.db.query(Entitlement).filter(
                Entitlement.license_id == license_obj.id,
                Entitlement.scope == "agent.run",
                Entitlement.is_active == True,
            ).first()
            
            if entitlement:
                return str(entitlement.id)
        
        return None
    
    def revoke_credential(self, credential_id: str, organization_id: str) -> bool:
        """
        Revoke an agent credential.
        
        Args:
            credential_id: ID of the credential to revoke
            organization_id: Organization ID (for access control)
        
        Returns:
            True if revoked, False if not found
        """
        credential = self.db.query(AgentCredential).filter(
            AgentCredential.id == uuid.UUID(credential_id),
            AgentCredential.organization_id == uuid.UUID(organization_id),
        ).first()
        
        if not credential:
            return False
        
        credential.is_active = False
        self.db.commit()
        
        return True
    
    def list_credentials(self, organization_id: str) -> list[AgentCredential]:
        """List all credentials for an organization."""
        return self.db.query(AgentCredential).filter(
            AgentCredential.organization_id == uuid.UUID(organization_id),
        ).all()
