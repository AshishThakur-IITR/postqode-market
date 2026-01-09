"""
Local Docker Runtime Service.
Builds and runs agent containers locally.
"""
import subprocess
import os
import json
import tempfile
import zipfile
import shutil
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class ContainerInfo:
    """Information about a running container."""
    container_id: str
    container_name: str
    agent_id: str
    deployment_id: str
    status: str
    ports: Dict[str, str]
    created_at: datetime


class DockerRuntimeService:
    """
    Manages Docker containers for agent deployments.
    Builds images from packages and runs them locally.
    """
    
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = storage_path
        self.images_path = os.path.join(storage_path, "docker_images")
        self.build_path = os.path.join(storage_path, "docker_builds")
        os.makedirs(self.images_path, exist_ok=True)
        os.makedirs(self.build_path, exist_ok=True)
    
    def _run_docker_cmd(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a Docker command."""
        cmd = ["docker"] + args
        return subprocess.run(cmd, capture_output=True, text=True, check=check)
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = self._run_docker_cmd(["info"], check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def build_image_from_package(
        self, 
        agent_id: str, 
        version: str, 
        package_path: str,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Build a Docker image from an agent package.
        
        Args:
            agent_id: Unique agent identifier
            version: Agent version
            package_path: Path to the zip package
            tags: Additional image tags
            
        Returns:
            Build result with image info
        """
        if not os.path.exists(package_path):
            return {"success": False, "error": "Package not found"}
        
        # Create build directory
        build_id = str(uuid.uuid4())[:8]
        build_dir = os.path.join(self.build_path, f"{agent_id}-{build_id}")
        os.makedirs(build_dir, exist_ok=True)
        
        try:
            # Extract package
            with zipfile.ZipFile(package_path, 'r') as zf:
                zf.extractall(build_dir)
            
            # Check for Dockerfile
            dockerfile_path = os.path.join(build_dir, "Dockerfile")
            if not os.path.exists(dockerfile_path):
                # Create default Dockerfile
                self._create_default_dockerfile(build_dir)
            
            # Build image
            image_name = f"postqode-agent-{agent_id}:{version}"
            result = self._run_docker_cmd([
                "build",
                "-t", image_name,
                "-f", dockerfile_path,
                build_dir
            ], check=False)
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr,
                    "stdout": result.stdout
                }
            
            # Add additional tags
            if tags:
                for tag in tags:
                    self._run_docker_cmd(["tag", image_name, tag], check=False)
            
            return {
                "success": True,
                "image_name": image_name,
                "build_id": build_id,
                "build_output": result.stdout
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            # Cleanup build directory
            shutil.rmtree(build_dir, ignore_errors=True)
    
    def _create_default_dockerfile(self, build_dir: str):
        """Create a default Dockerfile for Python agents."""
        dockerfile_content = """
# PostQode Agent Default Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Install PostQode SDK
RUN pip install --no-cache-dir httpx pyyaml

# Copy agent code
COPY . .

# Set environment variables
ENV POSTQODE_MARKETPLACE_URL=http://host.docker.internal:8000
ENV POSTQODE_AGENT_PORT=8080

# Expose port
EXPOSE 8080

# Run agent
CMD ["python", "agent.py"]
"""
        with open(os.path.join(build_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)
    
    def run_container(
        self,
        deployment_id: str,
        agent_id: str,
        version: str,
        adapter: str = "openai",
        env_vars: Optional[Dict[str, str]] = None,
        port: int = 8080
    ) -> Dict:
        """
        Run an agent container.
        
        Args:
            deployment_id: Deployment ID for tracking
            agent_id: Agent ID
            version: Agent version
            adapter: Runtime adapter (openai, anthropic, etc.)
            env_vars: Additional environment variables
            port: Host port to expose
            
        Returns:
            Container info or error
        """
        image_name = f"postqode-agent-{agent_id}:{version}"
        container_name = f"postqode-{agent_id}-{deployment_id[:8]}"
        
        # Check if image exists
        result = self._run_docker_cmd(["images", "-q", image_name], check=False)
        if not result.stdout.strip():
            return {"success": False, "error": f"Image {image_name} not found. Build it first."}
        
        # Check if container already running
        result = self._run_docker_cmd(["ps", "-q", "-f", f"name={container_name}"], check=False)
        if result.stdout.strip():
            return {"success": False, "error": f"Container {container_name} already running"}
        
        # Build run command
        run_args = [
            "run", "-d",
            "--name", container_name,
            "-p", f"{port}:8080",
            "-e", f"POSTQODE_DEPLOYMENT_ID={deployment_id}",
            "-e", f"POSTQODE_AGENT_ID={agent_id}",
            "-e", f"POSTQODE_ADAPTER={adapter}",
            "-e", "POSTQODE_MARKETPLACE_URL=http://host.docker.internal:8000",
            "--add-host", "host.docker.internal:host-gateway"
        ]
        
        # Add custom env vars
        if env_vars:
            for key, value in env_vars.items():
                run_args.extend(["-e", f"{key}={value}"])
        
        run_args.append(image_name)
        
        result = self._run_docker_cmd(run_args, check=False)
        
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        
        container_id = result.stdout.strip()[:12]
        
        return {
            "success": True,
            "container_id": container_id,
            "container_name": container_name,
            "port": port,
            "image": image_name,
            "message": f"Container started. Access at http://localhost:{port}"
        }
    
    def stop_container(self, deployment_id: str, agent_id: str) -> Dict:
        """Stop a running container."""
        container_name = f"postqode-{agent_id}-{deployment_id[:8]}"
        
        result = self._run_docker_cmd(["stop", container_name], check=False)
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        
        # Remove container
        self._run_docker_cmd(["rm", container_name], check=False)
        
        return {"success": True, "message": f"Container {container_name} stopped and removed"}
    
    def get_container_status(self, deployment_id: str, agent_id: str) -> Dict:
        """Get status of a container."""
        container_name = f"postqode-{agent_id}-{deployment_id[:8]}"
        
        result = self._run_docker_cmd([
            "inspect", container_name,
            "--format", "{{.State.Status}}"
        ], check=False)
        
        if result.returncode != 0:
            return {"status": "not_found", "running": False}
        
        status = result.stdout.strip()
        return {
            "status": status,
            "running": status == "running",
            "container_name": container_name
        }
    
    def get_container_logs(self, deployment_id: str, agent_id: str, tail: int = 100) -> Dict:
        """Get container logs."""
        container_name = f"postqode-{agent_id}-{deployment_id[:8]}"
        
        result = self._run_docker_cmd([
            "logs", container_name, "--tail", str(tail)
        ], check=False)
        
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        
        return {
            "success": True,
            "logs": result.stdout,
            "stderr": result.stderr
        }
    
    def list_running_containers(self) -> List[Dict]:
        """List all running PostQode agent containers."""
        result = self._run_docker_cmd([
            "ps", "-a",
            "--filter", "name=postqode-",
            "--format", "{{json .}}"
        ], check=False)
        
        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    container = json.loads(line)
                    containers.append({
                        "id": container.get("ID"),
                        "name": container.get("Names"),
                        "image": container.get("Image"),
                        "status": container.get("Status"),
                        "ports": container.get("Ports"),
                        "created": container.get("CreatedAt")
                    })
                except json.JSONDecodeError:
                    pass
        
        return containers


# Singleton instance
_docker_runtime: Optional[DockerRuntimeService] = None


def get_docker_runtime() -> DockerRuntimeService:
    """Get the Docker runtime service singleton."""
    global _docker_runtime
    if _docker_runtime is None:
        _docker_runtime = DockerRuntimeService()
    return _docker_runtime
