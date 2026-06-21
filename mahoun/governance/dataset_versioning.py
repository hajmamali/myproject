"""
Dataset Versioning with DVC Integration
========================================

Provides cryptographic versioning for training datasets with full lineage tracking.

Features:
- SHA256 hashing for dataset integrity
- DVC integration for version control
- Metadata tracking (version, timestamp, metrics, provenance)
- Rollback support
- Dataset comparison and diff
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import subprocess
import logging

logger = logging.getLogger(__name__)


class DatasetVersion(BaseModel):
    """Dataset version metadata."""
    version: str = Field(..., description="Version identifier (e.g., 'v1.0.0')")
    dataset_name: str = Field(..., description="Dataset name")
    hash: str = Field(..., description="SHA256 hash of dataset")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    description: str = Field(default="", description="Version description")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Quality metrics")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Data provenance")
    file_count: int = Field(default=0, ge=0)
    total_size_bytes: int = Field(default=0, ge=0)
    source_datasets: List[str] = Field(default_factory=list, description="Source dataset versions")
    
    model_config = ConfigDict(frozen=True)


class DatasetVersionManager:
    """
    Manages dataset versioning with DVC integration.
    
    Provides cryptographic hashing, version tracking, and rollback capabilities.
    """
    
    def __init__(self, versions_dir: Path = Path("dataset_versions")):
        """
        Initialize dataset version manager.
        
        Args:
            versions_dir: Directory to store version metadata
        """
        self.versions_dir = Path(versions_dir)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.dvc_enabled = self._check_dvc_available()
        
    def _check_dvc_available(self) -> bool:
        """Check if DVC is available."""
        try:
            result = subprocess.run(
                ["dvc", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("DVC not available - versioning will use local storage only")
            return False
    
    def compute_dataset_hash(self, dataset_path: Path) -> str:
        """
        Compute SHA256 hash of entire dataset.
        
        Args:
            dataset_path: Path to dataset directory
            
        Returns:
            SHA256 hash as hex string
        """
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset path not found: {dataset_path}")
        
        hasher = hashlib.sha256()
        
        # Sort files for deterministic hashing
        files = sorted(dataset_path.rglob("*"))
        
        for file_path in files:
            if file_path.is_file():
                # Hash relative path
                rel_path = file_path.relative_to(dataset_path)
                hasher.update(str(rel_path).encode('utf-8'))
                
                # Hash file content
                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def create_version(
        self,
        dataset_path: Path,
        dataset_name: str,
        version: str,
        description: str = "",
        metrics: Optional[Dict[str, float]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        source_datasets: Optional[List[str]] = None
    ) -> DatasetVersion:
        """
        Create new dataset version.
        
        Args:
            dataset_path: Path to dataset
            dataset_name: Name of dataset
            version: Version identifier
            description: Version description
            metrics: Quality metrics
            provenance: Data provenance information
            source_datasets: Source dataset versions
            
        Returns:
            DatasetVersion object
        """
        logger.info(f"Creating version {version} for dataset {dataset_name}")
        
        # Compute hash
        dataset_hash = self.compute_dataset_hash(dataset_path)
        
        # Count files and size
        files = list(dataset_path.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        
        # Create version metadata
        version_obj = DatasetVersion(
            version=version,
            dataset_name=dataset_name,
            hash=dataset_hash,
            description=description,
            metrics=metrics or {},
            provenance=provenance or {},
            file_count=file_count,
            total_size_bytes=total_size,
            source_datasets=source_datasets or []
        )
        
        # Save metadata
        self._save_version_metadata(version_obj)
        
        # DVC tracking if available
        if self.dvc_enabled:
            self._dvc_add(dataset_path, version)
        
        logger.info(f"Version {version} created with hash {dataset_hash[:16]}...")
        return version_obj
    
    def _save_version_metadata(self, version: DatasetVersion) -> None:
        """Save version metadata to disk."""
        filename = f"{version.dataset_name}_{version.version}.json"
        filepath = self.versions_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(version.model_dump(mode='json'), f, indent=2, default=str)
    
    def _dvc_add(self, dataset_path: Path, version: str) -> None:
        """Add dataset to DVC tracking."""
        try:
            # Add to DVC
            subprocess.run(
                ["dvc", "add", str(dataset_path)],
                check=True,
                capture_output=True,
                timeout=60
            )
            
            # Tag version
            subprocess.run(
                ["git", "tag", f"data-{version}"],
                check=False,  # Don't fail if tag exists
                capture_output=True,
                timeout=10
            )
            
            logger.info(f"Dataset added to DVC with tag data-{version}")
        except subprocess.TimeoutExpired:
            logger.error("DVC add timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"DVC add failed: {e.stderr.decode()}")
    
    def list_versions(self, dataset_name: str) -> List[DatasetVersion]:
        """
        List all versions of a dataset.
        
        Args:
            dataset_name: Name of dataset
            
        Returns:
            List of DatasetVersion objects sorted by timestamp
        """
        versions = []
        
        for filepath in self.versions_dir.glob(f"{dataset_name}_*.json"):
            with open(filepath, 'r') as f:
                data = json.load(f)
                versions.append(DatasetVersion(**data))
        
        # Sort by timestamp (newest first)
        versions.sort(key=lambda v: v.timestamp, reverse=True)
        return versions
    
    def get_version(self, dataset_name: str, version: str) -> Optional[DatasetVersion]:
        """
        Get specific dataset version.
        
        Args:
            dataset_name: Name of dataset
            version: Version identifier
            
        Returns:
            DatasetVersion object or None if not found
        """
        filepath = self.versions_dir / f"{dataset_name}_{version}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            return DatasetVersion(**data)
    
    def verify_dataset(self, dataset_path: Path, expected_hash: str) -> bool:
        """
        Verify dataset integrity against expected hash.
        
        Args:
            dataset_path: Path to dataset
            expected_hash: Expected SHA256 hash
            
        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = self.compute_dataset_hash(dataset_path)
        return actual_hash == expected_hash
    
    def compare_versions(
        self,
        dataset_name: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two dataset versions.
        
        Args:
            dataset_name: Name of dataset
            version1: First version
            version2: Second version
            
        Returns:
            Comparison results
        """
        v1 = self.get_version(dataset_name, version1)
        v2 = self.get_version(dataset_name, version2)
        
        if not v1 or not v2:
            raise ValueError(f"Version not found: {version1} or {version2}")
        
        return {
            "version1": version1,
            "version2": version2,
            "hash_changed": v1.hash != v2.hash,
            "file_count_diff": v2.file_count - v1.file_count,
            "size_diff_bytes": v2.total_size_bytes - v1.total_size_bytes,
            "metrics_diff": {
                k: v2.metrics.get(k, 0) - v1.metrics.get(k, 0)
                for k in set(v1.metrics.keys()) | set(v2.metrics.keys())
            },
            "timestamp_diff_seconds": (v2.timestamp - v1.timestamp).total_seconds()
        }
    
    def rollback(self, dataset_name: str, version: str, target_path: Path) -> bool:
        """
        Rollback dataset to specific version using DVC.
        
        Args:
            dataset_name: Name of dataset
            version: Version to rollback to
            target_path: Path to restore dataset
            
        Returns:
            True if successful, False otherwise
        """
        if not self.dvc_enabled:
            logger.error("DVC not available - cannot rollback")
            return False
        
        version_obj = self.get_version(dataset_name, version)
        if not version_obj:
            logger.error(f"Version {version} not found")
            return False
        
        try:
            # Checkout DVC version
            subprocess.run(
                ["git", "checkout", f"data-{version}"],
                check=True,
                capture_output=True,
                timeout=30
            )
            
            subprocess.run(
                ["dvc", "checkout", str(target_path)],
                check=True,
                capture_output=True,
                timeout=120
            )
            
            logger.info(f"Rolled back to version {version}")
            return True
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            logger.error(f"Rollback failed: {e}")
            return False
