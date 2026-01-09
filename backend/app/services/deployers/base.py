"""
Base Deployer Interface and Common Types.
All platform-specific deployers inherit from this base class.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum
from datetime import datetime


class DeploymentPlatform(str, Enum):
    """Supported deployment platforms."""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    AZURE_FUNCTIONS = "azure_functions"
    VM_STANDALONE = "vm_standalone"
    EDGE = "edge"
    CLOUD_MANAGED = "cloud_managed"


@dataclass
class DeployConfig:
    """Configuration for a deployment."""
    agent_id: str
    agent_name: str
    version: str
    adapter: str
    env_vars: Dict[str, str] = field(default_factory=dict)
    platform_config: Dict[str, Any] = field(default_factory=dict)
    port: int = 8080
    environment_name: str = "production"
    
    # Platform-specific configs are flattened from platform_config
    @property
    def kubeconfig(self) -> Optional[str]:
        return self.platform_config.get("kubeconfig")
    
    @property
    def namespace(self) -> str:
        return self.platform_config.get("namespace", "default")
    
    @property
    def replicas(self) -> int:
        return self.platform_config.get("replicas", 1)
    
    @property
    def registry(self) -> Optional[str]:
        return self.platform_config.get("registry")
    
    @property
    def ssh_host(self) -> Optional[str]:
        return self.platform_config.get("ssh_host")
    
    @property
    def ssh_user(self) -> str:
        return self.platform_config.get("ssh_user", "root")
    
    @property
    def ssh_key(self) -> Optional[str]:
        return self.platform_config.get("ssh_key")
    
    @property
    def device_id(self) -> Optional[str]:
        return self.platform_config.get("device_id")


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    requirements_met: Dict[str, bool] = field(default_factory=dict)


@dataclass  
class BuildResult:
    """Result of the build phase."""
    success: bool
    image_name: Optional[str] = None
    image_tag: Optional[str] = None
    artifact_path: Optional[Path] = None
    build_logs: str = ""
    error: Optional[str] = None
    duration_seconds: float = 0


@dataclass
class DeployResult:
    """Result of the deployment phase."""
    success: bool
    deployment_id: str
    external_id: Optional[str] = None  # K8s release name, Azure function name, etc.
    access_url: Optional[str] = None
    endpoints: Dict[str, str] = field(default_factory=dict)
    deploy_logs: str = ""
    error: Optional[str] = None
    duration_seconds: float = 0


@dataclass
class StatusResult:
    """Status of a deployment."""
    running: bool
    status: str  # running, stopped, error, pending, unknown
    health: str  # healthy, unhealthy, unknown
    message: str = ""
    uptime_seconds: int = 0
    last_updated: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class BaseDeployer(ABC):
    """
    Abstract base class for all deployment platforms.
    
    Each platform (Docker, Kubernetes, Azure, VM, Edge) implements
    this interface to provide consistent deployment behavior.
    """
    
    platform: DeploymentPlatform
    display_name: str
    description: str
    icon: str  # Lucide icon name
    
    @abstractmethod
    def validate_config(self, config: DeployConfig) -> ValidationResult:
        """
        Validate the deployment configuration.
        
        Checks that all required settings are present and valid.
        Returns errors and warnings.
        """
        pass
    
    @abstractmethod
    def check_prerequisites(self) -> ValidationResult:
        """
        Check that all prerequisites are met.
        
        For example:
        - Docker: Docker daemon running
        - Kubernetes: kubectl/helm installed, cluster reachable
        - Azure: Azure CLI authenticated
        - VM: SSH connectivity
        """
        pass
    
    @abstractmethod
    def build(
        self, 
        config: DeployConfig, 
        package_path: Path,
        progress_callback: Optional[callable] = None
    ) -> BuildResult:
        """
        Build the deployment artifact.
        
        For Docker/K8s: Build container image
        For Azure: Package function
        For VM: Package application
        For Edge: Create edge bundle
        """
        pass
    
    @abstractmethod
    def deploy(
        self, 
        deployment_id: str,
        config: DeployConfig,
        build_result: BuildResult,
        progress_callback: Optional[callable] = None
    ) -> DeployResult:
        """
        Deploy the built artifact to the target platform.
        
        Returns access URL and other deployment info.
        """
        pass
    
    @abstractmethod
    def start(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Start a stopped deployment."""
        pass
    
    @abstractmethod
    def stop(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Stop a running deployment."""
        pass
    
    @abstractmethod
    def restart(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Restart a deployment."""
        pass
    
    @abstractmethod
    def get_status(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Get current status of a deployment."""
        pass
    
    @abstractmethod
    def get_logs(
        self, 
        deployment_id: str, 
        config: DeployConfig,
        lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get logs from the deployment."""
        pass
    
    @abstractmethod
    def delete(self, deployment_id: str, config: DeployConfig) -> bool:
        """Delete/cleanup a deployment."""
        pass
    
    def get_access_instructions(self, deployment_id: str, config: DeployConfig) -> Dict[str, str]:
        """
        Get platform-specific access instructions.
        
        Returns a dict with instruction keys and values:
        {
            "url": "http://...",
            "cli": "command to access",
            "note": "additional notes"
        }
        """
        return {}
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for platform-specific configuration.
        
        Used by frontend to render configuration form.
        """
        return {}
