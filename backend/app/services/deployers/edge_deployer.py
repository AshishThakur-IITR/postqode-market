"""
Edge Deployer - Deploy agents to IoT/Edge devices.
"""
import os
import json
import logging
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import (
    BaseDeployer, DeployConfig, DeployResult, BuildResult, 
    ValidationResult, StatusResult, DeploymentPlatform
)

logger = logging.getLogger(__name__)


class EdgeDeployer(BaseDeployer):
    """Deploy agents to IoT/Edge devices via Edge Runtime."""
    
    platform = DeploymentPlatform.EDGE
    display_name = "Edge Device"
    description = "Deploy to IoT and edge devices"
    icon = "cpu"
    
    def __init__(self, 
                 edge_registry_url: str = "http://localhost:8001",
                 build_dir: str = "./storage/edge_builds"):
        self.edge_registry_url = edge_registry_url
        self.build_dir = Path(build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)
    
    def check_prerequisites(self) -> ValidationResult:
        """Check if Edge Registry is reachable."""
        try:
            response = httpx.get(f"{self.edge_registry_url}/health", timeout=5)
            if response.status_code == 200:
                return ValidationResult(
                    valid=True,
                    requirements_met={"edge_registry": True}
                )
        except:
            pass
        
        return ValidationResult(
            valid=False,
            errors=["Edge Registry is not reachable"],
            warnings=["Edge deployment requires PostQode Edge Runtime installed on target devices"],
            requirements_met={"edge_registry": False}
        )
    
    def validate_config(self, config: DeployConfig) -> ValidationResult:
        """Validate Edge deployment config."""
        errors = []
        warnings = []
        
        if not config.device_id and not config.platform_config.get("device_group"):
            errors.append("Either device_id or device_group is required")
        
        # Check device enrollment
        device_id = config.device_id
        if device_id:
            try:
                response = httpx.get(
                    f"{self.edge_registry_url}/devices/{device_id}",
                    timeout=10
                )
                if response.status_code != 200:
                    errors.append(f"Device {device_id} not found in registry")
                else:
                    device = response.json()
                    if device.get("status") != "online":
                        warnings.append(f"Device {device_id} is currently offline")
            except Exception as e:
                warnings.append(f"Could not verify device: {e}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            requirements_met={"device_enrolled": len(errors) == 0}
        )
    
    def build(
        self, 
        config: DeployConfig, 
        package_path: Path,
        progress_callback: Optional[callable] = None
    ) -> BuildResult:
        """Build edge-optimized agent package."""
        start_time = datetime.now()
        
        if progress_callback:
            progress_callback("Creating edge-optimized package...")
        
        build_path = self.build_dir / config.agent_id / config.version
        build_path.mkdir(parents=True, exist_ok=True)
        
        # For edge, we create a manifest that the edge runtime understands
        edge_manifest = {
            "apiVersion": "edge.postqode.io/v1",
            "kind": "EdgeAgent",
            "metadata": {
                "name": config.agent_name,
                "version": config.version,
                "agent_id": config.agent_id
            },
            "spec": {
                "adapter": config.adapter,
                "env": config.env_vars,
                "resources": {
                    "memory_mb": config.platform_config.get("memory_mb", 256),
                    "cpu_percent": config.platform_config.get("cpu_percent", 50)
                },
                "offline_capable": config.platform_config.get("offline_capable", False),
                "sync_interval": config.platform_config.get("sync_interval", 60)
            }
        }
        
        (build_path / "edge-manifest.json").write_text(json.dumps(edge_manifest, indent=2))
        
        # Copy original package
        import shutil
        shutil.copy(package_path, build_path / "agent.zip")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return BuildResult(
            success=True,
            artifact_path=build_path,
            duration_seconds=duration
        )
    
    def deploy(
        self, 
        deployment_id: str,
        config: DeployConfig,
        build_result: BuildResult,
        progress_callback: Optional[callable] = None
    ) -> DeployResult:
        """Deploy to edge device via registry."""
        start_time = datetime.now()
        
        if not build_result.success or not build_result.artifact_path:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error="Cannot deploy without successful build"
            )
        
        if progress_callback:
            progress_callback("Uploading to Edge Registry...")
        
        # Upload package to edge registry
        try:
            with open(build_result.artifact_path / "agent.zip", "rb") as f:
                files = {"package": f}
                manifest = json.loads((build_result.artifact_path / "edge-manifest.json").read_text())
                
                response = httpx.post(
                    f"{self.edge_registry_url}/packages",
                    files=files,
                    data={"manifest": json.dumps(manifest)},
                    timeout=60
                )
                
                if response.status_code != 200:
                    return DeployResult(
                        success=False,
                        deployment_id=deployment_id,
                        error=f"Failed to upload to registry: {response.text}",
                        duration_seconds=(datetime.now() - start_time).total_seconds()
                    )
                
                package_id = response.json().get("package_id")
        except Exception as e:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error=f"Failed to upload to registry: {e}",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        if progress_callback:
            progress_callback("Deploying to device(s)...")
        
        # Create deployment command
        device_id = config.device_id
        device_group = config.platform_config.get("device_group")
        
        deploy_request = {
            "deployment_id": deployment_id,
            "package_id": package_id,
            "agent_id": config.agent_id,
            "config": {
                "adapter": config.adapter,
                "env_vars": config.env_vars,
                "port": config.port
            }
        }
        
        if device_id:
            deploy_request["device_id"] = device_id
        if device_group:
            deploy_request["device_group"] = device_group
        
        try:
            response = httpx.post(
                f"{self.edge_registry_url}/deployments",
                json=deploy_request,
                timeout=30
            )
            
            if response.status_code != 200:
                return DeployResult(
                    success=False,
                    deployment_id=deployment_id,
                    error=f"Deployment command failed: {response.text}",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            result = response.json()
            duration = (datetime.now() - start_time).total_seconds()
            
            return DeployResult(
                success=True,
                deployment_id=deployment_id,
                external_id=result.get("edge_deployment_id"),
                access_url=result.get("local_url"),  # Local device URL
                endpoints={
                    "device": result.get("device_endpoint", ""),
                    "registry": f"{self.edge_registry_url}/deployments/{deployment_id}"
                },
                deploy_logs=json.dumps(result, indent=2),
                duration_seconds=duration
            )
        except Exception as e:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def start(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Start agent on device."""
        try:
            response = httpx.post(
                f"{self.edge_registry_url}/deployments/{deployment_id}/start",
                timeout=30
            )
            if response.status_code == 200:
                return StatusResult(running=True, status="running", health="unknown", message="Agent started")
        except:
            pass
        return StatusResult(running=False, status="error", health="unknown", message="Failed to start")
    
    def stop(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Stop agent on device."""
        try:
            response = httpx.post(
                f"{self.edge_registry_url}/deployments/{deployment_id}/stop",
                timeout=30
            )
            if response.status_code == 200:
                return StatusResult(running=False, status="stopped", health="unknown", message="Agent stopped")
        except:
            pass
        return StatusResult(running=False, status="error", health="unknown", message="Failed to stop")
    
    def restart(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Restart agent on device."""
        self.stop(deployment_id, config)
        return self.start(deployment_id, config)
    
    def get_status(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Get device deployment status."""
        try:
            response = httpx.get(
                f"{self.edge_registry_url}/deployments/{deployment_id}/status",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return StatusResult(
                    running=data.get("running", False),
                    status=data.get("status", "unknown"),
                    health=data.get("health", "unknown"),
                    message=data.get("message", ""),
                    uptime_seconds=data.get("uptime_seconds", 0),
                    last_updated=datetime.now()
                )
        except:
            pass
        
        return StatusResult(
            running=False,
            status="unknown",
            health="unknown",
            message="Could not reach device"
        )
    
    def get_logs(
        self, 
        deployment_id: str, 
        config: DeployConfig,
        lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get device logs via registry."""
        try:
            response = httpx.get(
                f"{self.edge_registry_url}/deployments/{deployment_id}/logs",
                params={"lines": lines},
                timeout=30
            )
            if response.status_code == 200:
                return response.text
        except:
            pass
        return "Could not retrieve logs from device"
    
    def delete(self, deployment_id: str, config: DeployConfig) -> bool:
        """Remove deployment from device."""
        try:
            response = httpx.delete(
                f"{self.edge_registry_url}/deployments/{deployment_id}",
                timeout=30
            )
            return response.status_code == 200
        except:
            return False
    
    def get_access_instructions(self, deployment_id: str, config: DeployConfig) -> Dict[str, str]:
        """Get Edge-specific access instructions."""
        return {
            "registry": f"{self.edge_registry_url}/deployments/{deployment_id}",
            "device_url": f"http://{config.device_id}.local:{config.port}",
            "note": "Access depends on network connectivity to the edge device"
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for Edge config."""
        return {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "Target device ID (enrolled in Edge Registry)"
                },
                "device_group": {
                    "type": "string",
                    "description": "Deploy to all devices in this group"
                },
                "offline_capable": {
                    "type": "boolean",
                    "default": False,
                    "description": "Can agent work offline?"
                },
                "sync_interval": {
                    "type": "integer",
                    "default": 60,
                    "description": "Seconds between health syncs"
                },
                "memory_mb": {
                    "type": "integer",
                    "default": 256,
                    "description": "Memory limit in MB"
                },
                "cpu_percent": {
                    "type": "integer",
                    "default": 50,
                    "description": "CPU limit percentage"
                }
            },
            "required": []
        }
    
    # Additional edge-specific methods
    
    def list_devices(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        """List enrolled edge devices."""
        try:
            params = {"group": group} if group else {}
            response = httpx.get(
                f"{self.edge_registry_url}/devices",
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("devices", [])
        except:
            pass
        return []
    
    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific device."""
        try:
            response = httpx.get(
                f"{self.edge_registry_url}/devices/{device_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
