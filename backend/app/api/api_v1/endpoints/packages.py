"""
Package Management API Endpoints.
Handles agent package upload, download, and installation commands.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.agent_adapter import AgentAdapter
from app.models.license import License, LicenseStatus
from app.models.user import User
from app.models.enums import AgentStatus
from app.services.package_storage import get_package_storage, ManifestValidation
from app.schemas.agent import AgentAdapterSchema, AgentAdapterCreate
from datetime import datetime
import yaml

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# PACKAGE UPLOAD ENDPOINTS (Publisher)
# ==========================================

@router.post("/agents/{agent_id}/upload")
async def upload_agent_package(
    agent_id: str,
    publisher_id: str = Query(..., description="Publisher user ID"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an agent package (zip file).
    Extracts manifest, validates, and stores the package.
    """
    # Verify agent exists and belongs to publisher
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if str(agent.publisher_id) != publisher_id:
        raise HTTPException(status_code=403, detail="Not authorized to upload to this agent")
    
    # Can only upload to DRAFT or REJECTED agents
    if agent.status not in [AgentStatus.DRAFT, AgentStatus.REJECTED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload package for agent in {agent.status.value} status"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate package
    storage = get_package_storage()
    validation = storage.validate_package(content)
    
    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Package validation failed",
                "errors": validation.errors,
                "warnings": validation.warnings
            }
        )
    
    # Upload package
    package_info = storage.upload_package(
        agent_id=agent_id,
        version=agent.version,
        package_content=content,
        filename=file.filename or "package.zip"
    )
    
    # Update agent with package info
    agent.manifest_yaml = yaml.dump(package_info.manifest) if package_info.manifest else None
    agent.package_url = package_info.url
    agent.package_checksum = package_info.checksum
    agent.package_size_bytes = package_info.size_bytes
    
    # Extract runtime info from manifest
    if package_info.manifest:
        spec = package_info.manifest.get("spec", {})
        runtime = spec.get("runtime", {})
        agent.supported_runtimes = runtime.get("supportedRuntimes", ["postqode-runtime"])
        agent.min_runtime_version = runtime.get("minVersion", "1.0.0")
        agent.inputs_schema = spec.get("inputs", [])
        agent.outputs_schema = spec.get("outputs", [])
    
    agent.updated_at = datetime.utcnow()
    db.commit()
    
    # Create adapters from package
    for adapter_type in package_info.adapters:
        existing = db.query(AgentAdapter).filter(
            AgentAdapter.agent_id == agent.id,
            AgentAdapter.adapter_type == adapter_type
        ).first()
        
        if not existing:
            adapter = AgentAdapter(
                agent_id=agent.id,
                adapter_type=adapter_type,
                display_name=adapter_type.title(),
                config_yaml="",  # Will be populated from package
                is_default=(adapter_type == "openai")
            )
            db.add(adapter)
    
    db.commit()
    
    return {
        "message": "Package uploaded successfully",
        "package_url": package_info.url,
        "checksum": package_info.checksum,
        "size_bytes": package_info.size_bytes,
        "adapters_found": package_info.adapters,
        "warnings": validation.warnings
    }


@router.post("/agents/{agent_id}/validate-package")
async def validate_package(
    agent_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Validate a package without uploading it.
    Returns validation errors and warnings.
    """
    content = await file.read()
    storage = get_package_storage()
    validation = storage.validate_package(content)
    
    return {
        "is_valid": validation.is_valid,
        "manifest": validation.manifest,
        "errors": validation.errors,
        "warnings": validation.warnings
    }


@router.get("/agents/{agent_id}/manifest")
def get_agent_manifest(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Get the parsed manifest for an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.manifest_yaml:
        raise HTTPException(status_code=404, detail="No manifest found for this agent")
    
    return yaml.safe_load(agent.manifest_yaml)


# ==========================================
# ADAPTER MANAGEMENT
# ==========================================

@router.get("/agents/{agent_id}/adapters", response_model=List[AgentAdapterSchema])
def list_agent_adapters(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """List all runtime adapters for an agent."""
    adapters = db.query(AgentAdapter).filter(AgentAdapter.agent_id == agent_id).all()
    return adapters


@router.post("/agents/{agent_id}/adapters", response_model=AgentAdapterSchema)
def add_agent_adapter(
    agent_id: str,
    adapter_data: AgentAdapterCreate,
    publisher_id: str = Query(..., description="Publisher user ID"),
    db: Session = Depends(get_db)
):
    """Add a new runtime adapter to an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if str(agent.publisher_id) != publisher_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    adapter = AgentAdapter(
        agent_id=agent.id,
        adapter_type=adapter_data.adapter_type,
        display_name=adapter_data.display_name,
        config_yaml=adapter_data.config_yaml,
        is_default=adapter_data.is_default
    )
    db.add(adapter)
    db.commit()
    db.refresh(adapter)
    
    return adapter


# ==========================================
# PACKAGE DOWNLOAD (Buyer)
# ==========================================

@router.get("/agents/{agent_id}/download")
def get_download_url(
    agent_id: str,
    user_id: str = Query(..., description="User ID (must have valid license)"),
    db: Session = Depends(get_db)
):
    """
    Get download URL for an agent package.
    Requires valid license.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status != AgentStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Agent not available")
    
    # Check license
    license = db.query(License).filter(
        License.agent_id == agent_id,
        License.user_id == user_id,
        License.status == LicenseStatus.ACTIVE
    ).first()
    
    if not license:
        raise HTTPException(status_code=403, detail="Valid license required to download")
    
    if not agent.package_url:
        raise HTTPException(status_code=404, detail="No package available")
    
    storage = get_package_storage()
    download_url = storage.get_download_url(agent_id, agent.version)
    
    return {
        "download_url": download_url,
        "version": agent.version,
        "checksum": agent.package_checksum,
        "size_bytes": agent.package_size_bytes
    }


@router.get("/packages/{agent_id}/{version}/download")
def download_package_file(
    agent_id: str,
    version: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Direct package file download."""
    # Verify license
    license = db.query(License).filter(
        License.agent_id == agent_id,
        License.user_id == user_id,
        License.status == LicenseStatus.ACTIVE
    ).first()
    
    if not license:
        raise HTTPException(status_code=403, detail="Valid license required")
    
    storage = get_package_storage()
    package_path = storage.get_package_path(agent_id, version)
    
    if not package_path:
        raise HTTPException(status_code=404, detail="Package not found")
    
    return FileResponse(
        path=package_path,
        filename=f"{agent_id}-{version}.zip",
        media_type="application/zip"
    )


# ==========================================
# INSTALLATION COMMANDS
# ==========================================

@router.get("/agents/{agent_id}/install-cmd")
def get_install_command(
    agent_id: str,
    adapter: str = Query("openai", description="Runtime adapter to use"),
    db: Session = Depends(get_db)
):
    """Get CLI install command for an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Sanitize agent name for Docker/CLI (lowercase, no spaces, alphanumeric + dashes)
    safe_name = agent.name.lower().replace(" ", "-").replace("_", "-")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")
    
    return {
        "cli": f"qode agent install {safe_name}@{agent.version} --adapter={adapter}",
        "docker": f"docker pull postqode/{safe_name}:{agent.version}",
        "helm": f"helm install {safe_name} postqode/{safe_name} --version {agent.version} --set adapter={adapter}",
        "note": "The PostQode registry requires a valid license. Run 'qode login' first."
    }


@router.get("/agents/{agent_id}/helm-values")
def get_helm_values(
    agent_id: str,
    adapter: str = Query("openai", description="Runtime adapter"),
    db: Session = Depends(get_db)
):
    """Generate Helm values.yaml for Kubernetes deployment."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    values = {
        "agent": {
            "name": agent.name,
            "version": agent.version
        },
        "adapter": adapter,
        "resources": {
            "requests": {
                "memory": "512Mi",
                "cpu": "500m"
            },
            "limits": {
                "memory": "2Gi",
                "cpu": "2"
            }
        },
        "secrets": {
            "apiKeySecretName": f"{agent.name}-secrets"
        }
    }
    
    return {"values": values, "yaml": yaml.dump(values)}


@router.get("/agents/{agent_id}/docker-compose")
def get_docker_compose(
    agent_id: str,
    adapter: str = Query("openai", description="Runtime adapter"),
    db: Session = Depends(get_db)
):
    """Generate docker-compose.yaml for local deployment."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    compose = {
        "version": "3.8",
        "services": {
            agent.name: {
                "image": f"postqode.io/agents/{agent.name}:{agent.version}",
                "environment": [
                    f"ADAPTER={adapter}",
                    "OPENAI_API_KEY=${OPENAI_API_KEY}"
                ],
                "ports": ["8080:8080"],
                "volumes": ["./data:/workspace"]
            }
        }
    }
    
    return {"compose": compose, "yaml": yaml.dump(compose)}
