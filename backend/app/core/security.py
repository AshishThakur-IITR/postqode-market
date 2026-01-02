"""
Core security utilities for authentication and authorization.
Handles JWT token creation/validation and password hashing.
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from jose import jwt, JWTError
import bcrypt
from pydantic import BaseModel

from .config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    password_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: dict[str, Any] = None
) -> str:
    """
    Create a JWT access token for human users.
    
    Args:
        subject: User ID or email
        expires_delta: Token expiration time
        additional_claims: Extra claims to include in token
    
    Returns:
        Encoded JWT string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """
    Create a JWT refresh token for token renewal.
    
    Args:
        subject: User ID or email
    
    Returns:
        Encoded JWT string
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(subject),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_agent_token(
    agent_id: str,
    tenant_id: str,
    scopes: list[str],
    execution_scope: str,
    entitlement_id: Optional[str] = None
) -> str:
    """
    Create a JWT token for AI agent execution.
    
    This implements OAuth 2.0 Client Credentials flow for machine-to-machine auth.
    Token contains claims for:
    - tenant_id: Organization context
    - agent_id: Agent identifier  
    - purchased_entitlement: License reference
    - execution_scope: Allowed operations
    
    Args:
        agent_id: The AI agent's ID
        tenant_id: Organization/tenant ID
        scopes: Permission scopes (e.g., ["agent.run", "agent.configure"])
        execution_scope: Execution context scope
        entitlement_id: Optional license/entitlement reference
    
    Returns:
        Encoded JWT string
    """
    expire = datetime.utcnow() + timedelta(hours=settings.AGENT_TOKEN_EXPIRE_HOURS)
    
    to_encode = {
        "sub": str(agent_id),
        "type": "agent",
        "exp": expire,
        "iat": datetime.utcnow(),
        "tenant_id": str(tenant_id),
        "agent_id": str(agent_id),
        "scopes": scopes,
        "execution_scope": execution_scope,
    }
    
    if entitlement_id:
        to_encode["purchased_entitlement"] = str(entitlement_id)
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload dict or None if invalid
    
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token_type(payload: dict[str, Any], expected_type: str) -> bool:
    """
    Verify that a token payload has the expected type.
    
    Args:
        payload: Decoded JWT payload
        expected_type: Expected token type ("access", "refresh", "agent")
    
    Returns:
        True if token type matches
    """
    return payload.get("type") == expected_type
