"""
Authentication API endpoints.
Implements user registration, login, token refresh, and profile endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_active_user, CurrentUser
from app.services.auth_service import AuthService
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    TokenRefresh,
    UserResponse,
    UserUpdate,
)
from app.models.user import User


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Creates a new user with the provided email and password.
    Optionally creates a new organization if organization_name is provided.
    """
    auth_service = AuthService(db)
    
    try:
        user = auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
            organization_name=user_data.organization_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        organization_id=str(user.organization_id) if user.organization_id else None,
        role=user.role if isinstance(user.role, str) else user.role.value if user.role else 'ORG_USER',
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_marketplace_owner=user.is_marketplace_owner,
    )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login.
    
    Returns access and refresh tokens for authenticated users.
    Uses standard OAuth2 password flow (form data with username/password).
    """
    auth_service = AuthService(db)
    
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    tokens = auth_service.create_tokens(user)
    return Token(**tokens)


@router.post("/login/json", response_model=Token)
def login_json(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    JSON-based login endpoint.
    
    Alternative to OAuth2 form-based login for clients that prefer JSON.
    """
    auth_service = AuthService(db)
    
    user = auth_service.authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    tokens = auth_service.create_tokens(user)
    return Token(**tokens)


@router.post("/refresh", response_model=Token)
def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Returns new access and refresh tokens.
    """
    auth_service = AuthService(db)
    
    tokens = auth_service.refresh_access_token(token_data.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return Token(**tokens)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: CurrentUser
):
    """
    Get current authenticated user's profile.
    
    Requires valid access token.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        role=current_user.role if isinstance(current_user.role, str) else current_user.role.value if current_user.role else 'org_user',
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_approved=getattr(current_user, 'is_approved', True),
    )


@router.patch("/me", response_model=UserResponse)
def update_current_user(
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    
    Allows updating name and password.
    """
    auth_service = AuthService(db)
    
    if user_update.name is not None:
        current_user.name = user_update.name
    
    if user_update.password is not None:
        auth_service.update_password(current_user, user_update.password)
    else:
        db.commit()
        db.refresh(current_user)
    
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        role=current_user.role if isinstance(current_user.role, str) else current_user.role.value if current_user.role else 'ORG_USER',
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_marketplace_owner=current_user.is_marketplace_owner,
    )


@router.post("/logout")
def logout(current_user: CurrentUser):
    """
    Logout current user.
    
    Note: JWT tokens are stateless, so this endpoint is primarily for clients
    to clear their local token storage. For true token invalidation, implement
    a token blacklist or use short-lived tokens with refresh.
    """
    return {"message": "Successfully logged out"}
