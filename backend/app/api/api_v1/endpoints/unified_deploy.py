"""
Unified Deployment API Endpoint.
One-click deployment: Configure → Build → Deploy → Run
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.agent_deployment import AgentDeployment
from app.models.license import License, LicenseStatus
from app.models.enums import DeploymentStatus, DeploymentType
from app.services.docker_runtime import get_docker_runtime
from app.services.package_storage import get_package_storage
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime
import uuid
import yaml

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# REQUEST/RESPONSE SCHEMAS
# ==========================================

class EnvVarConfig(BaseModel):
    """Environment variable configuration."""
    key: str
    value: str
    is_secret: bool = False
    description: Optional[str] = None


class UnifiedDeployRequest(BaseModel):
    """
    Unified deployment request - handles everything in one call.
    """
    agent_id: str
    adapter: str = "openai"
    deployment_type: str = "docker"  # docker, kubernetes, azure_functions, vm_standalone, edge
    environment_name: str = "production"
    port: int = 8080
    env_vars: Dict[str, str] = {}  # User-provided environment variables
    platform_config: Dict[str, Any] = {}  # Platform-specific configuration
    auto_start: bool = True  # Automatically start after build


class DeploymentStep(BaseModel):
    """A single step in the deployment process."""
    step: str
    status: str  # pending, running, completed, failed
    message: str
    timestamp: Optional[str] = None


class UnifiedDeployResponse(BaseModel):
    """Response from unified deployment."""
    deployment_id: str
    status: str
    steps: List[DeploymentStep]
    container_url: Optional[str] = None
    error: Optional[str] = None


class AgentEnvRequirements(BaseModel):
    """Environment requirements for an agent."""
    agent_id: str
    agent_name: str
    required_env_vars: List[Dict[str, Any]]
    optional_env_vars: List[Dict[str, Any]]
    supported_adapters: List[str]
    adapter_env_vars: Dict[str, List[Dict[str, Any]]]


# ==========================================
# GET AGENT ENVIRONMENT REQUIREMENTS
# ==========================================

@router.get("/agents/{agent_id}/env-requirements")
def get_env_requirements(
    agent_id: str,
    db: Session = Depends(get_db)
) -> AgentEnvRequirements:
    """
    Get environment variable requirements for an agent.
    Extracts from manifest and provides adapter-specific vars.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Base required env vars (all agents need these)
    required_env_vars = [
        {
            "key": "POSTQODE_AGENT_ID",
            "description": "Agent identifier (auto-set)",
            "auto_set": True,
            "value": str(agent.id)
        },
        {
            "key": "POSTQODE_DEPLOYMENT_ID", 
            "description": "Deployment identifier (auto-set)",
            "auto_set": True
        }
    ]
    
    optional_env_vars = [
        {
            "key": "LOG_LEVEL",
            "description": "Logging level (DEBUG, INFO, WARNING, ERROR)",
            "default": "INFO"
        },
        {
            "key": "POSTQODE_AGENT_PORT",
            "description": "Port the agent listens on",
            "default": "8080"
        }
    ]
    
    # Parse manifest to get agent-specific requirements
    if agent.manifest_yaml:
        try:
            manifest = yaml.safe_load(agent.manifest_yaml)
            spec = manifest.get("spec", {})
            
            # Get inputs schema for required credentials
            inputs = spec.get("inputs", [])
            for inp in inputs:
                if inp.get("type") == "credential" or inp.get("secret"):
                    required_env_vars.append({
                        "key": inp.get("name", "").upper().replace("-", "_"),
                        "description": inp.get("description", "Required credential"),
                        "secret": True
                    })
        except Exception:
            pass
    
    # Adapter-specific environment variables
    adapter_env_vars = {
        "openai": [
            {
                "key": "OPENAI_API_KEY",
                "description": "OpenAI API key for GPT models",
                "required": True,
                "secret": True
            },
            {
                "key": "OPENAI_MODEL",
                "description": "Model to use (e.g., gpt-4, gpt-3.5-turbo)",
                "default": "gpt-4",
                "required": False
            }
        ],
        "anthropic": [
            {
                "key": "ANTHROPIC_API_KEY",
                "description": "Anthropic API key for Claude models",
                "required": True,
                "secret": True
            },
            {
                "key": "ANTHROPIC_MODEL",
                "description": "Model to use (e.g., claude-3-sonnet)",
                "default": "claude-3-sonnet-20240229",
                "required": False
            }
        ],
        "azure": [
            {
                "key": "AZURE_OPENAI_API_KEY",
                "description": "Azure OpenAI API key",
                "required": True,
                "secret": True
            },
            {
                "key": "AZURE_OPENAI_ENDPOINT",
                "description": "Azure OpenAI endpoint URL",
                "required": True
            },
            {
                "key": "AZURE_OPENAI_DEPLOYMENT",
                "description": "Azure deployment name",
                "required": True
            }
        ],
        "local": [
            {
                "key": "LOCAL_LLM_URL",
                "description": "Local LLM API URL (e.g., http://localhost:11434)",
                "default": "http://localhost:11434",
                "required": True
            },
            {
                "key": "LOCAL_LLM_MODEL",
                "description": "Model name (e.g., llama2, mistral)",
                "default": "llama2",
                "required": False
            }
        ]
    }
    
    # Get supported adapters from package
    supported_adapters = ["openai", "anthropic", "azure", "local"]
    
    return AgentEnvRequirements(
        agent_id=str(agent.id),
        agent_name=agent.name,
        required_env_vars=required_env_vars,
        optional_env_vars=optional_env_vars,
        supported_adapters=supported_adapters,
        adapter_env_vars=adapter_env_vars
    )


# ==========================================
# PLATFORM DISCOVERY ENDPOINTS
# ==========================================

@router.get("/platforms")
def list_deployment_platforms():
    """
    List all available deployment platforms and their requirements.
    
    Returns platform details including:
    - ID and display name
    - Description and icon
    - Whether prerequisites are met
    - Configuration schema for the frontend
    """
    from app.services.deployers import DeploymentFactory
    
    platforms = DeploymentFactory.list_platforms()
    return {
        "platforms": platforms,
        "default": "docker"
    }


@router.get("/platforms/{platform}/schema")
def get_platform_config_schema(platform: str):
    """
    Get the configuration schema for a specific platform.
    
    Used by the frontend to dynamically render platform-specific config forms.
    """
    from app.services.deployers import get_deployer
    
    try:
        deployer = get_deployer(platform)
        return {
            "platform": platform,
            "display_name": deployer.display_name,
            "schema": deployer.get_config_schema(),
            "available": deployer.check_prerequisites().valid
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/platforms/{platform}/validate")
def validate_platform_config(
    platform: str,
    platform_config: Dict[str, Any]
):
    """
    Validate platform-specific configuration before deployment.
    
    Checks connectivity and prerequisites for the target platform.
    """
    from app.services.deployers import get_deployer
    from app.services.deployers.base import DeployConfig
    
    try:
        deployer = get_deployer(platform)
        
        # Create a minimal config for validation
        config = DeployConfig(
            agent_id="validation-test",
            agent_name="Validation Test",
            version="1.0.0",
            adapter="openai",
            platform_config=platform_config
        )
        
        # Check prerequisites first
        prereqs = deployer.check_prerequisites()
        if not prereqs.valid:
            return {
                "valid": False,
                "errors": prereqs.errors,
                "warnings": prereqs.warnings,
                "requirements": prereqs.requirements_met
            }
        
        # Validate config
        result = deployer.validate_config(config)
        
        return {
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "requirements": result.requirements_met
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/kubeconfig")
def get_local_kubeconfig():
    """
    Get the local kubeconfig file from ~/.kube/config.
    
    This endpoint allows the frontend to auto-populate the kubeconfig field
    for Kubernetes deployments without requiring users to manually copy/paste
    the base64-encoded config.
    """
    import base64
    import subprocess
    from pathlib import Path
    
    # Try to get flattened kubeconfig (with embedded certs)
    try:
        result = subprocess.run(
            ["kubectl", "config", "view", "--flatten"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            kubeconfig_content = result.stdout
            kubeconfig_base64 = base64.b64encode(kubeconfig_content.encode()).decode()
            
            # Get current context info
            context_result = subprocess.run(
                ["kubectl", "config", "current-context"],
                capture_output=True,
                text=True,
                timeout=5
            )
            current_context = context_result.stdout.strip() if context_result.returncode == 0 else "unknown"
            
            return {
                "kubeconfig_base64": kubeconfig_base64,
                "current_context": current_context,
                "source": "kubectl config view --flatten"
            }
    except Exception as e:
        pass
    
    # Fallback: read from file directly
    kubeconfig_path = Path.home() / ".kube" / "config"
    
    if not kubeconfig_path.exists():
        raise HTTPException(
            status_code=404, 
            detail="No kubeconfig found. Please ensure kubectl is configured."
        )
    
    try:
        kubeconfig_content = kubeconfig_path.read_text()
        kubeconfig_base64 = base64.b64encode(kubeconfig_content.encode()).decode()
        
        return {
            "kubeconfig_base64": kubeconfig_base64,
            "source": str(kubeconfig_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read kubeconfig: {str(e)}")


# ==========================================
# UNIFIED DEPLOY ENDPOINT
# ==========================================

@router.post("/deploy")
def unified_deploy(
    request: UnifiedDeployRequest,
    user_id: str = Query(..., description="User ID"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
) -> UnifiedDeployResponse:
    """
    Unified one-click deployment.
    
    This endpoint handles the complete deployment flow:
    1. Validates license
    2. Creates deployment record
    3. Builds Docker image (if needed)
    4. Runs container with provided env vars
    5. Returns deployment status with URL
    """
    steps = []
    
    # Step 1: Validate Agent
    steps.append(DeploymentStep(
        step="validate_agent",
        status="running",
        message="Validating agent...",
        timestamp=datetime.utcnow().isoformat()
    ))
    
    agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
    if not agent:
        steps[-1].status = "failed"
        steps[-1].message = "Agent not found"
        return UnifiedDeployResponse(
            deployment_id="",
            status="failed",
            steps=steps,
            error="Agent not found"
        )
    
    steps[-1].status = "completed"
    steps[-1].message = f"Agent '{agent.name}' validated"
    
    # Step 2: Check/Create License
    steps.append(DeploymentStep(
        step="check_license",
        status="running",
        message="Checking license...",
        timestamp=datetime.utcnow().isoformat()
    ))
    
    license = db.query(License).filter(
        License.agent_id == request.agent_id,
        License.user_id == user_id,
        License.status == LicenseStatus.ACTIVE
    ).first()
    
    if not license:
        # Auto-create license for free agents or return error
        if agent.price_cents == 0:
            license = License(
                user_id=user_id,
                agent_id=request.agent_id,
                license_type="standard",
                status=LicenseStatus.ACTIVE
            )
            db.add(license)
            db.flush()
            steps[-1].message = "Free license activated"
        else:
            steps[-1].status = "failed"
            steps[-1].message = "Valid license required"
            return UnifiedDeployResponse(
                deployment_id="",
                status="failed",
                steps=steps,
                error="Please purchase a license first"
            )
    
    steps[-1].status = "completed"
    steps[-1].message = "License verified"
    
    # Step 3: Create Deployment Record
    steps.append(DeploymentStep(
        step="create_deployment",
        status="running",
        message="Creating deployment record...",
        timestamp=datetime.utcnow().isoformat()
    ))
    
    deployment = AgentDeployment(
        license_id=license.id,
        agent_id=request.agent_id,
        user_id=user_id,
        deployment_type=DeploymentType(request.deployment_type),
        adapter_used=request.adapter,
        deployment_config={
            "env_vars": request.env_vars,
            "port": request.port
        },
        environment_name=request.environment_name,
        status=DeploymentStatus.PENDING,
        deployed_at=datetime.utcnow()
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    deployment_id = str(deployment.id)
    steps[-1].status = "completed"
    steps[-1].message = f"Deployment record created"
    
    # Step 4: Check Docker Availability
    runtime = get_docker_runtime()
    
    steps.append(DeploymentStep(
        step="check_docker",
        status="running",
        message="Checking Docker availability...",
        timestamp=datetime.utcnow().isoformat()
    ))
    
    if not runtime.is_docker_available():
        steps[-1].status = "failed"
        steps[-1].message = "Docker is not available"
        deployment.status = DeploymentStatus.ERROR
        deployment.error_message = "Docker is not running or not installed"
        db.commit()
        return UnifiedDeployResponse(
            deployment_id=deployment_id,
            status="failed",
            steps=steps,
            error="Docker is not available. Please start Docker and try again."
        )
    
    steps[-1].status = "completed"
    steps[-1].message = "Docker is available"
    
    # Step 5: Build Docker Image
    steps.append(DeploymentStep(
        step="build_image",
        status="running",
        message="Building Docker image...",
        timestamp=datetime.utcnow().isoformat()
    ))
    
    # Check if image already exists
    image_name = f"postqode-agent-{request.agent_id}:{agent.version}"
    image_check = runtime._run_docker_cmd(["images", "-q", image_name], check=False)
    
    if not image_check.stdout.strip():
        # Need to build
        if not agent.package_url:
            steps[-1].status = "failed"
            steps[-1].message = "No package available to build"
            deployment.status = DeploymentStatus.ERROR
            deployment.error_message = "Agent package not found"
            db.commit()
            return UnifiedDeployResponse(
                deployment_id=deployment_id,
                status="failed",
                steps=steps,
                error="Agent package not available"
            )
        
        storage = get_package_storage()
        package_path = storage.get_package_path(request.agent_id, agent.version)
        
        if not package_path:
            steps[-1].status = "failed"
            steps[-1].message = "Package file not found"
            deployment.status = DeploymentStatus.ERROR
            deployment.error_message = "Package file not found"
            db.commit()
            return UnifiedDeployResponse(
                deployment_id=deployment_id,
                status="failed",
                steps=steps,
                error="Package file not found"
            )
        
        build_result = runtime.build_image_from_package(
            agent_id=request.agent_id,
            version=agent.version,
            package_path=package_path
        )
        
        if not build_result.get("success"):
            steps[-1].status = "failed"
            steps[-1].message = f"Build failed: {build_result.get('error', 'Unknown error')[:100]}"
            deployment.status = DeploymentStatus.ERROR
            deployment.error_message = build_result.get("error", "Build failed")
            db.commit()
            return UnifiedDeployResponse(
                deployment_id=deployment_id,
                status="failed",
                steps=steps,
                error=build_result.get("error", "Build failed")
            )
        
        steps[-1].message = f"Image built: {image_name}"
    else:
        steps[-1].message = f"Image already exists: {image_name}"
    
    steps[-1].status = "completed"
    
    # Step 6: Run Container
    if request.auto_start:
        steps.append(DeploymentStep(
            step="run_container",
            status="running",
            message="Starting container...",
            timestamp=datetime.utcnow().isoformat()
        ))
        
        # Prepare environment variables
        env_vars = dict(request.env_vars)
        env_vars["POSTQODE_ADAPTER"] = request.adapter
        env_vars["POSTQODE_DEPLOYMENT_ID"] = deployment_id
        env_vars["POSTQODE_AGENT_ID"] = request.agent_id
        
        run_result = runtime.run_container(
            deployment_id=deployment_id,
            agent_id=request.agent_id,
            version=agent.version,
            adapter=request.adapter,
            env_vars=env_vars,
            port=request.port
        )
        
        if not run_result.get("success"):
            steps[-1].status = "failed"
            steps[-1].message = f"Failed to start: {run_result.get('error', 'Unknown error')[:100]}"
            deployment.status = DeploymentStatus.ERROR
            deployment.error_message = run_result.get("error", "Failed to start container")
            db.commit()
            return UnifiedDeployResponse(
                deployment_id=deployment_id,
                status="failed",
                steps=steps,
                error=run_result.get("error", "Failed to start container")
            )
        
        # Update deployment status
        deployment.status = DeploymentStatus.ACTIVE
        deployment.error_message = None
        db.commit()
        
        container_url = f"http://localhost:{request.port}"
        steps[-1].status = "completed"
        steps[-1].message = f"Container running at {container_url}"
        
        return UnifiedDeployResponse(
            deployment_id=deployment_id,
            status="active",
            steps=steps,
            container_url=container_url
        )
    else:
        # Just built, not started
        deployment.status = DeploymentStatus.PENDING
        db.commit()
        
        return UnifiedDeployResponse(
            deployment_id=deployment_id,
            status="pending",
            steps=steps,
            container_url=None
        )


# ==========================================
# QUICK ACTIONS
# ==========================================

@router.post("/deploy/{deployment_id}/start")
def start_deployment(
    deployment_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Start/restart a deployment."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    agent = db.query(Agent).filter(Agent.id == deployment.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    runtime = get_docker_runtime()
    
    if not runtime.is_docker_available():
        raise HTTPException(status_code=503, detail="Docker is not available")
    
    # Get saved config
    config = deployment.deployment_config or {}
    env_vars = config.get("env_vars", {})
    port = config.get("port", 8080)
    
    result = runtime.run_container(
        deployment_id=deployment_id,
        agent_id=str(deployment.agent_id),
        version=agent.version,
        adapter=deployment.adapter_used or "openai",
        env_vars=env_vars,
        port=port
    )
    
    if not result.get("success"):
        deployment.status = DeploymentStatus.ERROR
        deployment.error_message = result.get("error")
        db.commit()
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    deployment.status = DeploymentStatus.ACTIVE
    deployment.deployed_at = datetime.utcnow()
    deployment.error_message = None
    db.commit()
    
    return {
        "message": "Container started",
        "container_url": f"http://localhost:{port}",
        "container_id": result.get("container_id")
    }


@router.post("/deploy/{deployment_id}/stop")
def stop_deployment(
    deployment_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Stop a running deployment."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    runtime = get_docker_runtime()
    result = runtime.stop_container(
        deployment_id=deployment_id,
        agent_id=str(deployment.agent_id)
    )
    
    deployment.status = DeploymentStatus.STOPPED
    deployment.stopped_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Container stopped", "deployment_id": deployment_id}


@router.post("/deploy/{deployment_id}/reconfigure")
def reconfigure_deployment(
    deployment_id: str,
    env_vars: Dict[str, str],
    user_id: str = Query(..., description="User ID"),
    restart: bool = Query(True, description="Restart after reconfiguration"),
    db: Session = Depends(get_db)
):
    """Update environment variables and optionally restart."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.id == deployment_id,
        AgentDeployment.user_id == user_id
    ).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Update config
    config = deployment.deployment_config or {}
    config["env_vars"] = env_vars
    deployment.deployment_config = config
    db.commit()
    
    if restart and deployment.status == DeploymentStatus.ACTIVE:
        # Stop current container
        runtime = get_docker_runtime()
        runtime.stop_container(deployment_id, str(deployment.agent_id))
        
        # Start with new config
        agent = db.query(Agent).filter(Agent.id == deployment.agent_id).first()
        port = config.get("port", 8080)
        
        result = runtime.run_container(
            deployment_id=deployment_id,
            agent_id=str(deployment.agent_id),
            version=agent.version,
            adapter=deployment.adapter_used or "openai",
            env_vars=env_vars,
            port=port
        )
        
        if not result.get("success"):
            deployment.status = DeploymentStatus.ERROR
            deployment.error_message = result.get("error")
            db.commit()
            raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {"message": "Configuration updated", "restarted": restart}
