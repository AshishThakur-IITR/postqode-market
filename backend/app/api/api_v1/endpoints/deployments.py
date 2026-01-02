"""
Deployment Management API Endpoints.
Track agent installations in customer environments.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.agent_deployment import AgentDeployment
from app.models.license import License, LicenseStatus
from app.models.user import User
from app.models.enums import DeploymentStatus, DeploymentType
from app.schemas.deployment import (
    Deployment, DeploymentBrief, DeploymentCreate, 
    DeploymentUpdate, DeploymentHealthUpdate
)
from datetime import datetime

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# DEPLOYMENT CRUD
# ==========================================

@router.get("", response_model=List[DeploymentBrief])
def list_deployments(
    user_id: str = Query(..., description="User ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """List all deployments for a user."""
    query = db.query(AgentDeployment).filter(AgentDeployment.user_id == user_id)
    
    if status:
        try:
            deployment_status = DeploymentStatus(status)
            query = query.filter(AgentDeployment.status == deployment_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    deployments = query.order_by(AgentDeployment.deployed_at.desc()).all()
    
    # Add agent names
    result = []
    for d in deployments:
        agent = db.query(Agent).filter(Agent.id == d.agent_id).first()
        result.append(DeploymentBrief(
            id=d.id,
            agent_id=d.agent_id,
            agent_name=agent.name if agent else None,
            deployment_type=d.deployment_type,
            status=d.status,
            deployed_at=d.deployed_at
        ))
    
    return result


@router.post("", response_model=Deployment)
def create_deployment(
    deployment_data: DeploymentCreate,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Register a new agent deployment.
    Called when user installs an agent in their environment.
    """
    # Verify license
    license = db.query(License).filter(
        License.id == deployment_data.license_id,
        License.user_id == user_id,
        License.status == LicenseStatus.ACTIVE
    ).first()
    
    if not license:
        raise HTTPException(status_code=403, detail="Valid license required")
    
    # Verify agent
    agent = db.query(Agent).filter(Agent.id == deployment_data.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    deployment = AgentDeployment(
        license_id=deployment_data.license_id,
        agent_id=deployment_data.agent_id,
        user_id=user_id,
        deployment_type=DeploymentType(deployment_data.deployment_type.value),
        adapter_used=deployment_data.adapter_used,
        deployment_config=deployment_data.deployment_config or {},
        environment_name=deployment_data.environment_name,
        status=DeploymentStatus.PENDING,
        deployed_at=datetime.utcnow()
    )
    
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    return Deployment(
        id=deployment.id,
        license_id=deployment.license_id,
        agent_id=deployment.agent_id,
        user_id=deployment.user_id,
        deployment_type=deployment.deployment_type,
        adapter_used=deployment.adapter_used,
        deployment_config=deployment.deployment_config,
        environment_name=deployment.environment_name,
        status=deployment.status,
        deployed_at=deployment.deployed_at,
        agent_name=agent.name,
        agent_version=agent.version
    )


@router.get("/{deployment_id}", response_model=Deployment)
def get_deployment(
    deployment_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get deployment details."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    agent = db.query(Agent).filter(Agent.id == deployment.agent_id).first()
    
    return Deployment(
        id=deployment.id,
        license_id=deployment.license_id,
        agent_id=deployment.agent_id,
        user_id=deployment.user_id,
        deployment_type=deployment.deployment_type,
        adapter_used=deployment.adapter_used,
        deployment_config=deployment.deployment_config,
        environment_name=deployment.environment_name,
        status=deployment.status,
        error_message=deployment.error_message,
        deployed_at=deployment.deployed_at,
        last_health_check=deployment.last_health_check,
        stopped_at=deployment.stopped_at,
        total_invocations=deployment.total_invocations,
        last_invocation=deployment.last_invocation,
        runtime_version=deployment.runtime_version,
        agent_name=agent.name if agent else None,
        agent_version=agent.version if agent else None
    )


@router.put("/{deployment_id}/status", response_model=Deployment)
def update_deployment_status(
    deployment_id: str,
    update_data: DeploymentUpdate,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Update deployment status."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if update_data.status:
        deployment.status = DeploymentStatus(update_data.status.value)
        if update_data.status == DeploymentStatus.STOPPED:
            deployment.stopped_at = datetime.utcnow()
    
    if update_data.error_message is not None:
        deployment.error_message = update_data.error_message
    
    if update_data.deployment_config is not None:
        deployment.deployment_config = update_data.deployment_config
    
    db.commit()
    db.refresh(deployment)
    
    agent = db.query(Agent).filter(Agent.id == deployment.agent_id).first()
    
    return Deployment(
        id=deployment.id,
        license_id=deployment.license_id,
        agent_id=deployment.agent_id,
        user_id=deployment.user_id,
        deployment_type=deployment.deployment_type,
        adapter_used=deployment.adapter_used,
        deployment_config=deployment.deployment_config,
        environment_name=deployment.environment_name,
        status=deployment.status,
        error_message=deployment.error_message,
        deployed_at=deployment.deployed_at,
        last_health_check=deployment.last_health_check,
        stopped_at=deployment.stopped_at,
        total_invocations=deployment.total_invocations,
        last_invocation=deployment.last_invocation,
        agent_name=agent.name if agent else None,
        agent_version=agent.version if agent else None
    )


@router.post("/{deployment_id}/health")
def health_check(
    deployment_id: str,
    health_data: DeploymentHealthUpdate,
    db: Session = Depends(get_db)
):
    """
    Health check ping from deployed agent.
    Updates last_health_check and optional invocation stats.
    """
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    deployment.last_health_check = datetime.utcnow()
    
    if health_data.total_invocations is not None:
        deployment.total_invocations = health_data.total_invocations
    
    if health_data.last_invocation is not None:
        deployment.last_invocation = health_data.last_invocation
    
    # If we receive a health check, mark as active
    if deployment.status == DeploymentStatus.PENDING:
        deployment.status = DeploymentStatus.ACTIVE
    
    db.commit()
    
    return {"message": "Health check recorded", "status": deployment.status.value}


@router.delete("/{deployment_id}")
def delete_deployment(
    deployment_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Delete/unregister a deployment."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    db.delete(deployment)
    db.commit()
    
    return {"message": "Deployment deleted"}


# ==========================================
# DEPLOYMENT STATS
# ==========================================

@router.get("/stats/summary")
def get_deployment_stats(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get deployment statistics for a user."""
    total = db.query(AgentDeployment).filter(AgentDeployment.user_id == user_id).count()
    active = db.query(AgentDeployment).filter(
        AgentDeployment.user_id == user_id,
        AgentDeployment.status == DeploymentStatus.ACTIVE
    ).count()
    stopped = db.query(AgentDeployment).filter(
        AgentDeployment.user_id == user_id,
        AgentDeployment.status == DeploymentStatus.STOPPED
    ).count()
    error = db.query(AgentDeployment).filter(
        AgentDeployment.user_id == user_id,
        AgentDeployment.status == DeploymentStatus.ERROR
    ).count()
    
    # Total invocations across all deployments
    total_invocations = db.query(AgentDeployment).filter(
        AgentDeployment.user_id == user_id
    ).with_entities(AgentDeployment.total_invocations).all()
    
    return {
        "total_deployments": total,
        "active": active,
        "stopped": stopped,
        "error": error,
        "total_invocations": sum(i[0] for i in total_invocations if i[0])
    }
