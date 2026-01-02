from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.license import License, LicenseStatus
from app.models.user import User
from app.models.enums import AgentStatus
from app.schemas.agent import (
    Agent as AgentSchema,
    AgentCreate,
    AgentUpdate,
    AgentSubmit,
    AgentPublisherView,
    AgentBrief
)
from datetime import datetime, timedelta
import uuid

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# PUBLIC MARKETPLACE ENDPOINTS
# ==========================================

@router.get("/agents", response_model=List[AgentSchema])
def read_agents(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[List[str]] = Query(None),
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List all PUBLISHED agents in the marketplace."""
    query = db.query(Agent).filter(Agent.status == AgentStatus.PUBLISHED)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(Agent.name.ilike(search_filter) | Agent.description.ilike(search_filter))
    
    if category:
        query = query.filter(Agent.category.in_(category))
        
    if min_price is not None:
        query = query.filter(Agent.price_cents >= min_price)
        
    if max_price is not None:
        query = query.filter(Agent.price_cents <= max_price)
        
    return query.offset(skip).limit(limit).all()


@router.get("/agents/{agent_id}", response_model=AgentSchema)
def read_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get a single published agent by ID."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    # Only return published agents to public
    if agent.status != AgentStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ==========================================
# PUBLISHER ENDPOINTS (Agent Submission)
# ==========================================

@router.post("/agents", response_model=AgentSchema, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_data: AgentCreate,
    publisher_id: str = Query(..., description="Publisher user ID"),
    db: Session = Depends(get_db)
):
    """
    Create a new agent (publisher submission).
    Agent starts in DRAFT status and must be submitted for review.
    """
    # Verify publisher exists
    publisher = db.query(User).filter(User.id == publisher_id).first()
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")
    
    # Create agent in DRAFT status
    agent = Agent(
        **agent_data.model_dump(),
        publisher_id=publisher.id,
        status=AgentStatus.DRAFT,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return agent


@router.put("/agents/{agent_id}", response_model=AgentSchema)
def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    publisher_id: str = Query(..., description="Publisher user ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Update an agent. Only allowed in DRAFT or REJECTED status.
    Publisher can only update their own agents.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Authorization: publisher can only edit own agents
    if str(agent.publisher_id) != publisher_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this agent")
    
    # Can only edit in DRAFT or REJECTED status
    if agent.status not in [AgentStatus.DRAFT, AgentStatus.REJECTED]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot edit agent in {agent.status.value} status. Only DRAFT or REJECTED agents can be edited."
        )
    
    # Update only provided fields
    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(agent, field, value)
    
    agent.updated_at = datetime.utcnow()
    # Clear rejection reason if resubmitting
    if agent.status == AgentStatus.REJECTED:
        agent.rejection_reason = None
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.post("/agents/{agent_id}/submit", response_model=AgentSchema)
def submit_agent_for_review(
    agent_id: str,
    submit_data: AgentSubmit,
    publisher_id: str = Query(..., description="Publisher user ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Submit an agent for admin review.
    Can only submit agents in DRAFT or REJECTED status.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Authorization
    if str(agent.publisher_id) != publisher_id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this agent")
    
    # Can only submit from DRAFT or REJECTED status
    if agent.status not in [AgentStatus.DRAFT, AgentStatus.REJECTED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit agent in {agent.status.value} status"
        )
    
    agent.status = AgentStatus.PENDING_REVIEW
    agent.submitted_at = datetime.utcnow()
    agent.updated_at = datetime.utcnow()
    agent.rejection_reason = None
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.get("/agents/my/list", response_model=List[AgentSchema])
def list_my_agents(
    publisher_id: str = Query(..., description="Publisher user ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    List all agents belonging to a publisher.
    Publishers can see their own agents in any status.
    """
    query = db.query(Agent).filter(Agent.publisher_id == publisher_id)
    
    if status_filter:
        try:
            agent_status = AgentStatus(status_filter)
            query = query.filter(Agent.status == agent_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
    
    return query.order_by(Agent.created_at.desc()).all()


# ==========================================
# PUBLISHER SUBSCRIBERS ENDPOINT
# ==========================================

@router.get("/publisher/subscribers")
def get_publisher_subscribers(
    publisher_id: str = Query(..., description="Publisher user ID"),
    db: Session = Depends(get_db)
):
    """
    Get all subscribers (license holders) for a publisher's agents.
    Returns subscriber details, license info, and revenue stats.
    """
    try:
        # Get all publisher's agents
        publisher_agents = db.query(Agent).filter(Agent.publisher_id == publisher_id).all()
        agent_ids = [str(a.id) for a in publisher_agents]
        
        if not agent_ids:
            return {
                "subscribers": [],
                "stats": {
                    "total_subscribers": 0,
                    "active_licenses": 0,
                    "monthly_revenue": 0,
                    "total_revenue": 0
                }
            }
        
        # Get all licenses for these agents
        licenses = db.query(License).filter(License.agent_id.in_(agent_ids)).all()
        
        # Build subscriber list
        subscribers = []
        for lic in licenses:
            user = db.query(User).filter(User.id == lic.user_id).first()
            agent = db.query(Agent).filter(Agent.id == lic.agent_id).first()
            
            if user and agent:
                subscribers.append({
                    "id": str(lic.id),
                    "user_name": user.name or user.email.split('@')[0],
                    "user_email": user.email,
                    "agent_name": agent.name,
                    "agent_id": str(agent.id),
                    "license_status": lic.status.value,
                    "start_date": lic.start_date.isoformat() if lic.start_date else None,
                    "end_date": lic.end_date.isoformat() if lic.end_date else None,
                    "price_cents": agent.price_cents
                })
        
        # Calculate stats
        active_licenses = len([l for l in licenses if l.status == LicenseStatus.ACTIVE])
        total_subscribers = len(set([str(l.user_id) for l in licenses]))
        
        # Calculate revenue (sum of all agent prices for active licenses)
        total_revenue = sum([agent.price_cents for agent in publisher_agents for l in licenses 
                           if str(l.agent_id) == str(agent.id) and l.status == LicenseStatus.ACTIVE])
        
        # Monthly revenue (assuming annual licenses, divide by 12)
        monthly_revenue = total_revenue // 12 if total_revenue > 0 else 0
        
        return {
            "subscribers": subscribers,
            "stats": {
                "total_subscribers": total_subscribers,
                "active_licenses": active_licenses,
                "monthly_revenue": monthly_revenue,
                "total_revenue": total_revenue
            }
        }
    except Exception as e:
        return {
            "subscribers": [],
            "stats": {
                "total_subscribers": 0,
                "active_licenses": 0,
                "monthly_revenue": 0,
                "total_revenue": 0
            },
            "error": str(e)
        }




# ==========================================
# LICENSE ENDPOINTS (Purchase Flow)
# ==========================================

@router.post("/licenses", status_code=status.HTTP_201_CREATED)
def create_license(
    license_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Create a license for a user to access an agent.
    This is the purchase flow endpoint.
    """
    user_id = license_data.get("user_id")
    agent_id = license_data.get("agent_id")
    license_type = license_data.get("license_type", "standard")
    
    if not user_id or not agent_id:
        raise HTTPException(status_code=400, detail="user_id and agent_id are required")
    
    # Verify agent exists and is published
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.status != AgentStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Agent is not available for purchase")
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user already has an active license for this agent
    existing = db.query(License).filter(
        License.user_id == user_id,
        License.agent_id == agent_id,
        License.status == LicenseStatus.ACTIVE
    ).first()
    
    if existing:
        return {"id": str(existing.id), "message": "License already exists", "status": "active"}
    
    # Create the license
    license = License(
        id=uuid.uuid4(),
        user_id=user_id,
        agent_id=agent_id,
        status=LicenseStatus.ACTIVE,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=365),  # 1 year license
        renewal_date=datetime.utcnow() + timedelta(days=335),  # Renewal notice 30 days before expiry
    )
    
    db.add(license)
    db.commit()
    db.refresh(license)
    
    return {
        "id": str(license.id),
        "user_id": str(license.user_id),
        "agent_id": str(license.agent_id),
        "status": license.status.value,
        "start_date": license.start_date,
        "end_date": license.end_date,
        "message": "License created successfully"
    }


# ==========================================
# DASHBOARD ENDPOINT
# ==========================================

@router.get("/dashboard")
def get_dashboard_data(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Get dashboard data for a user including licenses and published agents."""
    try:
        # Simulating a logged-in user if not provided (normally from auth token)
        if not user_id:
            user = db.query(User).first()
            if not user:
                user = User(name="John Doe", email="john@example.com")
                db.add(user)
                db.commit()
                db.refresh(user)
            user_id = str(user.id)
        
        today = datetime.utcnow()
        next_30_days = today + timedelta(days=30)
        
        # Expiring licenses
        expiring_licenses = db.query(License).filter(
            License.user_id == user_id,
            License.status == LicenseStatus.ACTIVE,
            License.end_date <= next_30_days,
            License.end_date >= today
        ).all()
        
        # Renewals due
        renewals = db.query(License).filter(
            License.user_id == user_id,
            License.renewal_date <= next_30_days
        ).all()
        
        # My licensed agents
        my_agents = db.query(License).filter(
            License.user_id == user_id,
            License.status == LicenseStatus.ACTIVE
        ).all()
        
        # Publisher stats: agents I've published
        published_agents = db.query(Agent).filter(
            Agent.publisher_id == user_id
        ).all()
        
        return {
            "action_required": [
                {
                    "id": str(l.id),
                    "agent_name": l.agent.name if l.agent else "Unknown",
                    "agent_version": l.agent.version if l.agent else "1.0.0",
                    "type": "Expiring Soon"
                } for l in expiring_licenses if l.agent
            ],
            "renewals_due": [
                {
                    "id": str(l.id),
                    "agent_name": l.agent.name if l.agent else "Unknown",
                    "renewal_date": l.renewal_date,
                    "days_remaining": (l.renewal_date - today).days if l.renewal_date else 0,
                    "publisher": l.agent.publisher.name if l.agent and l.agent.publisher else "Unknown"
                } for l in renewals if l.agent
            ],
            "my_agents": [
                {
                    "id": str(l.agent.id) if l.agent else "",
                    "name": l.agent.name if l.agent else "Unknown",
                    "category": l.agent.category if l.agent else "",
                    "price_cents": l.agent.price_cents if l.agent else 0,
                    "usage_percentage": 76,
                    "sessions_used": 19,
                    "sessions_total": 25,
                    "last_active": datetime.utcnow(),
                    "status": "Active"
                } for l in my_agents if l.agent
            ],
            "publisher_stats": {
                "total_agents": len(published_agents),
                "published": len([a for a in published_agents if a.status == AgentStatus.PUBLISHED]),
                "pending_review": len([a for a in published_agents if a.status == AgentStatus.PENDING_REVIEW]),
                "drafts": len([a for a in published_agents if a.status == AgentStatus.DRAFT]),
            }
        }
    except Exception as e:
        # Return empty dashboard on error
        return {
            "action_required": [],
            "renewals_due": [],
            "my_agents": [],
            "publisher_stats": {
                "total_agents": 0,
                "published": 0,
                "pending_review": 0,
                "drafts": 0,
            },
            "error": str(e)
        }


# ==========================================
# SEED ENDPOINT (Development only)
# ==========================================

@router.post("/seed")
def seed_db(db: Session = Depends(get_db)):
    """Seed database with demo data."""
    if db.query(Agent).count() > 0:
        return {"message": "Database already seeded"}
        
    # Create Publisher User
    publisher = User(name="PostQode Official", email="official@postqode.ai", company_metadata={"type": "official"})
    db.add(publisher)
    db.commit()
    db.refresh(publisher)
    
    # Create Consumer User
    consumer = User(name="John Doe", email="john.doe@example.com")
    db.add(consumer)
    db.commit()
    db.refresh(consumer)
    
    # Create Agents (all PUBLISHED for backward compatibility)
    agents_data = [
        {
            "name": "Statement Agent",
            "description": "Reconcile member statements of account with corresponding financial records.",
            "category": "Finance",
            "price_cents": 29900,
            "publisher_id": publisher.id,
            "status": AgentStatus.PUBLISHED,
            "published_at": datetime.utcnow()
        },
        {
            "name": "Service Call Agent",
            "description": "AI-powered customer support automation.",
            "category": "Service Operations",
            "price_cents": 17500,
            "publisher_id": publisher.id,
            "status": AgentStatus.PUBLISHED,
            "published_at": datetime.utcnow()
        },
        {
            "name": "Booking Agent",
            "description": "Automated scheduling and reservation management system.",
            "category": "Service Operations",
            "price_cents": 12000,
            "publisher_id": publisher.id,
            "status": AgentStatus.PUBLISHED,
            "published_at": datetime.utcnow()
        },
        {
            "name": "Parts Inventory Manager",
            "description": "Track and manage automotive parts inventory.",
            "category": "Procurement",
            "price_cents": 35000,
            "publisher_id": publisher.id,
            "status": AgentStatus.PUBLISHED,
            "published_at": datetime.utcnow()
        },
        {
            "name": "Vehicle Diagnostic Assistant",
            "description": "Assist technicians with vehicle diagnostics.",
            "category": "Service Operations",
            "price_cents": 25000,
            "publisher_id": publisher.id,
            "status": AgentStatus.PUBLISHED,
            "published_at": datetime.utcnow()
        },
        {
            "name": "Customer Feedback Analyzer",
            "description": "Analyze customer sentiment and feedback.",
            "category": "Data Analytics",
            "price_cents": 15000,
            "publisher_id": publisher.id,
            "status": AgentStatus.PUBLISHED,
            "published_at": datetime.utcnow()
        }
    ]
    
    created_agents = []
    for data in agents_data:
        agent = Agent(**data)
        db.add(agent)
        created_agents.append(agent)
    
    db.commit()
    
    # Create Licenses for Consumer
    booking_agent = [a for a in created_agents if a.name == "Booking Agent"][0]
    service_agent = [a for a in created_agents if a.name == "Service Call Agent"][0]
    
    lic1 = License(
        user_id=consumer.id, 
        agent_id=booking_agent.id,
        status=LicenseStatus.ACTIVE,
        start_date=datetime.utcnow() - timedelta(days=60),
        end_date=datetime.utcnow() + timedelta(days=300),
        renewal_date=datetime.utcnow() + timedelta(days=300)
    )
    
    lic2 = License(
        user_id=consumer.id,
        agent_id=service_agent.id,
        status=LicenseStatus.ACTIVE,
        start_date=datetime.utcnow() - timedelta(days=330),
        end_date=datetime.utcnow() + timedelta(days=30),
        renewal_date=datetime.utcnow() + timedelta(days=30)
    )
    
    db.add(lic1)
    db.add(lic2)
    db.commit()
    
    return {"message": "Database seeded successfully"}

