"""
Docker Deployer - Local container deployment.
Refactored from docker_runtime.py to use the deployer interface.
"""
import os
import subprocess
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .base import (
    BaseDeployer, DeployConfig, DeployResult, BuildResult, 
    ValidationResult, StatusResult, DeploymentPlatform
)

logger = logging.getLogger(__name__)


class DockerDeployer(BaseDeployer):
    """Deploy agents as Docker containers locally."""
    
    platform = DeploymentPlatform.DOCKER
    display_name = "Docker"
    description = "Run locally with Docker containers"
    icon = "box"
    
    def __init__(self, 
                 build_dir: str = "./storage/docker_builds",
                 marketplace_url: str = "http://host.docker.internal:8000"):
        self.build_dir = Path(build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.marketplace_url = marketplace_url
    
    def _run_docker_cmd(self, args: list, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run a docker command."""
        cmd = ["docker"] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            if check and result.returncode != 0:
                logger.error(f"Docker command failed: {result.stderr}")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Docker command timed out: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 1, "", "Command timed out")
        except Exception as e:
            logger.error(f"Docker command error: {e}")
            return subprocess.CompletedProcess(cmd, 1, "", str(e))
    
    def check_prerequisites(self) -> ValidationResult:
        """Check if Docker is available."""
        result = self._run_docker_cmd(["version"], check=False)
        if result.returncode == 0:
            return ValidationResult(
                valid=True,
                requirements_met={"docker": True}
            )
        return ValidationResult(
            valid=False,
            errors=["Docker is not installed or not running"],
            requirements_met={"docker": False}
        )
    
    def validate_config(self, config: DeployConfig) -> ValidationResult:
        """Validate Docker deployment config."""
        errors = []
        warnings = []
        
        prereqs = self.check_prerequisites()
        if not prereqs.valid:
            return prereqs
        
        if not config.agent_id:
            errors.append("agent_id is required")
        
        if config.port < 1 or config.port > 65535:
            errors.append(f"Invalid port: {config.port}")
        
        # Check if port is in use
        result = self._run_docker_cmd(
            ["ps", "--format", "{{.Ports}}"],
            check=False
        )
        if f":{config.port}->" in result.stdout:
            warnings.append(f"Port {config.port} may already be in use")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            requirements_met={"docker": True, "port_available": len(warnings) == 0}
        )
    
    def build(
        self, 
        config: DeployConfig, 
        package_path: Path,
        progress_callback: Optional[callable] = None
    ) -> BuildResult:
        """Build Docker image from agent package."""
        start_time = datetime.now()
        
        if progress_callback:
            progress_callback("Preparing build directory...")
        
        # Create build directory
        build_path = self.build_dir / config.agent_id / config.version
        build_path.mkdir(parents=True, exist_ok=True)
        
        # Extract package
        if progress_callback:
            progress_callback("Extracting package...")
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                zip_ref.extractall(build_path)
        except Exception as e:
            return BuildResult(
                success=False,
                error=f"Failed to extract package: {e}"
            )
        
        # Find Dockerfile
        dockerfile = build_path / "Dockerfile"
        if not dockerfile.exists():
            # Check subdirectory
            for child in build_path.iterdir():
                if child.is_dir() and (child / "Dockerfile").exists():
                    dockerfile = child / "Dockerfile"
                    build_path = child
                    break
        
        if not dockerfile.exists():
            return BuildResult(
                success=False,
                error="No Dockerfile found in package"
            )
        
        # Build image
        image_name = f"postqode-agent-{config.agent_id}"
        image_tag = f"{image_name}:{config.version}"
        
        if progress_callback:
            progress_callback(f"Building image {image_tag}...")
        
        result = self._run_docker_cmd(
            ["build", "-t", image_tag, str(build_path)],
            timeout=600
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.returncode != 0:
            return BuildResult(
                success=False,
                error=result.stderr[:500],
                build_logs=result.stdout + result.stderr,
                duration_seconds=duration
            )
        
        return BuildResult(
            success=True,
            image_name=image_name,
            image_tag=image_tag,
            artifact_path=build_path,
            build_logs=result.stdout,
            duration_seconds=duration
        )
    
    def deploy(
        self, 
        deployment_id: str,
        config: DeployConfig,
        build_result: BuildResult,
        progress_callback: Optional[callable] = None
    ) -> DeployResult:
        """Run Docker container."""
        start_time = datetime.now()
        
        if not build_result.success:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error="Cannot deploy without successful build"
            )
        
        # Stop any existing container
        container_name = f"postqode-{config.agent_id}-{deployment_id[:8]}"
        self._run_docker_cmd(["stop", container_name], check=False)
        self._run_docker_cmd(["rm", container_name], check=False)
        
        if progress_callback:
            progress_callback(f"Starting container {container_name}...")
        
        # Prepare environment variables
        env_args = []
        for key, value in config.env_vars.items():
            env_args.extend(["-e", f"{key}={value}"])
        
        # Add required PostQode env vars
        env_args.extend([
            "-e", f"POSTQODE_DEPLOYMENT_ID={deployment_id}",
            "-e", f"POSTQODE_AGENT_ID={config.agent_id}",
            "-e", f"POSTQODE_ADAPTER={config.adapter}",
            "-e", f"POSTQODE_MARKETPLACE_URL={self.marketplace_url}",
        ])
        
        # Run container
        run_cmd = [
            "run", "-d",
            "--name", container_name,
            "-p", f"{config.port}:8080",
            "--add-host", "host.docker.internal:host-gateway",
        ] + env_args + [build_result.image_tag]
        
        result = self._run_docker_cmd(run_cmd)
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.returncode != 0:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error=result.stderr,
                deploy_logs=result.stdout + result.stderr,
                duration_seconds=duration
            )
        
        container_id = result.stdout.strip()[:12]
        access_url = f"http://localhost:{config.port}"
        
        return DeployResult(
            success=True,
            deployment_id=deployment_id,
            external_id=container_id,
            access_url=access_url,
            endpoints={
                "web": access_url,
                "health": f"{access_url}/health",
                "invoke": f"{access_url}/invoke"
            },
            deploy_logs=result.stdout,
            duration_seconds=duration
        )
    
    def start(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Start a stopped container."""
        container_name = f"postqode-{config.agent_id}-{deployment_id[:8]}"
        result = self._run_docker_cmd(["start", container_name])
        
        if result.returncode == 0:
            return StatusResult(
                running=True,
                status="running",
                health="unknown",
                message="Container started"
            )
        return StatusResult(
            running=False,
            status="error",
            health="unknown",
            message=result.stderr
        )
    
    def stop(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Stop a running container."""
        container_name = f"postqode-{config.agent_id}-{deployment_id[:8]}"
        result = self._run_docker_cmd(["stop", container_name])
        
        if result.returncode == 0:
            return StatusResult(
                running=False,
                status="stopped",
                health="unknown",
                message="Container stopped"
            )
        return StatusResult(
            running=False,
            status="error",
            health="unknown",
            message=result.stderr
        )
    
    def restart(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Restart a container."""
        container_name = f"postqode-{config.agent_id}-{deployment_id[:8]}"
        result = self._run_docker_cmd(["restart", container_name])
        
        if result.returncode == 0:
            return StatusResult(
                running=True,
                status="running",
                health="unknown",
                message="Container restarted"
            )
        return StatusResult(
            running=False,
            status="error",
            health="unknown",
            message=result.stderr
        )
    
    def get_status(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Get container status."""
        container_name = f"postqode-{config.agent_id}-{deployment_id[:8]}"
        result = self._run_docker_cmd([
            "inspect", container_name,
            "--format", "{{.State.Status}}|{{.State.Health.Status}}|{{.State.StartedAt}}"
        ], check=False)
        
        if result.returncode != 0:
            return StatusResult(
                running=False,
                status="unknown",
                health="unknown",
                message="Container not found"
            )
        
        parts = result.stdout.strip().split("|")
        status = parts[0] if len(parts) > 0 else "unknown"
        health = parts[1] if len(parts) > 1 and parts[1] else "unknown"
        
        return StatusResult(
            running=(status == "running"),
            status=status,
            health=health,
            message=f"Container is {status}",
            last_updated=datetime.now()
        )
    
    def get_logs(
        self, 
        deployment_id: str, 
        config: DeployConfig,
        lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get container logs."""
        container_name = f"postqode-{config.agent_id}-{deployment_id[:8]}"
        args = ["logs", f"--tail={lines}"]
        if follow:
            args.append("-f")
        args.append(container_name)
        
        result = self._run_docker_cmd(args, check=False)
        return result.stdout + result.stderr
    
    def delete(self, deployment_id: str, config: DeployConfig) -> bool:
        """Delete container and optionally image."""
        container_name = f"postqode-{config.agent_id}-{deployment_id[:8]}"
        
        # Stop and remove container
        self._run_docker_cmd(["stop", container_name], check=False)
        result = self._run_docker_cmd(["rm", container_name], check=False)
        
        return result.returncode == 0
    
    def get_access_instructions(self, deployment_id: str, config: DeployConfig) -> Dict[str, str]:
        """Get Docker-specific access instructions."""
        container_name = f"postqode-{config.agent_id}-{deployment_id[:8]}"
        return {
            "url": f"http://localhost:{config.port}",
            "logs": f"docker logs {container_name}",
            "shell": f"docker exec -it {container_name} /bin/sh",
            "stop": f"docker stop {container_name}"
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for Docker config."""
        return {
            "type": "object",
            "properties": {
                "port": {
                    "type": "integer",
                    "default": 8080,
                    "description": "Host port to map to container",
                    "minimum": 1,
                    "maximum": 65535
                },
                "memory_limit": {
                    "type": "string",
                    "default": "2g",
                    "description": "Memory limit (e.g., 512m, 2g)"
                },
                "cpu_limit": {
                    "type": "number",
                    "default": 2,
                    "description": "CPU cores limit"
                }
            }
        }
