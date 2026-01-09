"""
VM Deployer - Deploy agents to VMs or bare metal servers via SSH.
"""
import os
import subprocess
import shutil
import base64
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import (
    BaseDeployer, DeployConfig, DeployResult, BuildResult, 
    ValidationResult, StatusResult, DeploymentPlatform
)

logger = logging.getLogger(__name__)


class VMDeployer(BaseDeployer):
    """Deploy agents to virtual machines or bare metal servers via SSH."""
    
    platform = DeploymentPlatform.VM_STANDALONE
    display_name = "VM / Bare Metal"
    description = "Deploy to traditional servers via SSH"
    icon = "server"
    
    def __init__(self, build_dir: str = "./storage/vm_builds"):
        self.build_dir = Path(build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)
    
    def _write_ssh_key(self, config: DeployConfig) -> Optional[Path]:
        """Write SSH key to temp file."""
        if not config.ssh_key:
            return None
        
        try:
            key_content = base64.b64decode(config.ssh_key).decode('utf-8')
            key_path = Path(tempfile.mktemp())
            key_path.write_text(key_content)
            os.chmod(str(key_path), 0o600)
            return key_path
        except Exception as e:
            logger.error(f"Failed to write SSH key: {e}")
            return None
    
    def _run_ssh(self, config: DeployConfig, command: str, key_path: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run SSH command."""
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
        
        if key_path:
            ssh_cmd.extend(["-i", str(key_path)])
        
        port = config.platform_config.get("ssh_port", 22)
        ssh_cmd.extend(["-p", str(port)])
        
        ssh_cmd.append(f"{config.ssh_user}@{config.ssh_host}")
        ssh_cmd.append(command)
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False
            )
            return result
        except Exception as e:
            return subprocess.CompletedProcess(ssh_cmd, 1, "", str(e))
    
    def _run_scp(self, config: DeployConfig, source: Path, dest: str, key_path: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Copy file via SCP."""
        scp_cmd = ["scp", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
        
        if key_path:
            scp_cmd.extend(["-i", str(key_path)])
        
        port = config.platform_config.get("ssh_port", 22)
        scp_cmd.extend(["-P", str(port)])
        
        if source.is_dir():
            scp_cmd.append("-r")
        
        scp_cmd.append(str(source))
        scp_cmd.append(f"{config.ssh_user}@{config.ssh_host}:{dest}")
        
        try:
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False
            )
            return result
        except Exception as e:
            return subprocess.CompletedProcess(scp_cmd, 1, "", str(e))
    
    def check_prerequisites(self) -> ValidationResult:
        """Check if SSH client is available."""
        try:
            result = subprocess.run(["ssh", "-V"], capture_output=True, text=True)
            return ValidationResult(
                valid=True,
                requirements_met={"ssh": True}
            )
        except:
            return ValidationResult(
                valid=False,
                errors=["SSH client not available"],
                requirements_met={"ssh": False}
            )
    
    def validate_config(self, config: DeployConfig) -> ValidationResult:
        """Validate VM deployment config."""
        errors = []
        warnings = []
        
        if not config.ssh_host:
            errors.append("ssh_host is required")
        
        if not config.ssh_key and not config.platform_config.get("password"):
            warnings.append("No SSH key or password provided, will use default SSH agent")
        
        # Test SSH connection
        if config.ssh_host:
            key_path = self._write_ssh_key(config)
            result = self._run_ssh(config, "echo 'test'", key_path)
            if key_path:
                key_path.unlink()
            
            if result.returncode != 0:
                errors.append(f"Cannot connect to server: {result.stderr}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            requirements_met={
                "ssh": True,
                "server_reachable": len(errors) == 0
            }
        )
    
    def build(
        self, 
        config: DeployConfig, 
        package_path: Path,
        progress_callback: Optional[callable] = None
    ) -> BuildResult:
        """Prepare agent package for VM deployment."""
        start_time = datetime.now()
        
        if progress_callback:
            progress_callback("Preparing deployment package...")
        
        # For VM, we just need to prepare the package with a startup script
        build_path = self.build_dir / config.agent_id / config.version
        build_path.mkdir(parents=True, exist_ok=True)
        
        # Copy package
        dest_package = build_path / "agent.zip"
        shutil.copy(package_path, dest_package)
        
        # Generate startup script
        startup_script = f'''#!/bin/bash
# PostQode Agent Startup Script
set -e

AGENT_DIR="/opt/postqode/agents/{config.agent_id}"
LOG_DIR="/var/log/postqode"

echo "Installing PostQode Agent: {config.agent_name}"

# Create directories
mkdir -p $AGENT_DIR
mkdir -p $LOG_DIR

# Extract agent
cd $AGENT_DIR
unzip -o /tmp/agent.zip

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    for f in $(find . -name "requirements.txt" | head -1); do
        pip install -r $f
    done
fi

# Create environment file
cat > .env << EOF
POSTQODE_DEPLOYMENT_ID={config.agent_id}
POSTQODE_AGENT_ID={config.agent_id}
POSTQODE_ADAPTER={config.adapter}
'''
        for key, value in config.env_vars.items():
            startup_script += f"{key}={value}\n"
        
        startup_script += '''EOF

echo "Agent installed at $AGENT_DIR"
'''
        (build_path / "install.sh").write_text(startup_script)
        os.chmod(str(build_path / "install.sh"), 0o755)
        
        # Generate systemd service file
        service_file = f'''[Unit]
Description=PostQode Agent - {config.agent_name}
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/postqode/agents/{config.agent_id}
EnvironmentFile=/opt/postqode/agents/{config.agent_id}/.env
ExecStart=/opt/postqode/agents/{config.agent_id}/venv/bin/python agent.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/postqode/{config.agent_id}.log
StandardError=append:/var/log/postqode/{config.agent_id}.error.log

[Install]
WantedBy=multi-user.target
'''
        (build_path / "postqode-agent.service").write_text(service_file)
        
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
        """Deploy to VM via SSH."""
        start_time = datetime.now()
        logs = []
        
        if not build_result.success or not build_result.artifact_path:
            return DeployResult(
                success=False,
                deployment_id=deployment_id,
                error="Cannot deploy without successful build"
            )
        
        key_path = self._write_ssh_key(config)
        
        try:
            if progress_callback:
                progress_callback("Uploading agent package...")
            
            # Upload package
            result = self._run_scp(
                config,
                build_result.artifact_path / "agent.zip",
                "/tmp/agent.zip",
                key_path
            )
            logs.append(f"SCP: {result.stdout}{result.stderr}")
            
            if result.returncode != 0:
                return DeployResult(
                    success=False,
                    deployment_id=deployment_id,
                    error=f"Failed to upload package: {result.stderr}",
                    deploy_logs="\n".join(logs),
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            # Upload install script
            result = self._run_scp(
                config,
                build_result.artifact_path / "install.sh",
                "/tmp/install.sh",
                key_path
            )
            logs.append(f"SCP install.sh: {result.stdout}{result.stderr}")
            
            # Upload service file
            result = self._run_scp(
                config,
                build_result.artifact_path / "postqode-agent.service",
                "/tmp/postqode-agent.service",
                key_path
            )
            logs.append(f"SCP service: {result.stdout}{result.stderr}")
            
            if progress_callback:
                progress_callback("Running installation script...")
            
            # Run install script
            result = self._run_ssh(config, "sudo bash /tmp/install.sh", key_path)
            logs.append(f"Install: {result.stdout}{result.stderr}")
            
            if result.returncode != 0:
                return DeployResult(
                    success=False,
                    deployment_id=deployment_id,
                    error=f"Installation failed: {result.stderr}",
                    deploy_logs="\n".join(logs),
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            if progress_callback:
                progress_callback("Setting up systemd service...")
            
            # Install and start service
            service_name = f"postqode-{config.agent_id[:8]}"
            
            commands = [
                f"sudo cp /tmp/postqode-agent.service /etc/systemd/system/{service_name}.service",
                "sudo systemctl daemon-reload",
                f"sudo systemctl enable {service_name}",
                f"sudo systemctl restart {service_name}"
            ]
            
            for cmd in commands:
                result = self._run_ssh(config, cmd, key_path)
                logs.append(f"{cmd}: {result.stdout}{result.stderr}")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Get access info
            port = config.port
            access_url = f"http://{config.ssh_host}:{port}"
            
            return DeployResult(
                success=True,
                deployment_id=deployment_id,
                external_id=service_name,
                access_url=access_url,
                endpoints={
                    "web": access_url,
                    "ssh": f"{config.ssh_user}@{config.ssh_host}"
                },
                deploy_logs="\n".join(logs),
                duration_seconds=duration
            )
            
        finally:
            if key_path:
                key_path.unlink()
    
    def start(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Start the service."""
        service_name = f"postqode-{config.agent_id[:8]}"
        key_path = self._write_ssh_key(config)
        
        result = self._run_ssh(config, f"sudo systemctl start {service_name}", key_path)
        
        if key_path:
            key_path.unlink()
        
        if result.returncode == 0:
            return StatusResult(running=True, status="running", health="unknown", message="Service started")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def stop(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Stop the service."""
        service_name = f"postqode-{config.agent_id[:8]}"
        key_path = self._write_ssh_key(config)
        
        result = self._run_ssh(config, f"sudo systemctl stop {service_name}", key_path)
        
        if key_path:
            key_path.unlink()
        
        if result.returncode == 0:
            return StatusResult(running=False, status="stopped", health="unknown", message="Service stopped")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def restart(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Restart the service."""
        service_name = f"postqode-{config.agent_id[:8]}"
        key_path = self._write_ssh_key(config)
        
        result = self._run_ssh(config, f"sudo systemctl restart {service_name}", key_path)
        
        if key_path:
            key_path.unlink()
        
        if result.returncode == 0:
            return StatusResult(running=True, status="running", health="unknown", message="Service restarted")
        return StatusResult(running=False, status="error", health="unknown", message=result.stderr)
    
    def get_status(self, deployment_id: str, config: DeployConfig) -> StatusResult:
        """Get service status."""
        service_name = f"postqode-{config.agent_id[:8]}"
        key_path = self._write_ssh_key(config)
        
        result = self._run_ssh(
            config, 
            f"systemctl is-active {service_name} && systemctl show {service_name} --property=ActiveEnterTimestamp --value",
            key_path
        )
        
        if key_path:
            key_path.unlink()
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            status = lines[0] if lines else 'unknown'
            return StatusResult(
                running=(status == "active"),
                status=status,
                health="healthy" if status == "active" else "unknown",
                message=f"Service is {status}",
                last_updated=datetime.now()
            )
        
        return StatusResult(
            running=False,
            status="unknown",
            health="unknown",
            message="Could not get status"
        )
    
    def get_logs(
        self, 
        deployment_id: str, 
        config: DeployConfig,
        lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get service logs."""
        service_name = f"postqode-{config.agent_id[:8]}"
        key_path = self._write_ssh_key(config)
        
        cmd = f"sudo journalctl -u {service_name} -n {lines} --no-pager"
        result = self._run_ssh(config, cmd, key_path)
        
        if key_path:
            key_path.unlink()
        
        return result.stdout + result.stderr
    
    def delete(self, deployment_id: str, config: DeployConfig) -> bool:
        """Stop and disable service."""
        service_name = f"postqode-{config.agent_id[:8]}"
        key_path = self._write_ssh_key(config)
        
        commands = [
            f"sudo systemctl stop {service_name}",
            f"sudo systemctl disable {service_name}",
            f"sudo rm /etc/systemd/system/{service_name}.service",
            f"sudo rm -rf /opt/postqode/agents/{config.agent_id}"
        ]
        
        success = True
        for cmd in commands:
            result = self._run_ssh(config, cmd, key_path)
            if result.returncode != 0:
                success = False
        
        if key_path:
            key_path.unlink()
        
        return success
    
    def get_access_instructions(self, deployment_id: str, config: DeployConfig) -> Dict[str, str]:
        """Get VM-specific access instructions."""
        service_name = f"postqode-{config.agent_id[:8]}"
        return {
            "ssh": f"ssh {config.ssh_user}@{config.ssh_host}",
            "logs": f"sudo journalctl -u {service_name} -f",
            "status": f"sudo systemctl status {service_name}",
            "restart": f"sudo systemctl restart {service_name}"
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for VM config."""
        return {
            "type": "object",
            "properties": {
                "ssh_host": {
                    "type": "string",
                    "description": "Server hostname or IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "default": "root",
                    "description": "SSH username"
                },
                "ssh_port": {
                    "type": "integer",
                    "default": 22,
                    "description": "SSH port"
                },
                "ssh_key": {
                    "type": "string",
                    "format": "base64",
                    "description": "Base64-encoded SSH private key"
                },
                "install_path": {
                    "type": "string",
                    "default": "/opt/postqode/agents",
                    "description": "Installation directory on server"
                }
            },
            "required": ["ssh_host"]
        }
