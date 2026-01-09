"""
Agent Configuration.
Reads configuration from environment and manifest.
"""
import os
import yaml
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class AgentConfig:
    """
    Configuration for a PostQode Agent.
    Reads from environment variables and optional manifest file.
    """
    # Deployment info (from environment)
    deployment_id: str
    agent_id: str
    adapter: str
    
    # Marketplace connection
    marketplace_url: str
    api_key: Optional[str] = None
    
    # Runtime settings
    port: int = 8080
    health_interval: int = 30  # seconds between health pings
    
    # Custom config from manifest
    custom_config: Dict[str, Any] = None
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create config from environment variables."""
        return cls(
            deployment_id=os.environ.get("POSTQODE_DEPLOYMENT_ID", "local-dev"),
            agent_id=os.environ.get("POSTQODE_AGENT_ID", "unknown"),
            adapter=os.environ.get("POSTQODE_ADAPTER", "openai"),
            marketplace_url=os.environ.get("POSTQODE_MARKETPLACE_URL", "http://localhost:8000"),
            api_key=os.environ.get("POSTQODE_API_KEY"),
            port=int(os.environ.get("POSTQODE_AGENT_PORT", "8080")),
            health_interval=int(os.environ.get("POSTQODE_HEALTH_INTERVAL", "30")),
            custom_config={}
        )
    
    @classmethod
    def from_manifest(cls, manifest_path: str = "manifest.yaml") -> "AgentConfig":
        """Create config from manifest file + environment."""
        config = cls.from_env()
        
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
            
            if manifest:
                spec = manifest.get("spec", {})
                config.custom_config = spec.get("config", {})
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a custom config value."""
        if self.custom_config:
            return self.custom_config.get(key, default)
        return default
    
    def get_adapter_config(self) -> Dict[str, Any]:
        """Get adapter-specific configuration."""
        adapter_configs = {
            "openai": {
                "api_key_env": "OPENAI_API_KEY",
                "model": os.environ.get("OPENAI_MODEL", "gpt-4"),
                "base_url": os.environ.get("OPENAI_BASE_URL")
            },
            "anthropic": {
                "api_key_env": "ANTHROPIC_API_KEY",
                "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-sonnet"),
            },
            "azure": {
                "api_key_env": "AZURE_OPENAI_API_KEY",
                "endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT")
            },
            "local": {
                "model_path": os.environ.get("LOCAL_MODEL_PATH"),
            }
        }
        return adapter_configs.get(self.adapter, {})
