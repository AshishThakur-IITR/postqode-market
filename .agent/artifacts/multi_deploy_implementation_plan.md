# Multi-Platform Deployment Implementation Plan

## Overview

Extend the PostQode Marketplace one-click deployment to support multiple platforms beyond Docker:

| Deployment Type | Target Platform | Status |
|----------------|-----------------|--------|
| Docker | Local containers | ✅ Implemented |
| Kubernetes | Helm Charts on K8s | 🔄 To implement |
| Serverless | Azure Functions | 🔄 To implement |
| VM/Bare Metal | Standalone servers | 🔄 To implement |
| Edge Device | IoT/Edge devices | 🔄 To implement |

---

## Architecture Design

### Backend Services Structure

```
backend/app/services/
├── docker_runtime.py          # ✅ Existing Docker runtime
├── deployers/                  # New deployer services
│   ├── __init__.py
│   ├── base.py                 # Base deployer interface
│   ├── docker_deployer.py      # Docker deployment (refactored)
│   ├── kubernetes_deployer.py  # Helm/K8s deployment
│   ├── azure_functions_deployer.py  # Azure Functions
│   ├── vm_deployer.py          # VM/Bare metal via SSH
│   └── edge_deployer.py        # Edge device deployment
└── deployment_factory.py       # Factory to get deployer by type
```

### Deployer Interface

```python
class BaseDeployer(ABC):
    @abstractmethod
    def validate_config(self, config: DeployConfig) -> ValidationResult
    
    @abstractmethod
    def build(self, agent_id: str, version: str, package_path: Path) -> BuildResult
    
    @abstractmethod
    def deploy(self, deployment_id: str, build_result: BuildResult, config: DeployConfig) -> DeployResult
    
    @abstractmethod
    def start(self, deployment_id: str) -> StatusResult
    
    @abstractmethod
    def stop(self, deployment_id: str) -> StatusResult
    
    @abstractmethod
    def get_status(self, deployment_id: str) -> StatusResult
    
    @abstractmethod
    def get_logs(self, deployment_id: str, lines: int = 100) -> str
    
    @abstractmethod
    def get_access_url(self, deployment_id: str) -> Optional[str]
```

---

## Implementation Details

### 1. Kubernetes/Helm Deployment

**Requirements:**
- Helm CLI installed
- kubeconfig for target cluster
- Container registry access

**Flow:**
1. Build Docker image (reuse existing)
2. Push to container registry (Docker Hub, ACR, ECR, GCR)
3. Generate Helm values.yaml
4. Install/upgrade Helm release
5. Create Ingress/Service for access

**Configuration:**
```yaml
kubeconfig: base64_encoded_kubeconfig
namespace: default
registry: docker.io/postqode
ingress_enabled: true
ingress_host: agent-123.postqode.cloud
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2"
```

### 2. Azure Functions Deployment

**Requirements:**
- Azure subscription
- Azure CLI or SDK
- Function App created

**Flow:**
1. Generate Azure Function project from agent
2. Package as deployment zip
3. Deploy to Azure Function App
4. Configure environment variables
5. Return function URL

**Configuration:**
```yaml
azure_subscription_id: "xxx"
resource_group: "postqode-agents"
function_app_name: "agent-reconciliation"
runtime: "python"
storage_account: "postqodestorage"
```

### 3. VM/Bare Metal Deployment

**Requirements:**
- SSH access to target server
- Python 3.11+ on target
- Systemd or supervisor for process management

**Flow:**
1. SSH to target server
2. Create deployment directory
3. Transfer agent package via SCP
4. Install dependencies
5. Create systemd service
6. Start service
7. Configure reverse proxy (optional)

**Configuration:**
```yaml
host: "192.168.1.100"
ssh_port: 22
ssh_key: base64_encoded_private_key
username: "deploy"
install_path: "/opt/postqode/agents"
use_systemd: true
reverse_proxy: nginx  # or none
```

### 4. Edge Device Deployment

**Requirements:**
- Device enrolled in PostQode Edge Fleet
- PostQode Edge Runtime installed
- Network connectivity

**Flow:**
1. Package agent for edge (minimal dependencies)
2. Push to edge registry/CDN
3. Send deployment command to device
4. Device pulls and runs agent
5. Report health back to platform

**Configuration:**
```yaml
device_id: "edge-device-001"
device_group: "warehouse-sensors"
offline_capable: true
sync_interval: 60  # seconds
resource_limit:
  memory_mb: 256
  cpu_percent: 50
```

---

## Database Changes

### New Fields in AgentDeployment

```sql
ALTER TABLE agent_deployments ADD COLUMN deployment_config_v2 JSONB;
ALTER TABLE agent_deployments ADD COLUMN external_id VARCHAR(255);  -- K8s release name, Azure function name
ALTER TABLE agent_deployments ADD COLUMN access_url VARCHAR(512);
ALTER TABLE agent_deployments ADD COLUMN registry_image VARCHAR(512);
```

---

## Frontend Changes

### Deploy Wizard Flow

**Step 1: Choose Platform**
- Grid of deployment options with icons
- Show requirements/prerequisites for each

**Step 2: Platform-Specific Configuration**
- **Docker**: Port mapping, volume mounts
- **Kubernetes**: Cluster selection, namespace, replicas
- **Azure**: Subscription, region, plan
- **VM**: Host, SSH credentials, install path
- **Edge**: Device selection, offline mode

**Step 3: Environment Variables**
- Same for all platforms
- Adapter-specific vars

**Step 4: Review & Deploy**
- Summary of configuration
- One-click deploy button
- Real-time progress tracking

**Step 5: Access & Manage**
- Platform-specific access URL/instructions
- Logs viewer
- Start/Stop/Restart controls

---

## API Endpoints

### Unified Deploy (updated)
```
POST /api/v1/deploy/unified
{
  "agent_id": "uuid",
  "deployment_type": "kubernetes",
  "adapter": "openai",
  "platform_config": {
    "kubeconfig": "base64...",
    "namespace": "production",
    "replicas": 2
  },
  "env_vars": {...}
}
```

### Platform-Specific Validation
```
POST /api/v1/deploy/validate/{platform}
{
  "platform_config": {...}
}
```

### Push to Registry
```
POST /api/v1/deploy/{deployment_id}/push-registry
{
  "registry": "docker.io/myorg",
  "credentials": {...}
}
```

---

## Implementation Phases

### Phase 1: Refactor & Base Infrastructure (Week 1)
- [ ] Create deployers package structure
- [ ] Define BaseDeployer interface
- [ ] Refactor Docker to DockerDeployer
- [ ] Create DeploymentFactory
- [ ] Update unified_deploy.py to use factory

### Phase 2: Kubernetes/Helm (Week 2)
- [ ] Implement KubernetesDeployer
- [ ] Generate Helm charts from agent manifest
- [ ] Registry push functionality
- [ ] Helm install/upgrade
- [ ] Frontend K8s configuration

### Phase 3: Azure Functions (Week 3)
- [ ] Implement AzureFunctionsDeployer
- [ ] Function project generation
- [ ] Azure SDK integration
- [ ] Frontend Azure configuration

### Phase 4: VM/Bare Metal (Week 4)
- [ ] Implement VMDeployer
- [ ] SSH/SCP utilities
- [ ] Systemd service generation
- [ ] Frontend VM configuration

### Phase 5: Edge Devices (Week 5+)
- [ ] Design edge runtime protocol
- [ ] Implement EdgeDeployer
- [ ] Device enrollment flow
- [ ] Frontend device management

---

## Files to Create/Modify

### New Files
1. `backend/app/services/deployers/__init__.py`
2. `backend/app/services/deployers/base.py`
3. `backend/app/services/deployers/docker_deployer.py`
4. `backend/app/services/deployers/kubernetes_deployer.py`
5. `backend/app/services/deployers/azure_deployer.py`
6. `backend/app/services/deployers/vm_deployer.py`
7. `backend/app/services/deployers/edge_deployer.py`
8. `backend/app/services/deployment_factory.py`
9. `frontend-react/src/components/deploy/DeployWizard.tsx`
10. `frontend-react/src/components/deploy/platforms/*.tsx`

### Modified Files
1. `backend/app/api/api_v1/endpoints/unified_deploy.py`
2. `backend/app/models/enums.py`
3. `backend/app/models/agent_deployment.py`
4. `frontend-react/src/pages/AgentDetailPage.tsx`
5. `frontend-react/src/pages/DeploymentDashboard.tsx`

---

## Priority Order

1. **Kubernetes/Helm** - Most requested enterprise feature
2. **VM/Bare Metal** - Simple to implement, useful for on-prem
3. **Azure Functions** - Popular serverless option
4. **Edge Devices** - Advanced use case, implement last

