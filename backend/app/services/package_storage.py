"""
Package Storage Service for Agent Packages.
Handles upload, download, and validation of agent packages.
"""
import os
import hashlib
import zipfile
import yaml
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid


@dataclass
class ManifestValidation:
    """Result of package validation."""
    is_valid: bool
    manifest: Optional[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]


@dataclass
class PackageInfo:
    """Information about an uploaded package."""
    url: str
    checksum: str
    size_bytes: int
    manifest: Dict[str, Any]
    adapters: List[str]


class PackageStorageService:
    """
    Store and retrieve agent packages.
    Supports local filesystem storage with option to extend to S3/Azure Blob.
    """
    
    def __init__(self, storage_path: str = "./storage/packages"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.temp_path = self.storage_path / "temp"
        self.temp_path.mkdir(parents=True, exist_ok=True)
    
    def upload_package(
        self, 
        agent_id: str, 
        version: str,
        package_content: bytes,
        filename: str
    ) -> PackageInfo:
        """
        Upload and process an agent package.
        
        Args:
            agent_id: UUID of the agent
            version: Version string (e.g., "1.0.0")
            package_content: Raw bytes of the zip file
            filename: Original filename
            
        Returns:
            PackageInfo with storage URL, checksum, and parsed manifest
        """
        # Calculate checksum
        checksum = hashlib.sha256(package_content).hexdigest()
        
        # Create storage directory for this agent
        agent_dir = self.storage_path / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Save package with version in filename
        package_filename = f"{version}.zip"
        package_path = agent_dir / package_filename
        
        with open(package_path, "wb") as f:
            f.write(package_content)
        
        # Extract and parse manifest
        # Ensure temp path exists (may have been deleted by cleanup)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        temp_extract_dir = self.temp_path / str(uuid.uuid4())
        try:
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            manifest = self._parse_manifest(temp_extract_dir)
            adapters = self._find_adapters(temp_extract_dir)
        finally:
            # Cleanup temp extraction
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)
        
        return PackageInfo(
            url=f"/storage/packages/{agent_id}/{package_filename}",
            checksum=checksum,
            size_bytes=len(package_content),
            manifest=manifest,
            adapters=adapters
        )
    
    def get_download_url(
        self, 
        agent_id: str, 
        version: str,
        expires_in_hours: int = 24
    ) -> Optional[str]:
        """
        Get download URL for a package.
        For local storage, returns the file path.
        For cloud storage, would generate a signed URL.
        """
        package_path = self.storage_path / agent_id / f"{version}.zip"
        if package_path.exists():
            # In production, this would be a signed URL
            return f"/api/v1/market/packages/{agent_id}/{version}/download"
        return None
    
    def get_package_path(self, agent_id: str, version: str) -> Optional[Path]:
        """Get the filesystem path to a package."""
        package_path = self.storage_path / agent_id / f"{version}.zip"
        if package_path.exists():
            return package_path
        return None
    
    def validate_package(self, package_content: bytes) -> ManifestValidation:
        """
        Validate a package before upload.
        
        Checks:
        - Valid ZIP file
        - Contains agent.yaml
        - Manifest is valid YAML
        - Required fields present
        """
        errors = []
        warnings = []
        manifest = None
        
        # Check if it's a valid ZIP
        # Ensure temp path exists (may have been deleted by cleanup)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        temp_file = self.temp_path / f"{uuid.uuid4()}.zip"
        try:
            with open(temp_file, "wb") as f:
                f.write(package_content)
            
            if not zipfile.is_zipfile(temp_file):
                errors.append("File is not a valid ZIP archive")
                return ManifestValidation(False, None, errors, warnings)
            
            # Extract and validate contents
            temp_extract = self.temp_path / str(uuid.uuid4())
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)
            
            # Check for agent.yaml
            manifest_path = self._find_manifest_path(temp_extract)
            if not manifest_path:
                errors.append("Package must contain agent.yaml in root directory")
                return ManifestValidation(False, None, errors, warnings)
            
            # Parse manifest
            try:
                with open(manifest_path, 'r') as f:
                    manifest = yaml.safe_load(f)
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML in agent.yaml: {e}")
                return ManifestValidation(False, None, errors, warnings)
            
            # Validate required fields
            validation_errors = self._validate_manifest_structure(manifest)
            errors.extend(validation_errors)
            
            # Check for optional components
            if not (temp_extract / "adapters").exists():
                warnings.append("No adapters directory found - agent may not be portable")
            
            if not (temp_extract / "policies").exists():
                warnings.append("No policies directory found - using default permissions")
            
            # Cleanup
            shutil.rmtree(temp_extract)
            
        finally:
            if temp_file.exists():
                temp_file.unlink()
        
        return ManifestValidation(
            is_valid=len(errors) == 0,
            manifest=manifest,
            errors=errors,
            warnings=warnings
        )
    
    def _parse_manifest(self, extract_dir: Path) -> Dict[str, Any]:
        """Parse the agent.yaml manifest from an extracted package."""
        manifest_path = self._find_manifest_path(extract_dir)
        if manifest_path and manifest_path.exists():
            with open(manifest_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _find_manifest_path(self, extract_dir: Path) -> Optional[Path]:
        """Find the agent.yaml file in the extracted package."""
        # Check root
        if (extract_dir / "agent.yaml").exists():
            return extract_dir / "agent.yaml"
        
        # Check one level deep (in case of nested folder)
        for child in extract_dir.iterdir():
            if child.is_dir():
                if (child / "agent.yaml").exists():
                    return child / "agent.yaml"
        
        return None
    
    def _find_adapters(self, extract_dir: Path) -> List[str]:
        """Find adapter configurations in the package."""
        adapters = []
        adapters_dir = extract_dir / "adapters"
        
        if not adapters_dir.exists():
            # Check one level deep
            for child in extract_dir.iterdir():
                if child.is_dir() and (child / "adapters").exists():
                    adapters_dir = child / "adapters"
                    break
        
        if adapters_dir.exists():
            for adapter_file in adapters_dir.glob("*.yaml"):
                adapter_name = adapter_file.stem
                adapters.append(adapter_name)
        
        return adapters
    
    def _validate_manifest_structure(self, manifest: Dict[str, Any]) -> List[str]:
        """Validate the structure of the manifest."""
        errors = []
        
        # Required top-level fields
        if "apiVersion" not in manifest:
            errors.append("Missing required field: apiVersion")
        
        if "kind" not in manifest:
            errors.append("Missing required field: kind")
        elif manifest.get("kind") != "Agent":
            errors.append("kind must be 'Agent'")
        
        if "metadata" not in manifest:
            errors.append("Missing required field: metadata")
        else:
            metadata = manifest["metadata"]
            if "name" not in metadata:
                errors.append("Missing required field: metadata.name")
            if "version" not in metadata:
                errors.append("Missing required field: metadata.version")
        
        if "spec" not in manifest:
            errors.append("Missing required field: spec")
        else:
            spec = manifest["spec"]
            if "displayName" not in spec:
                errors.append("Missing required field: spec.displayName")
            if "description" not in spec:
                errors.append("Missing required field: spec.description")
        
        return errors
    
    def delete_package(self, agent_id: str, version: str) -> bool:
        """Delete a package from storage."""
        package_path = self.storage_path / agent_id / f"{version}.zip"
        if package_path.exists():
            package_path.unlink()
            return True
        return False
    
    def list_versions(self, agent_id: str) -> List[str]:
        """List all versions of an agent package."""
        agent_dir = self.storage_path / agent_id
        if not agent_dir.exists():
            return []
        
        versions = []
        for package_file in agent_dir.glob("*.zip"):
            version = package_file.stem  # e.g., "1.0.0" from "1.0.0.zip"
            versions.append(version)
        
        return sorted(versions, reverse=True)


# Singleton instance
_storage_service: Optional[PackageStorageService] = None


def get_package_storage() -> PackageStorageService:
    """Get the package storage service singleton."""
    global _storage_service
    if _storage_service is None:
        # In production, read storage path from config
        storage_path = os.environ.get("PACKAGE_STORAGE_PATH", "./storage/packages")
        _storage_service = PackageStorageService(storage_path)
    return _storage_service
