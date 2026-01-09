"""
Kubernetes Deployer - Deploy agents to Kubernetes clusters via Helm.
"""
import os
import subprocess
import tempfile
import base64
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import (
    BaseDeployer, DeployConfig, DeployResult, BuildResult, 
    ValidationResult, StatusResult, DeploymentPlatform
)

logger = logging.getLogger(__name__)


class KubernetesDeployer(BaseDeployer):
    """Deploy agents to Kubernetes clusters using Helm charts."""
    
    platform = DeploymentPlatform.KUBERNETES
    display_name = "Kubernetes"
    description = "Deploy to your Kubernetes cluster via Helm"
    icon = "container"
    
    def __init__(self, 
                 charts_dir: str = "./storage/helm_charts",
                 default_registry: str = "docker.io/postqode"):
        self.charts_dir = Path(charts_dir)
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.default_registry = default_registry
    
    def _run_cmd(self, cmd: List[str], env: Dict = None, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run a shell command."""
        try:
            full_env = os.environ.copy()
            if env:
                full_env.update(env)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=full_env,
                check=False
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 1, "", "Command timed out")
        except Exception as e:
            logger.error(f"Command error: {e}")
            return subprocess.CompletedProcess(cmd, 1, "", str(e))
    
    def _write_kubeconfig(self, config: DeployConfig) -> Optional[Path]:
        """Write kubeconfig to temp file."""
        if not config.kubeconfig:
            return None
        
        try:
            kubeconfig_content = base64.b64decode(config.kubeconfig).decode('utf-8')
            kubeconfig_path = Path(tempfile.mktemp(suffix='.yaml'))
            kubeconfig_path.write_text(kubeconfig_content)
            return kubeconfig_path
        except Exception as e:
            logger.error(f"Failed to write kubeconfig: {e}")
            return None
    
    def check_prerequisites(self) -> ValidationResult:
        """Check if kubectl and helm are available."""
        requirements = {}
        errors = []
        
        # Check kubectl
        result = self._run_cmd(["kubectl", "version", "--client"])
        requirements["kubectl"] = result.returncode == 0
        if not requirements["kubectl"]:
            errors.append("kubectl is not installed")
        
        # Check helm
        result = self._run_cmd(["helm", "version"])
        requirements["helm"] = result.returncode == 0
        if not requirements["helm"]:
            errors.append("helm is not installed")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            requirements_met=requirements
        )
    
    def validate_config(self, config: DeployConfig) -> ValidationResult:
        """Validate Kubernetes deployment config."""
        errors = []
        warnings = []
        
        prereqs = self.check_prerequisites()
        if not prereqs.valid:
            return prereqs
        
        if not config.kubeconfig:
            warnings.append("No kubeconfig provided, will use default context")
        else:
            # Validate kubeconfig
            kubeconfig_path = self._write_kubeconfig(config)
            if kubeconfig_path:
                result = self._run_cmd(
                    ["kubectl", "cluster-info", "--kubeconfig", str(kubeconfig_path)],
                    timeout=30
                )
                kubeconfig_path.unlink()
                
                if result.returncode != 0:
                    errors.append("Failed to connect to Kubernetes cluster")
            else:
                errors.append("Invalid kubeconfig format")
        
        if not config.registry:
            warnings.append(f"No registry specified, using default: {self.default_registry}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            requirements_met={
                "kubectl": True,
                "helm": True,
                "cluster_connected": len(errors) == 0
            }
        )
    
    def build(
        self, 
        config: DeployConfig, 
        package_path: Path,
        progress_callback: Optional[callable] = None
    ) -> BuildResult:
        """Build Docker image and push to registry."""
        start_time = datetime.now()
        
        # First, build Docker image using DockerDeployer
        from .docker_deployer import DockerDeployer
        docker = DockerDeployer()
        
        if progress_callback:
            progress_callback("Building Docker image...")
        
        build_result = docker.build(config, package_path, progress_callback)
        
        if not build_result.success:
            return build_result
        
        # Tag for registry
        registry = config.registry or self.default_registry
        registry_tag = f"{registry}/{config.agent_name}:{config.version}"
        
        if progress_callback:
            progress_callback(f"Tagging image for registry: {registry_tag}")
        
        tag_result = self._run_cmd([
            "docker", "tag", build_result.image_tag, registry_tag
        ])
        
        if tag_result.returncode != 0:
            return BuildResult(
                success=False,
                error=f"Failed to tag image: {tag_result.stderr}",
                build_logs=build_result.build_logs + tag_result.stderr,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        # Push to registry
        if progress_callback:
            progress_callback(f"Pushing to registry {registry}...")
        
        push_result = self._run_cmd(
            ["docker", "push", registry_tag],
            timeout=600
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if push_result.returncode != 0:
            return BuildResult(
                success=False,
                error=f"Failed to push image: {push_result.stderr}",
                build_logs=build_result.build_logs + push_result.stdout + push_result.stderr,
                duration_seconds=duration
            )
        
        return BuildResult(
            success=True,
            image_name=registry_tag.split(":")[0],
            image_tag=registry_tag,
            artifact_path=build_result.artifact_path,
            build_logs=build_result.build_logs + push_result.stdout,
            duration_seconds=duration
        )
    
    def _generate_helm_chart(self, config: DeployConfig, image_tag: str) -> Path:
        """Generate Helm chart for the agent."""
        chart_path = self.charts_dir / config.agent_id / config.version
        chart_path.mkdir(parents=True, exist_ok=True)
        
        # Chart.yaml
        chart_yaml = {
            "apiVersion": "v2",
            "name": config.agent_name.lower().replace(" ", "-"),
            "description": f"PostQode Agent: {config.agent_name}",
            "type": "application",
            "version": "1.0.0",
            "appVersion": config.version
        }
        (chart_path / "Chart.yaml").write_text(yaml.dump(chart_yaml))
        
        # values.yaml
        values = {
            "replicaCount": config.replicas,
            "image": {
                "repository": image_tag.split(":")[0],
                "tag": image_tag.split(":")[-1],
                "pullPolicy": "Always"
            },
            "service": {
                "type": "ClusterIP",
                "port": 8080
            },
            "env": [
                {"name": key, "value": value}
                for key, value in config.env_vars.items()
            ] + [
                {"name": "POSTQODE_ADAPTER", "value": config.adapter},
                {"name": "POSTQODE_AGENT_ID", "value": config.agent_id},
            ],
            "resources": {
                "requests": {"memory": "512Mi", "cpu": "500m"},
                "limits": {"memory": "2Gi", "cpu": "2"}
            },
            "ingress": {
                "enabled": config.platform_config.get("ingress_enabled", False),
                "host": config.platform_config.get("ingress_host", "")
            }
        }
        (chart_path / "values.yaml").write_text(yaml.dump(values))
        
        # templates directory
        templates_path = chart_path / "templates"
        templates_path.mkdir(exist_ok=True)
        
        # deployment.yaml
        deployment = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Chart.Name }}
  labels:
    app: {{ .Chart.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Chart.Name }}
  template:
    metadata:
      labels:
        app: {{ .Chart.Name }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - containerPort: 8080
          env:
            {{- range .Values.env }}
            - name: {{ .name }}
              value: {{ .value | quote }}
            {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
"""
        (templates_path / "deployment.yaml").write_text(deployment)
        
        # service.yaml
        service = """
apiVersion: v1
kind: Service
metadata:
  name: {{ .Chart.Name }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: 8080
      protocol: TCP
  selector:
    app: {{ .Chart.Name }}
"""
        (templates_path / "service.yaml").write_text(service)
        
        # ingress.yaml (optional)
        ingress = """
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Chart.Name }}
spec:
  rules:
    - host: {{ .Values.ingress.host }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ .Chart.Name }}
                port:
                  number: {{ .Values.service.port }}
{{- end }}
"""
        (templates_path / "ingress.yaml").write_text(ingress)
        
        return chart_path
    
    def deploy(
        self, 
        deployment_id: str,
        config: DeployConfig,
        build_result: BuildResult,
        progress_callback: Optional[callable] = None
    ) -> DeployResult:
        """Deploy using Helm."""
        start_time = datetime.now()
        
        if not build_result.success:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error="Cannot deploy without successful build"
            )
        
        if progress_callback:
            progress_callback("Generating Helm chart...")
        
        chart_path = self._generate_helm_chart(config, build_result.image_tag)
        
        # Prepare kubeconfig
        kubeconfig_path = self._write_kubeconfig(config)
        env = {}
        if kubeconfig_path:
            env["KUBECONFIG"] = str(kubeconfig_path)
        
        release_name = f"agent-{config.agent_id[:8]}"
        
        if progress_callback:
            progress_callback(f"Installing Helm release: {release_name}")
        
        # Install or upgrade
        helm_cmd = [
            "helm", "upgrade", "--install",
            release_name,
            str(chart_path),
            "--namespace", config.namespace,
            "--create-namespace",
            "--wait",
            "--timeout", "5m"
        ]
        
        # Add deployment ID as annotation
        helm_cmd.extend([
            "--set", f"deploymentId={deployment_id}"
        ])
        
        result = self._run_cmd(helm_cmd, env=env, timeout=600)
        
        # Cleanup kubeconfig
        if kubeconfig_path:
            kubeconfig_path.unlink()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.returncode != 0:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error=result.stderr,
                deploy_logs=result.stdout + result.stderr,
                duration_seconds=duration
            )
        
        # Get service URL
        access_url = None
        if config.platform_config.get("ingress_enabled"):
            access_url = f"https://{config.platform_config.get('ingress_host')}"
        else:
            # Return kubectl port-forward instructions
            access_url = f"kubectl port-forward svc/{release_name} 8080:8080 -n {config.namespace}"
        
        return DeployResult(
            success=True,
            deployment_id=deployment_id,
            external_id=release_name,
            access_url=access_url,
            endpoints={
                "service": f"{release_name}.{config.namespace}.svc.cluster.local:8080"
            },
            deploy_logs=result.stdout,
            duration_seconds=duration
        )
    
    def start(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Scale deployment to replicas."""
        release_name = f"agent-{config.agent_id[:8]}"
        
        kubeconfig_path = self._write_kubeconfig(config)
        env = {"KUBECONFIG": str(kubeconfig_path)} if kubeconfig_path else {}
        
        result = self._run_cmd([
            "kubectl", "scale", "deployment", release_name,
            f"--replicas={config.replicas}",
            "-n", config.namespace
        ], env=env)
        
        if kubeconfig_path:
            kubeconfig_path.unlink()
        
        if result.returncode == 0:
            return StatusResult(running=True, status="running", health="unknown", message="Scaled up")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def stop(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Scale deployment to 0."""
        release_name = f"agent-{config.agent_id[:8]}"
        
        kubeconfig_path = self._write_kubeconfig(config)
        env = {"KUBECONFIG": str(kubeconfig_path)} if kubeconfig_path else {}
        
        result = self._run_cmd([
            "kubectl", "scale", "deployment", release_name,
            "--replicas=0",
            "-n", config.namespace
        ], env=env)
        
        if kubeconfig_path:
            kubeconfig_path.unlink()
        
        if result.returncode == 0:
            return StatusResult(running=False, status="stopped", health="unknown", message="Scaled to 0")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def restart(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Rollout restart."""
        release_name = f"agent-{config.agent_id[:8]}"
        
        kubeconfig_path = self._write_kubeconfig(config)
        env = {"KUBECONFIG": str(kubeconfig_path)} if kubeconfig_path else {}
        
        result = self._run_cmd([
            "kubectl", "rollout", "restart",
            f"deployment/{release_name}",
            "-n", config.namespace
        ], env=env)
        
        if kubeconfig_path:
            kubeconfig_path.unlink()
        
        if result.returncode == 0:
            return StatusResult(running=True, status="running", health="unknown", message="Rollout restarted")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def get_status(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Get deployment status."""
        release_name = f"agent-{config.agent_id[:8]}"
        
        kubeconfig_path = self._write_kubeconfig(config)
        env = {"KUBECONFIG": str(kubeconfig_path)} if kubeconfig_path else {}
        
        result = self._run_cmd([
            "kubectl", "get", "deployment", release_name,
            "-n", config.namespace,
            "-o", "jsonpath={.status.readyReplicas}/{.status.replicas}"
        ], env=env)
        
        if kubeconfig_path:
            kubeconfig_path.unlink()
        
        if result.returncode != 0:
            return StatusResult(running=False, status="unknown", health="unknown", message="Deployment not found")
        
        parts = result.stdout.strip().split("/")
        ready = int(parts[0]) if parts[0] else 0
        total = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        
        return StatusResult(
            running=ready > 0,
            status="running" if ready == total else "updating",
            health="healthy" if ready == total else "degraded",
            message=f"{ready}/{total} replicas ready",
            last_updated=datetime.now()
        )
    
    def get_logs(
        self, 
        deployment_id: str, 
        config: DeployConfig,
        lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get pod logs."""
        release_name = f"agent-{config.agent_id[:8]}"
        
        kubeconfig_path = self._write_kubeconfig(config)
        env = {"KUBECONFIG": str(kubeconfig_path)} if kubeconfig_path else {}
        
        cmd = [
            "kubectl", "logs",
            f"deployment/{release_name}",
            "-n", config.namespace,
            f"--tail={lines}"
        ]
        if follow:
            cmd.append("-f")
        
        result = self._run_cmd(cmd, env=env)
        
        if kubeconfig_path:
            kubeconfig_path.unlink()
        
        return result.stdout + result.stderr
    
    def delete(self, deployment_id: str, config: DeployConfig) -> bool:
        """Uninstall Helm release."""
        release_name = f"agent-{config.agent_id[:8]}"
        
        kubeconfig_path = self._write_kubeconfig(config)
        env = {"KUBECONFIG": str(kubeconfig_path)} if kubeconfig_path else {}
        
        result = self._run_cmd([
            "helm", "uninstall", release_name,
            "-n", config.namespace
        ], env=env)
        
        if kubeconfig_path:
            kubeconfig_path.unlink()
        
        return result.returncode == 0
    
    def get_access_instructions(self, deployment_id: str, config: DeployConfig) -> Dict[str, str]:
        """Get Kubernetes-specific access instructions."""
        release_name = f"agent-{config.agent_id[:8]}"
        return {
            "port_forward": f"kubectl port-forward svc/{release_name} 8080:8080 -n {config.namespace}",
            "logs": f"kubectl logs deployment/{release_name} -n {config.namespace}",
            "status": f"kubectl get pods -l app={release_name} -n {config.namespace}",
            "helm_status": f"helm status {release_name} -n {config.namespace}"
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for Kubernetes config."""
        return {
            "type": "object",
            "properties": {
                "kubeconfig": {
                    "type": "string",
                    "format": "base64",
                    "description": "Base64-encoded kubeconfig file"
                },
                "namespace": {
                    "type": "string",
                    "default": "default",
                    "description": "Kubernetes namespace"
                },
                "replicas": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Number of replicas"
                },
                "registry": {
                    "type": "string",
                    "description": "Container registry to push images"
                },
                "ingress_enabled": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable Ingress resource"
                },
                "ingress_host": {
                    "type": "string",
                    "description": "Ingress hostname"
                }
            },
            "required": []
        }
