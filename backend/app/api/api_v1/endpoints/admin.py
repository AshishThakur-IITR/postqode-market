from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.user import User
from app.models.organization import Organization
from app.models.enums import AgentStatus, UserRole, SubscriptionStatus
from app.schemas.agent import Agent as AgentSchema, AgentReject
from datetime import datetime

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_admin(user_id: str, db: Session) -> User:
    """Verify user exists and has admin privileges (ORG_ADMIN)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Check if user is ORG_ADMIN (case insensitive)
    role = str(getattr(user, 'role', '') or '').upper()
    if role != 'ORG_ADMIN':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


# ==========================================
# ADMIN REVIEW ENDPOINTS
# ==========================================

@router.get("/agents/pending", response_model=List[AgentSchema])
def list_pending_agents(
    admin_id: str = Query(..., description="Admin user ID for authorization"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all agents pending review.
    Requires admin/marketplace owner privileges.
    """
    verify_admin(admin_id, db)
    
    agents = db.query(Agent).filter(
        Agent.status == AgentStatus.PENDING_REVIEW
    ).order_by(Agent.submitted_at.asc()).offset(skip).limit(limit).all()
    
    return agents


@router.get("/agents/all", response_model=List[AgentSchema])
def list_all_agents(
    admin_id: str = Query(..., description="Admin user ID for authorization"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all agents with any status (admin view).
    Requires admin/marketplace owner privileges.
    """
    verify_admin(admin_id, db)
    
    query = db.query(Agent)
    
    if status_filter:
        try:
            agent_status = AgentStatus(status_filter)
            query = query.filter(Agent.status == agent_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
    
    return query.order_by(Agent.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/agents/{agent_id}/approve", response_model=AgentSchema)
def approve_agent(
    agent_id: str,
    admin_id: str = Query(..., description="Admin user ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Approve an agent and publish it to the marketplace.
    Changes status from PENDING_REVIEW to PUBLISHED.
    """
    verify_admin(admin_id, db)
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status != AgentStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve agent in {agent.status.value} status. Only PENDING_REVIEW agents can be approved."
        )
    
    agent.status = AgentStatus.PUBLISHED
    agent.published_at = datetime.utcnow()
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.post("/agents/{agent_id}/reject", response_model=AgentSchema)
def reject_agent(
    agent_id: str,
    rejection: AgentReject,
    admin_id: str = Query(..., description="Admin user ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Reject an agent submission.
    Publisher will be able to edit and resubmit after rejection.
    """
    verify_admin(admin_id, db)
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status != AgentStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject agent in {agent.status.value} status. Only PENDING_REVIEW agents can be rejected."
        )
    
    agent.status = AgentStatus.REJECTED
    agent.rejection_reason = rejection.reason
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.post("/agents/{agent_id}/archive", response_model=AgentSchema)
def archive_agent(
    agent_id: str,
    admin_id: str = Query(..., description="Admin user ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Archive a published agent (remove from marketplace).
    """
    verify_admin(admin_id, db)
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status not in [AgentStatus.PUBLISHED, AgentStatus.APPROVED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot archive agent in {agent.status.value} status"
        )
    
    agent.status = AgentStatus.ARCHIVED
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.post("/agents/{agent_id}/republish", response_model=AgentSchema)
def republish_agent(
    agent_id: str,
    admin_id: str = Query(..., description="Admin user ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Republish an archived agent back to the marketplace.
    """
    verify_admin(admin_id, db)
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status != AgentStatus.ARCHIVED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot republish agent in {agent.status.value} status. Only ARCHIVED agents can be republished."
        )
    
    agent.status = AgentStatus.PUBLISHED
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    return agent


# ==========================================
# ADMIN DASHBOARD STATS
# ==========================================

@router.get("/stats")
def get_admin_stats(
    admin_id: str = Query(..., description="Admin user ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Get marketplace admin statistics.
    """
    try:
        verify_admin(admin_id, db)
        
        from app.models.license import License, LicenseStatus
        
        total_agents = db.query(Agent).count()
        pending_review = db.query(Agent).filter(Agent.status == AgentStatus.PENDING_REVIEW).count()
        published = db.query(Agent).filter(Agent.status == AgentStatus.PUBLISHED).count()
        drafts = db.query(Agent).filter(Agent.status == AgentStatus.DRAFT).count()
        rejected = db.query(Agent).filter(Agent.status == AgentStatus.REJECTED).count()
        archived = db.query(Agent).filter(Agent.status == AgentStatus.ARCHIVED).count()
        
        # Safer publisher count
        try:
            total_publishers = db.query(User).join(Agent, Agent.publisher_id == User.id).distinct().count()
        except:
            total_publishers = 0
        
        return {
            "total_agents": total_agents,
            "pending_review": pending_review,
            "published": published,
            "drafts": drafts,
            "rejected": rejected,
            "archived": archived,
            "total_publishers": total_publishers
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
def get_admin_dashboard(
    admin_id: str = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Get comprehensive admin dashboard data."""
    verify_admin(admin_id, db)
    
    from app.models.license import License, LicenseStatus
    
    total_users = db.query(User).count()
    total_agents = db.query(Agent).count()
    total_licenses = db.query(License).filter(License.status == LicenseStatus.ACTIVE).count()
    
    # Revenue calculation
    active_licenses = db.query(License).filter(License.status == LicenseStatus.ACTIVE).all()
    total_revenue = 0
    for lic in active_licenses:
        agent = db.query(Agent).filter(Agent.id == lic.agent_id).first()
        if agent:
            total_revenue += agent.price_cents
    
    # Recent activity (last 10 agents)
    recent_agents = db.query(Agent).order_by(Agent.created_at.desc()).limit(10).all()
    
    # Recent licenses (last 10)
    recent_licenses = db.query(License).order_by(License.start_date.desc()).limit(10).all()
    
    return {
        "stats": {
            "total_users": total_users,
            "total_agents": total_agents,
            "active_licenses": total_licenses,
            "total_revenue": total_revenue,
            "monthly_revenue": total_revenue // 12 if total_revenue > 0 else 0
        },
        "recent_activity": [
            {
                "type": "agent",
                "id": str(a.id),
                "name": a.name,
                "status": a.status.value,
                "created_at": a.created_at.isoformat() if a.created_at else None
            } for a in recent_agents
        ],
        "recent_licenses": [
            {
                "id": str(l.id),
                "user_id": str(l.user_id),
                "agent_id": str(l.agent_id),
                "status": l.status.value,
                "created_at": l.created_at.isoformat() if l.created_at else None
            } for l in recent_licenses
        ]
    }


# ==========================================
# USER & ROLE MANAGEMENT
# ==========================================

@router.get("/users")
def list_all_users(
    admin_id: str = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """List all users with their roles."""
    verify_admin(admin_id, db)
    
    users = db.query(User).all()
    
    return [
        {
            "id": str(u.id),
            "name": u.name or u.email.split('@')[0],
            "email": u.email,
            "role": u.role or 'ORG_USER',
            "is_admin": str(u.role or '').upper() == 'ORG_ADMIN',
            "created_at": u.created_at.isoformat() if hasattr(u, 'created_at') and u.created_at else None,
            # Count published agents (publisher role indicator)
            "published_agents": db.query(Agent).filter(Agent.publisher_id == u.id).count()
        } for u in users
    ]


@router.post("/users/invite")
def invite_user(
    admin_id: str = Query(..., description="Admin user ID"),
    email: str = Query(..., description="Email of user to invite"),
    name: str = Query(None, description="Name of user"),
    role: str = Query("ORG_USER", description="Role to assign: ORG_ADMIN, ORG_USER, PUBLISHER"),
    access_type: str = Query("PASSWORD", description="Access type: PASSWORD, RESET_EMAIL, MAGIC_LINK"),
    password: str = Query(None, description="Temporary password (required if access_type is PASSWORD)"),
    db: Session = Depends(get_db)
):
    """
    Invite a new user and assign a role.
    
    Access types:
    - PASSWORD: Admin sets a temporary password for the user
    - RESET_EMAIL: User receives a password reset email (placeholder - email not implemented)
    - MAGIC_LINK: User receives a magic login link each time (placeholder - email not implemented)
    """
    from app.core.security import get_password_hash
    
    admin_user = verify_admin(admin_id, db)
    
    # Check if user already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate role
    valid_roles = ['ORG_ADMIN', 'ORG_USER', 'PUBLISHER']
    if role.upper() not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    # Validate access type
    valid_access_types = ['PASSWORD', 'RESET_EMAIL', 'MAGIC_LINK']
    if access_type.upper() not in valid_access_types:
        raise HTTPException(status_code=400, detail=f"Invalid access type. Must be one of: {valid_access_types}")
    
    # Handle password requirement
    password_hash = None
    if access_type.upper() == 'PASSWORD':
        if not password:
            raise HTTPException(status_code=400, detail="Password is required when access_type is PASSWORD")
        password_hash = get_password_hash(password)
    
    # Create new user
    new_user = User(
        email=email,
        name=name,
        role=role.upper(),
        password_hash=password_hash,
        organization_id=admin_user.organization_id,  # Same org as admin
        is_active=True,
        is_verified=True,
        is_approved=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Response message based on access type
    access_message = {
        'PASSWORD': 'User can login with the provided password',
        'RESET_EMAIL': 'Password reset email will be sent (email integration pending)',
        'MAGIC_LINK': 'Magic link login enabled (email integration pending)'
    }
    
    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "name": new_user.name,
        "role": new_user.role,
        "access_type": access_type.upper(),
        "message": f"User invited successfully. {access_message[access_type.upper()]}"
    }


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    admin_id: str = Query(..., description="Admin user ID"),
    new_role: str = Query(..., description="New role: ORG_ADMIN, ORG_USER, PUBLISHER"),
    db: Session = Depends(get_db)
):
    """Update a user's role."""
    verify_admin(admin_id, db)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role
    valid_roles = ['ORG_ADMIN', 'ORG_USER', 'PUBLISHER']
    if new_role.upper() not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    user.role = new_role.upper()
    db.commit()
    db.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "is_admin": str(user.role or '').upper() == 'ORG_ADMIN',
        "message": f"User role updated to {user.role}"
    }


# ==========================================
# LICENSE MANAGEMENT
# ==========================================

@router.get("/licenses")
def list_all_licenses(
    admin_id: str = Query(..., description="Admin user ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """List all licenses in the system."""
    verify_admin(admin_id, db)
    
    from app.models.license import License, LicenseStatus
    
    query = db.query(License)
    
    if status_filter:
        try:
            status_enum = LicenseStatus(status_filter.upper())
            query = query.filter(License.status == status_enum)
        except ValueError:
            pass
    
    licenses = query.all()
    
    result = []
    for lic in licenses:
        user = db.query(User).filter(User.id == lic.user_id).first()
        agent = db.query(Agent).filter(Agent.id == lic.agent_id).first()
        
        result.append({
            "id": str(lic.id),
            "user_name": user.name or user.email.split('@')[0] if user else "Unknown",
            "user_email": user.email if user else "N/A",
            "agent_name": agent.name if agent else "Unknown",
            "agent_id": str(lic.agent_id),
            "status": lic.status.value,
            "start_date": lic.start_date.isoformat() if lic.start_date else None,
            "end_date": lic.end_date.isoformat() if lic.end_date else None,
            "price_cents": agent.price_cents if agent else 0
        })
    
    return result


@router.put("/licenses/{license_id}/status")
def update_license_status(
    license_id: str,
    admin_id: str = Query(..., description="Admin user ID"),
    new_status: str = Query(..., description="New status (ACTIVE, SUSPENDED, EXPIRED)"),
    db: Session = Depends(get_db)
):
    """Update license status (suspend/reactivate)."""
    verify_admin(admin_id, db)
    
    from app.models.license import License, LicenseStatus
    
    license_obj = db.query(License).filter(License.id == license_id).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    
    try:
        status_enum = LicenseStatus(new_status.upper())
        license_obj.status = status_enum
        db.commit()
        db.refresh(license_obj)
        
        return {
            "id": str(license_obj.id),
            "status": license_obj.status.value,
            "message": f"License status updated to {new_status}"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")


# ==========================================
# AGENT CERTIFICATION
# ==========================================

@router.put("/agents/{agent_id}/certify")
def certify_agent(
    agent_id: str,
    admin_id: str = Query(..., description="Admin user ID"),
    certification_level: str = Query(..., description="Certification level (BASIC, VERIFIED, CERTIFIED)"),
    db: Session = Depends(get_db)
):
    """Certify an agent with a specific certification level."""
    admin_user = verify_admin(admin_id, db)
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    valid_levels = ["BASIC", "VERIFIED", "CERTIFIED"]
    if certification_level.upper() not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid certification level. Must be one of: {valid_levels}")
    
    agent.certification_level = certification_level.upper()
    agent.certified_at = datetime.utcnow()
    agent.certified_by = admin_user.id
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    return {
        "id": str(agent.id),
        "name": agent.name,
        "certification_level": agent.certification_level,
        "certified_at": agent.certified_at.isoformat() if agent.certified_at else None,
        "message": f"Agent certified as {certification_level.upper()}"
    }


# ==========================================
# ORGANIZATION MANAGEMENT
# ==========================================

@router.get("/organizations/pending")
def list_pending_organizations(
    admin_id: str = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """List all organizations pending approval."""
    verify_admin(admin_id, db)
    
    pending_orgs = db.query(Organization).filter(
        Organization.subscription_status == SubscriptionStatus.PENDING
    ).order_by(Organization.created_at.asc()).all()
    
    return pending_orgs


@router.post("/organizations/{org_id}/approve")
def approve_organization(
    org_id: str,
    admin_id: str = Query(..., description="Admin user ID"),
    db: Session = Depends(get_db)
):
    """Approve a pending organization."""
    admin_user = verify_admin(admin_id, db)
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org.subscription_status = SubscriptionStatus.ACTIVE
    org.approved_by = admin_user.id
    org.approved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(org)
    
    return {"message": f"Organization {org.name} approved successfully", "status": "active"}

