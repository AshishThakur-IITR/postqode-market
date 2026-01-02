"""
Pydantic schemas for Agent Manifest validation.
Based on the agent.yaml specification.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class PricingModel(str, Enum):
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one_time"
    USAGE_BASED = "usage_based"
    FREE = "free"


class PricingTier(BaseModel):
    name: str
    priceUSD: float
    limits: Optional[Dict[str, Any]] = {}


class Pricing(BaseModel):
    model: PricingModel = PricingModel.SUBSCRIPTION
    tiers: List[PricingTier] = []


class Capability(BaseModel):
    name: str
    description: Optional[str] = None


class InputType(str, Enum):
    FILE = "file"
    API = "api"
    DATABASE = "database"
    STRING = "string"
    JSON = "json"


class InputDef(BaseModel):
    name: str
    type: str  # Can be combination like "file | api | database"
    required: bool = True
    description: Optional[str] = None
    default: Optional[Any] = None


class OutputDef(BaseModel):
    name: str
    type: str  # "json", "pdf", "file", etc.
    description: Optional[str] = None


class RuntimeRequirements(BaseModel):
    minVersion: Optional[str] = "1.0.0"
    supportedRuntimes: List[str] = ["postqode-runtime"]
    resources: Optional[Dict[str, Any]] = {}


class ManifestMetadata(BaseModel):
    name: str = Field(..., description="Agent package name (slug)")
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    publisher: Optional[str] = None
    publishedAt: Optional[str] = None


class ManifestSpec(BaseModel):
    displayName: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="Agent description")
    category: Optional[str] = "Other"
    tags: List[str] = []
    
    pricing: Optional[Pricing] = None
    capabilities: List[Capability] = []
    inputs: List[InputDef] = []
    outputs: List[OutputDef] = []
    runtime: Optional[RuntimeRequirements] = None


class AgentManifest(BaseModel):
    """
    Schema for agent.yaml manifest file.
    """
    apiVersion: str = Field(default="postqode.ai/v1", description="API version")
    kind: str = Field(default="Agent", description="Resource type")
    metadata: ManifestMetadata
    spec: ManifestSpec
    
    class Config:
        extra = "allow"  # Allow additional fields


# ========================================
# Adapter Schemas
# ========================================

class AdapterAPIConfig(BaseModel):
    baseUrl: str
    authType: str = "bearer"  # bearer, api-key, x-api-key, none
    secretRef: Optional[str] = None  # Name of secrets to use
    apiVersion: Optional[str] = None
    extraHeaders: Optional[Dict[str, str]] = {}


class AdapterModelConfig(BaseModel):
    default: str
    fallback: Optional[str] = None
    embedding: Optional[str] = None


class AdapterRequestMapping(BaseModel):
    systemPrompt: Optional[str] = None
    maxTokens: Optional[int] = 4096
    temperature: Optional[float] = 0.7


class AdapterErrorHandling(BaseModel):
    retryOn: List[int] = [429, 500, 502, 503]
    maxRetries: int = 3
    backoffMultiplier: float = 2.0


class RuntimeAdapterSpec(BaseModel):
    provider: str  # openai, anthropic, azure-openai, ollama, custom
    models: AdapterModelConfig
    api: AdapterAPIConfig
    requestMapping: Optional[AdapterRequestMapping] = None
    errorHandling: Optional[AdapterErrorHandling] = None


class RuntimeAdapter(BaseModel):
    """
    Schema for runtime adapter YAML files.
    """
    apiVersion: str = "postqode.ai/v1"
    kind: str = "RuntimeAdapter"
    metadata: Dict[str, str]
    spec: RuntimeAdapterSpec


# ========================================
# Permissions Schemas
# ========================================

class DataAccessPermission(BaseModel):
    resource: str  # files, databases, apis
    operations: List[str]  # read, write, invoke
    scope: Optional[str] = None


class NetworkPermission(BaseModel):
    domain: str
    purpose: Optional[str] = None


class SecretPermission(BaseModel):
    name: str
    required: bool = True
    description: Optional[str] = None


class PermissionsSpec(BaseModel):
    dataAccess: List[DataAccessPermission] = []
    network: Optional[Dict[str, List[NetworkPermission]]] = None
    secrets: List[SecretPermission] = []


class Permissions(BaseModel):
    """
    Schema for policies/permissions.yaml
    """
    apiVersion: str = "postqode.ai/v1"
    kind: str = "Permissions"
    dataAccess: List[DataAccessPermission] = []
    network: Optional[Dict[str, Any]] = None
    secrets: List[SecretPermission] = []
