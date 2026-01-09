"""
Runtime Management API Endpoints.
Control Docker containers for agent deployments.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.agent_deployment import AgentDeployment
from app.models.license import License, LicenseStatus
from app.models.enums import DeploymentStatus, DeploymentType
from app.services.docker_runtime import get_docker_runtime
from app.services.package_storage import get_package_storage
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RuntimeStartRequest(BaseModel):
    """Request to start an agent runtime."""
    deployment_id: str
    adapter: str = "openai"
    port: int = 8080
    env_vars: Optional[Dict[str, str]] = None


class RuntimeBuildRequest(BaseModel):
    """Request to build an agent image."""
    agent_id: str
    version: str


# ==========================================
# DOCKER STATUS
# ==========================================

@router.get("/status")
def check_docker_status():
    """Check if Docker is available."""
    runtime = get_docker_runtime()
    available = runtime.is_docker_available()
    
    return {
        "docker_available": available,
        "message": "Docker is ready" if available else "Docker is not running or not installed"
    }


@router.get("/containers")
def list_containers():
    """List all running PostQode agent containers."""
    runtime = get_docker_runtime()
    containers = runtime.list_running_containers()
    
    return {
        "count": len(containers),
        "containers": containers
    }


# ==========================================
# BUILD OPERATIONS
# ==========================================

@router.post("/build")
def build_agent_image(
    agent_id: str = Query(..., description="Agent ID"),
    user_id: str = Query(..., description="User ID (must be publisher)"),
    db: Session = Depends(get_db)
):
    """
    Build Docker image from agent package.
    Must be the publisher of the agent.
    """
    # Verify agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if str(agent.publisher_id) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not agent.package_url:
        raise HTTPException(status_code=400, detail="Agent has no package uploaded")
    
    # Get package path
    storage = get_package_storage()
    package_path = storage.get_package_path(agent_id, agent.version)
    
    if not package_path:
        raise HTTPException(status_code=404, detail="Package file not found")
    
    # Build image
    runtime = get_docker_runtime()
    
    if not runtime.is_docker_available():
        raise HTTPException(status_code=503, detail="Docker is not available")
    
    result = runtime.build_image_from_package(
        agent_id=agent_id,
        version=agent.version,
        package_path=package_path
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Build failed"))
    
    return {
        "message": "Image built successfully",
        "image_name": result.get("image_name"),
        "build_id": result.get("build_id")
    }


# ==========================================
# CONTAINER OPERATIONS
# ==========================================

@router.post("/start")
def start_container(
    request: RuntimeStartRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Start an agent container from a deployment.
    Requires valid license and existing deployment record.
    """
    # Get deployment
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == request.deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Verify license is active
    license = db.query(License).filter(
        License.id == deployment.license_id,
        License.status == LicenseStatus.ACTIVE
    ).first()
    
    if not license:
        raise HTTPException(status_code=403, detail="Valid license required")
    
    # Get agent info
    agent = db.query(Agent).filter(Agent.id == deployment.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Start container
    runtime = get_docker_runtime()
    
    if not runtime.is_docker_available():
        raise HTTPException(status_code=503, detail="Docker is not available")
    
    result = runtime.run_container(
        deployment_id=str(deployment.id),
        agent_id=str(agent.id),
        version=agent.version,
        adapter=request.adapter,
        env_vars=request.env_vars,
        port=request.port
    )
    
    if not result.get("success"):
        # Update deployment status to error
        deployment.status = DeploymentStatus.ERROR
        deployment.error_message = result.get("error", "Failed to start container")
        db.commit()
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    # Update deployment status
    deployment.status = DeploymentStatus.ACTIVE
    deployment.deployment_type = DeploymentType.DOCKER
    deployment.adapter_used = request.adapter
    deployment.deployed_at = datetime.utcnow()
    deployment.error_message = None
    db.commit()
    
    return {
        "message": "Container started successfully",
        "container_id": result.get("container_id"),
        "container_name": result.get("container_name"),
        "port": result.get("port"),
        "url": f"http://localhost:{result.get('port')}"
    }


@router.post("/stop")
def stop_container(
    deployment_id: str = Query(..., description="Deployment ID"),
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Stop a running agent container."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    runtime = get_docker_runtime()
    result = runtime.stop_container(
        deployment_id=str(deployment.id),
        agent_id=str(deployment.agent_id)
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    # Update deployment status
    deployment.status = DeploymentStatus.STOPPED
    deployment.stopped_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Container stopped", "deployment_id": deployment_id}


@router.get("/status/{deployment_id}")
def get_container_status(
    deployment_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get status of a deployed container."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    runtime = get_docker_runtime()
    container_status = runtime.get_container_status(
        deployment_id=str(deployment.id),
        agent_id=str(deployment.agent_id)
    )
    
    return {
        "deployment_id": deployment_id,
        "deployment_status": deployment.status.value,
        "container_status": container_status.get("status"),
        "container_running": container_status.get("running"),
        "last_health_check": deployment.last_health_check,
        "total_invocations": deployment.total_invocations
    }


@router.get("/logs/{deployment_id}")
def get_container_logs(
    deployment_id: str,
    user_id: str = Query(..., description="User ID"),
    tail: int = Query(100, description="Number of lines to return"),
    db: Session = Depends(get_db)
):
    """Get logs from a running container."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    runtime = get_docker_runtime()
    result = runtime.get_container_logs(
        deployment_id=str(deployment.id),
        agent_id=str(deployment.agent_id),
        tail=tail
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {
        "deployment_id": deployment_id,
        "logs": result.get("logs"),
        "stderr": result.get("stderr")
    }
