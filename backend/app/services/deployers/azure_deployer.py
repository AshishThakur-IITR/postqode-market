"""
Azure Functions Deployer - Deploy agents as serverless functions.
"""
import os
import subprocess
import shutil
import zipfile
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import (
    BaseDeployer, DeployConfig, DeployResult, BuildResult, 
    ValidationResult, StatusResult, DeploymentPlatform
)

logger = logging.getLogger(__name__)


class AzureFunctionsDeployer(BaseDeployer):
    """Deploy agents as Azure Functions (Serverless)."""
    
    platform = DeploymentPlatform.AZURE_FUNCTIONS
    display_name = "Azure Functions"
    description = "Serverless deployment on Azure"
    icon = "zap"
    
    def __init__(self, build_dir: str = "./storage/azure_builds"):
        self.build_dir = Path(build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)
    
    def _run_cmd(self, cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
        """Run a shell command."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(cmd, 1, "", "Command timed out")
        except Exception as e:
            return subprocess.CompletedProcess(cmd, 1, "", str(e))
    
    def check_prerequisites(self) -> ValidationResult:
        """Check if Azure CLI and Functions Core Tools are available."""
        requirements = {}
        errors = []
        
        # Check Azure CLI
        result = self._run_cmd(["az", "--version"])
        requirements["azure_cli"] = result.returncode == 0
        if not requirements["azure_cli"]:
            errors.append("Azure CLI is not installed. Install with: brew install azure-cli")
        
        # Check if logged in
        result = self._run_cmd(["az", "account", "show"])
        requirements["azure_logged_in"] = result.returncode == 0
        if not requirements["azure_logged_in"]:
            errors.append("Not logged into Azure. Run: az login")
        
        # Check Functions Core Tools
        result = self._run_cmd(["func", "--version"])
        requirements["func_tools"] = result.returncode == 0
        if not requirements["func_tools"]:
            errors.append("Azure Functions Core Tools not installed. Install with: npm install -g azure-functions-core-tools@4")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            requirements_met=requirements
        )
    
    def validate_config(self, config: DeployConfig) -> ValidationResult:
        """Validate Azure Functions config."""
        errors = []
        warnings = []
        
        prereqs = self.check_prerequisites()
        if not prereqs.valid:
            return prereqs
        
        # Check required config
        if not config.platform_config.get("resource_group"):
            errors.append("resource_group is required")
        
        if not config.platform_config.get("function_app_name"):
            errors.append("function_app_name is required")
        
        if not config.platform_config.get("storage_account"):
            warnings.append("No storage_account specified, a new one will be created")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            requirements_met=prereqs.requirements_met
        )
    
    def _generate_function_project(self, config: DeployConfig, package_path: Path) -> Path:
        """Generate Azure Function project from agent package."""
        project_path = self.build_dir / config.agent_id / config.version
        if project_path.exists():
            shutil.rmtree(project_path)
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Extract original package
        with zipfile.ZipFile(package_path, 'r') as zip_ref:
            zip_ref.extractall(project_path / "agent")
        
        # Find agent.py
        agent_code = None
        for path in (project_path / "agent").rglob("agent.py"):
            agent_code = path
            break
        
        # Create Azure Function structure
        # host.json
        host_json = {
            "version": "2.0",
            "logging": {
                "applicationInsights": {
                    "samplingSettings": {
                        "isEnabled": True,
                        "excludedTypes": "Request"
                    }
                }
            },
            "extensionBundle": {
                "id": "Microsoft.Azure.Functions.ExtensionBundle",
                "version": "[3.*, 4.0.0)"
            }
        }
        (project_path / "host.json").write_text(json.dumps(host_json, indent=2))
        
        # local.settings.json
        local_settings = {
            "IsEncrypted": False,
            "Values": {
                "FUNCTIONS_WORKER_RUNTIME": "python",
                "AzureWebJobsStorage": "",
                **config.env_vars,
                "POSTQODE_AGENT_ID": config.agent_id,
                "POSTQODE_ADAPTER": config.adapter
            }
        }
        (project_path / "local.settings.json").write_text(json.dumps(local_settings, indent=2))
        
        # requirements.txt
        original_reqs = project_path / "agent" / "requirements.txt"
        if not original_reqs.exists():
            original_reqs = list((project_path / "agent").rglob("requirements.txt"))
            original_reqs = original_reqs[0] if original_reqs else None
        
        reqs = "azure-functions\n"
        if original_reqs and original_reqs.exists():
            reqs += original_reqs.read_text()
        (project_path / "requirements.txt").write_text(reqs)
        
        # Create HTTP trigger function
        func_path = project_path / "InvokeAgent"
        func_path.mkdir(exist_ok=True)
        
        # function.json
        function_json = {
            "scriptFile": "__init__.py",
            "bindings": [
                {
                    "authLevel": "function",
                    "type": "httpTrigger",
                    "direction": "in",
                    "name": "req",
                    "methods": ["get", "post"]
                },
                {
                    "type": "http",
                    "direction": "out",
                    "name": "$return"
                }
            ]
        }
        (func_path / "function.json").write_text(json.dumps(function_json, indent=2))
        
        # __init__.py (wrapper for agent)
        wrapper_code = '''
import azure.functions as func
import json
import sys
import os

# Add agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function wrapper for PostQode Agent."""
    try:
        # Import agent
        from agent import agent
        
        # Parse request
        try:
            body = req.get_json()
        except:
            body = {}
        
        # Handle different endpoints
        route = req.route_params.get('route', '')
        
        if req.method == 'GET' and not body:
            # Health check
            return func.HttpResponse(
                json.dumps({"status": "healthy", "agent_id": os.environ.get("POSTQODE_AGENT_ID")}),
                mimetype="application/json"
            )
        
        # Invoke agent
        action = body.get('action', 'default')
        params = body.get('params', body)
        
        # Call the appropriate handler
        if hasattr(agent, 'handlers') and action in agent.handlers:
            result = await agent.handlers[action](params)
        else:
            result = {"error": f"Unknown action: {action}"}
        
        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
'''
        (func_path / "__init__.py").write_text(wrapper_code)
        
        return project_path
    
    def build(
        self, 
        config: DeployConfig, 
        package_path: Path,
        progress_callback: Optional[callable] = None
    ) -> BuildResult:
        """Build Azure Functions project."""
        start_time = datetime.now()
        
        if progress_callback:
            progress_callback("Generating Azure Functions project...")
        
        try:
            project_path = self._generate_function_project(config, package_path)
        except Exception as e:
            return BuildResult(
                success=False,
                error=f"Failed to generate project: {e}",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        if progress_callback:
            progress_callback("Installing dependencies...")
        
        # Install dependencies (for validation)
        result = self._run_cmd(
            ["pip", "install", "-r", str(project_path / "requirements.txt"), "-t", str(project_path / ".python_packages")]
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.returncode != 0:
            return BuildResult(
                success=False,
                error=f"Failed to install dependencies: {result.stderr}",
                build_logs=result.stdout + result.stderr,
                duration_seconds=duration
            )
        
        return BuildResult(
            success=True,
            artifact_path=project_path,
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
        """Deploy to Azure Functions."""
        start_time = datetime.now()
        
        if not build_result.success or not build_result.artifact_path:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error="Cannot deploy without successful build"
            )
        
        resource_group = config.platform_config.get("resource_group")
        function_app = config.platform_config.get("function_app_name")
        location = config.platform_config.get("location", "eastus")
        
        if progress_callback:
            progress_callback(f"Creating/updating Function App: {function_app}...")
        
        # Create resource group if needed
        self._run_cmd([
            "az", "group", "create",
            "--name", resource_group,
            "--location", location
        ])
        
        # Create storage account if needed
        storage_account = config.platform_config.get("storage_account")
        if not storage_account:
            storage_account = f"postqode{config.agent_id[:8]}"
            self._run_cmd([
                "az", "storage", "account", "create",
                "--name", storage_account,
                "--resource-group", resource_group,
                "--location", location,
                "--sku", "Standard_LRS"
            ])
        
        # Create Function App
        create_result = self._run_cmd([
            "az", "functionapp", "create",
            "--name", function_app,
            "--resource-group", resource_group,
            "--storage-account", storage_account,
            "--consumption-plan-location", location,
            "--runtime", "python",
            "--runtime-version", "3.11",
            "--os-type", "Linux",
            "--functions-version", "4"
        ], timeout=300)
        
        if create_result.returncode != 0 and "already exists" not in create_result.stderr:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error=f"Failed to create Function App: {create_result.stderr}",
                deploy_logs=create_result.stdout + create_result.stderr,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        # Configure app settings (env vars)
        if progress_callback:
            progress_callback("Configuring environment variables...")
        
        settings = [f"{k}={v}" for k, v in config.env_vars.items()]
        settings.append(f"POSTQODE_DEPLOYMENT_ID={deployment_id}")
        settings.append(f"POSTQODE_AGENT_ID={config.agent_id}")
        settings.append(f"POSTQODE_ADAPTER={config.adapter}")
        
        if settings:
            self._run_cmd([
                "az", "functionapp", "config", "appsettings", "set",
                "--name", function_app,
                "--resource-group", resource_group,
                "--settings", *settings
            ])
        
        # Deploy code
        if progress_callback:
            progress_callback("Deploying code to Azure...")
        
        deploy_result = self._run_cmd([
            "func", "azure", "functionapp", "publish", function_app,
            "--python"
        ], timeout=600)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if deploy_result.returncode != 0:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error=f"Failed to deploy: {deploy_result.stderr}",
                deploy_logs=deploy_result.stdout + deploy_result.stderr,
                duration_seconds=duration
            )
        
        # Get function URL
        access_url = f"https://{function_app}.azurewebsites.net/api/InvokeAgent"
        
        return DeployResult(
            success=True,
            deployment_id=deployment_id,
            external_id=function_app,
            access_url=access_url,
            endpoints={
                "invoke": access_url,
                "portal": f"https://portal.azure.com/#@/resource/subscriptions/.../resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{function_app}"
            },
            deploy_logs=deploy_result.stdout,
            duration_seconds=duration
        )
    
    def start(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Start the Function App."""
        function_app = config.platform_config.get("function_app_name")
        resource_group = config.platform_config.get("resource_group")
        
        result = self._run_cmd([
            "az", "functionapp", "start",
            "--name", function_app,
            "--resource-group", resource_group
        ])
        
        if result.returncode == 0:
            return StatusResult(running=True, status="running", health="unknown", message="Function App started")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def stop(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Stop the Function App."""
        function_app = config.platform_config.get("function_app_name")
        resource_group = config.platform_config.get("resource_group")
        
        result = self._run_cmd([
            "az", "functionapp", "stop",
            "--name", function_app,
            "--resource-group", resource_group
        ])
        
        if result.returncode == 0:
            return StatusResult(running=False, status="stopped", health="unknown", message="Function App stopped")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def restart(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Restart the Function App."""
        function_app = config.platform_config.get("function_app_name")
        resource_group = config.platform_config.get("resource_group")
        
        result = self._run_cmd([
            "az", "functionapp", "restart",
            "--name", function_app,
            "--resource-group", resource_group
        ])
        
        if result.returncode == 0:
            return StatusResult(running=True, status="running", health="unknown", message="Function App restarted")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def get_status(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Get Function App status."""
        function_app = config.platform_config.get("function_app_name")
        resource_group = config.platform_config.get("resource_group")
        
        result = self._run_cmd([
            "az", "functionapp", "show",
            "--name", function_app,
            "--resource-group", resource_group,
            "--query", "state",
            "-o", "tsv"
        ])
        
        if result.returncode != 0:
            return StatusResult(running=False, status="unknown", health="unknown", message="Function App not found")
        
        state = result.stdout.strip().lower()
        
        return StatusResult(
            running=(state == "running"),
            status=state,
            health="healthy" if state == "running" else "unknown",
            message=f"Function App is {state}",
            last_updated=datetime.now()
        )
    
    def get_logs(
        self, 
        deployment_id: str, 
        config: DeployConfig,
        lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get Function App logs."""
        function_app = config.platform_config.get("function_app_name")
        resource_group = config.platform_config.get("resource_group")
        
        result = self._run_cmd([
            "az", "webapp", "log", "tail",
            "--name", function_app,
            "--resource-group", resource_group
        ], timeout=30)
        
        return result.stdout + result.stderr
    
    def delete(self, deployment_id: str, config: DeployConfig) -> bool:
        """Delete the Function App."""
        function_app = config.platform_config.get("function_app_name")
        resource_group = config.platform_config.get("resource_group")
        
        result = self._run_cmd([
            "az", "functionapp", "delete",
            "--name", function_app,
            "--resource-group", resource_group,
            "--yes"
        ])
        
        return result.returncode == 0
    
    def get_access_instructions(self, deployment_id: str, config: DeployConfig) -> Dict[str, str]:
        """Get Azure-specific access instructions."""
        function_app = config.platform_config.get("function_app_name")
        return {
            "url": f"https://{function_app}.azurewebsites.net/api/InvokeAgent",
            "logs": f"az webapp log tail --name {function_app} --resource-group {config.platform_config.get('resource_group')}",
            "portal": "View in Azure Portal",
            "note": "Add ?code=<function_key> for authentication"
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for Azure config."""
        return {
            "type": "object",
            "properties": {
                "resource_group": {
                    "type": "string",
                    "description": "Azure Resource Group name"
                },
                "function_app_name": {
                    "type": "string",
                    "description": "Name of the Function App (must be globally unique)"
                },
                "location": {
                    "type": "string",
                    "default": "eastus",
                    "description": "Azure region",
                    "enum": ["eastus", "westus", "westeurope", "eastasia", "australiaeast"]
                },
                "storage_account": {
                    "type": "string",
                    "description": "Azure Storage Account (optional, auto-created if not provided)"
                }
            },
            "required": ["resource_group", "function_app_name"]
        }
