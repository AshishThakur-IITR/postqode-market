"""
Organization API endpoints.
Protected with JWT authentication and role-based access control.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
import re
from datetime import datetime, timedelta

from app.core.deps import get_db, get_current_active_user, get_current_org, CurrentUser, OrgContext
from app.models.organization import Organization
from app.models.user import User
from app.models.license import License, LicenseStatus
from app.models.agent import Agent
from app.models.enums import UserRole, SubscriptionPlan, SubscriptionStatus
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    Organization as OrganizationSchema,
    UserWithOrg
)


router = APIRouter()


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from organization name."""
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug[:100]


@router.post("/", response_model=OrganizationSchema)
def create_organization(
    org_data: OrganizationCreate,
    owner_email: str,
    owner_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new organization and set the creator as owner.
    Note: This endpoint is typically used during registration.
    """
    # Check if slug is unique
    existing = db.query(Organization).filter(Organization.slug == org_data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization slug already exists")
    
    # Determine status based on plan
    # Only FREE plan is auto-active, others require payment/approval
    # For now, we'll make everything PENDING unless it's explicitly 'NONE' (which shouldn't happen for paid)
    sub_status = SubscriptionStatus.PENDING
    if org_data.subscription_plan == "NONE":
        sub_status = SubscriptionStatus.ACTIVE
        
    # Create organization
    org = Organization(
        name=org_data.name,
        slug=org_data.slug,
        settings=org_data.settings or {},
        subscription_plan=org_data.subscription_plan,
        subscription_status=sub_status
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    # Create owner user
    owner = User(
        email=owner_email,
        name=owner_name or org_data.name + " Admin",
        organization_id=org.id,
        role="ORG_ADMIN",
        is_approved=True # Organization creators are implicitly approved as users, but org depends on subscription
    )
    db.add(owner)
    db.commit()
    
    return org


@router.get("/me", response_model=OrganizationSchema)
def get_my_organization(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Get the current user's organization.
    Requires authentication.
    """
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="User has no organization")
    
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.patch("/me", response_model=OrganizationSchema)
def update_my_organization(
    org_update: OrganizationUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Update the current user's organization settings.
    Requires admin or owner role.
    """
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="User has no organization")
    
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Update fields
    if org_update.name is not None:
        org.name = org_update.name
    if org_update.settings is not None:
        org.settings = {**org.settings, **org_update.settings}
    
    db.commit()
    db.refresh(org)
    
    return org


@router.get("/{org_slug}", response_model=OrganizationSchema)
def get_organization_by_slug(org_slug: str, db: Session = Depends(get_db)):
    """
    Get organization by slug (public info only).
    No authentication required.
    """
    org = db.query(Organization).filter(Organization.slug == org_slug).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/{org_id}/members")
def get_organization_members(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    List all members of an organization.
    User must be a member of the organization or ORG_ADMIN.
    """
    # Verify requester is a member or admin
    is_org_admin = str(current_user.role or '').upper() == 'ORG_ADMIN'
    
    if not is_org_admin and str(current_user.organization_id) != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    members = db.query(User).filter(
        User.organization_id == org_id
    ).all()
    
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "email": m.email,
            "role": m.role.value if hasattr(m.role, 'value') else m.role # Handle enum or string
        }
        for m in members
    ]


@router.post("/{org_id}/members")
def add_organization_member(
    org_id: str,
    email: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    role: str = "member"
):
    """
    Add a member to the organization.
    Requires admin or owner role.
    """
    # Verify current user is admin/owner
    is_org_admin = str(current_user.role or '').upper() == 'ORG_ADMIN'
    
    if not is_org_admin:
        if str(current_user.organization_id) != org_id:
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Validate role
    if role.upper() not in ['ORG_ADMIN', 'ORG_USER', 'PUBLISHER']:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    user_role = role.upper()
    
    # Check if user already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        if existing.organization_id:
            raise HTTPException(status_code=400, detail="User already belongs to an organization")
        # Add to org
        existing.organization_id = uuid.UUID(org_id)
        existing.role = user_role
        db.commit()
        return {"message": "User added to organization"}
    
    # Create new user
    new_user = User(
        email=email,
        organization_id=uuid.UUID(org_id),
        role=user_role,
        is_active=True, # Auto-activate added members for now
        is_verified=True 
    )
    db.add(new_user)
    db.commit()
    
    return {"message": "Invitation sent to new user"}


# ==========================================
# ORGANIZATION LICENSE MANAGEMENT
# ==========================================

@router.get("/{org_id}/licenses")
def list_organization_licenses(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    List all licenses for users in the organization.
    Requires ORG_ADMIN role.
    """
    is_org_admin = str(current_user.role or '').upper() == 'ORG_ADMIN'
    
    if not is_org_admin:
        raise HTTPException(status_code=403, detail="ORG_ADMIN role required")
    
    # Get all user IDs in this org
    org_user_ids = [u.id for u in db.query(User).filter(User.organization_id == org_id).all()]
    
    # Get licenses for those users
    licenses = db.query(License).filter(License.user_id.in_(org_user_ids)).all()
    
    result = []
    for lic in licenses:
        user = db.query(User).filter(User.id == lic.user_id).first()
        agent = db.query(Agent).filter(Agent.id == lic.agent_id).first()
        result.append({
            "id": str(lic.id),
            "user_id": str(lic.user_id),
            "user_name": user.name or user.email.split('@')[0] if user else "Unknown",
            "user_email": user.email if user else "N/A",
            "agent_id": str(lic.agent_id),
            "agent_name": agent.name if agent else "Unknown",
            "status": lic.status.value,
            "start_date": lic.start_date.isoformat() if lic.start_date else None,
            "end_date": lic.end_date.isoformat() if lic.end_date else None,
        })
    
    return result


@router.post("/{org_id}/licenses")
def create_organization_license(
    org_id: str,
    user_id: str,
    agent_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    duration_days: int = 365
):
    """
    Create a license for a user in the organization.
    Requires ORG_ADMIN role.
    """
    is_org_admin = str(current_user.role or '').upper() == 'ORG_ADMIN'
    
    if not is_org_admin:
        raise HTTPException(status_code=403, detail="ORG_ADMIN role required")
    
    # Verify user is in this org
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target_user.organization_id) != org_id:
        raise HTTPException(status_code=403, detail="User is not in this organization")
    
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create license
    new_license = License(
        user_id=uuid.UUID(user_id),
        agent_id=uuid.UUID(agent_id),
        status=LicenseStatus.ACTIVE,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=duration_days)
    )
    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    
    return {
        "id": str(new_license.id),
        "user_id": str(new_license.user_id),
        "agent_id": str(new_license.agent_id),
        "status": new_license.status.value,
        "start_date": new_license.start_date.isoformat(),
        "end_date": new_license.end_date.isoformat() if new_license.end_date else None,
        "message": "License created successfully"
    }

