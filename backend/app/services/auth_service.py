"""
Authentication service for user login/registration.
Implements OIDC-compatible authentication flows.
"""

from typing import Optional
from datetime import timedelta
from sqlalchemy.orm import Session
import uuid

from ..models.user import User
from ..models.organization import Organization
from ..core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from ..core.config import settings
from ..core.permissions import get_scopes_for_role


class AuthService:
    """Service for handling user authentication."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User's email address
            password: Plain text password
        
        Returns:
            User object if authenticated, None otherwise
        """
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not user.password_hash:
            # User registered via OIDC, can't use password login
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
    
    def register_user(
        self,
        email: str,
        password: str,
        name: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> User:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: Plain text password
            name: Optional display name
            organization_name: Optional org name (creates new org if provided)
        
        Returns:
            Created User object
        
        Raises:
            ValueError: If email already exists
        """
        # Check if email exists
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            raise ValueError("Email already registered")
        
        # Create organization if name provided
        organization = None
        if organization_name:
            slug = self._generate_slug(organization_name)
            organization = Organization(
                name=organization_name,
                slug=slug,
            )
            self.db.add(organization)
            self.db.flush()  # Get org ID without committing
        
        # Create user
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            name=name or email.split('@')[0],
            organization_id=organization.id if organization else None,
            role="ORG_ADMIN" if organization else "ORG_USER",
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def create_tokens(self, user: User) -> dict:
        """
        Create access and refresh tokens for a user.
        
        Args:
            user: Authenticated user
        
        Returns:
            Dict with access_token, refresh_token, token_type, expires_in
        """
        # Get scopes based on role
        scopes = get_scopes_for_role(user.role if isinstance(user.role, str) else user.role.value if user.role else 'ORG_USER')
        
        # Additional claims
        additional_claims = {
            "scopes": scopes,
        }
        if user.organization_id:
            additional_claims["tenant_id"] = str(user.organization_id)
        
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims=additional_claims,
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """
        Create new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            New token dict or None if invalid
        """
        payload = decode_token(refresh_token)
        if not payload:
            return None
        
        if not verify_token_type(payload, "refresh"):
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        try:
            user = self.db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        except ValueError:
            return None
        
        if not user or not user.is_active:
            return None
        
        return self.create_tokens(user)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            return self.db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        except ValueError:
            return None
    
    def update_password(self, user: User, new_password: str) -> User:
        """Update user's password."""
        user.password_hash = get_password_hash(new_password)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name."""
        import re
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
        slug = re.sub(r'[\s_]+', '-', slug)
        base_slug = slug[:90]
        
        # Ensure uniqueness
        counter = 0
        final_slug = base_slug
        while self.db.query(Organization).filter(Organization.slug == final_slug).first():
            counter += 1
            final_slug = f"{base_slug}-{counter}"
        
        return final_slug
