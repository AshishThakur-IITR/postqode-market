"""
Deployment Factory - Get the appropriate deployer for a platform.
"""
from typing import Dict, Optional, List, Any
from .base import BaseDeployer, DeploymentPlatform
from .docker_deployer import DockerDeployer
from .kubernetes_deployer import KubernetesDeployer
from .azure_deployer import AzureFunctionsDeployer
from .vm_deployer import VMDeployer
from .edge_deployer import EdgeDeployer


class DeploymentFactory:
    """
    Factory for creating deployers based on platform type.
    
    Usage:
        deployer = DeploymentFactory.get_deployer("kubernetes")
        result = deployer.deploy(...)
    """
    
    _deployers: Dict[str, BaseDeployer] = {}
    _initialized: bool = False
    
    @classmethod
    def _initialize(cls):
        """Initialize all deployers."""
        if cls._initialized:
            return
        
        cls._deployers = {
            "docker": DockerDeployer(),
            "kubernetes": KubernetesDeployer(),
            "azure_functions": AzureFunctionsDeployer(),
            "serverless": AzureFunctionsDeployer(),  # alias
            "vm_standalone": VMDeployer(),
            "vm": VMDeployer(),  # alias
            "bare_metal": VMDeployer(),  # alias
            "edge": EdgeDeployer(),
            "iot": EdgeDeployer(),  # alias
        }
        
        cls._initialized = True
    
    @classmethod
    def get_deployer(cls, platform: str) -> BaseDeployer:
        """
        Get a deployer for the specified platform.
        
        Args:
            platform: Platform identifier (docker, kubernetes, azure_functions, etc.)
            
        Returns:
            BaseDeployer instance
            
        Raises:
            ValueError if platform is not supported
        """
        cls._initialize()
        
        platform_lower = platform.lower().replace("-", "_")
        
        if platform_lower not in cls._deployers:
            raise ValueError(f"Unsupported platform: {platform}. Supported: {list(cls._deployers.keys())}")
        
        return cls._deployers[platform_lower]
    
    @classmethod
    def list_platforms(cls) -> List[Dict[str, Any]]:
        """
        List all available deployment platforms with their details.
        
        Returns:
            List of platform info dicts
        """
        cls._initialize()
        
        # Get unique deployers (avoiding aliases)
        seen = set()
        platforms = []
        
        for key, deployer in cls._deployers.items():
            platform_id = deployer.platform.value
            if platform_id in seen:
                continue
            seen.add(platform_id)
            
            prereqs = deployer.check_prerequisites()
            
            platforms.append({
                "id": platform_id,
                "name": deployer.display_name,
                "description": deployer.description,
                "icon": deployer.icon,
                "available": prereqs.valid,
                "requirements": prereqs.requirements_met,
                "config_schema": deployer.get_config_schema()
            })
        
        return platforms
    
    @classmethod
    def check_platform_available(cls, platform: str) -> bool:
        """Check if a platform is available for use."""
        try:
            deployer = cls.get_deployer(platform)
            prereqs = deployer.check_prerequisites()
            return prereqs.valid
        except ValueError:
            return False
    
    @classmethod
    def get_platform_schema(cls, platform: str) -> Dict[str, Any]:
        """Get the configuration schema for a platform."""
        deployer = cls.get_deployer(platform)
        return deployer.get_config_schema()


# Convenience function
def get_deployer(platform: str) -> BaseDeployer:
    """Get a deployer for the specified platform."""
    return DeploymentFactory.get_deployer(platform)


def list_available_platforms() -> List[Dict[str, Any]]:
    """List all available deployment platforms."""
    return DeploymentFactory.list_platforms()
