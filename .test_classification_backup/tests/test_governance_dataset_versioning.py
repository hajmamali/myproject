"""
Comprehensive tests for dataset versioning.

Tests cover:
- SHA256 hash computation
- Version creation and metadata
- DVC integration
- Version comparison
- Rollback functionality
- Edge cases
"""

import pytest
import json
import hashlib
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from mahoun.governance.dataset_versioning import (
    DatasetVersionManager,
    DatasetVersion
)


class TestDatasetVersion:
    """Test dataset version model."""
    
    def test_version_creation(self):
        """Test creating a dataset version."""
        version = DatasetVersion(
            version="v1.0.0",
            dataset_name="training_data",
            hash="abc123",
            description="Initial version",
            metrics={"accuracy": 0.95},
            provenance={"source": "production"},
            file_count=100,
            total_size_bytes=1024000,
            source_datasets=["raw_v1.0"]
        )
        
        assert version.version == "v1.0.0"
        assert version.dataset_name == "training_data"
        assert version.hash == "abc123"
        assert version.metrics["accuracy"] == 0.95
    
    def test_version_immutability(self):
        """Test that version is immutable."""
        version = DatasetVersion(
            version="v1.0.0",
            dataset_name="test",
            hash="abc123"
        )
        
        with pytest.raises(Exception):  # Pydantic frozen model
            version.version = "v2.0.0"
    
    def test_version_defaults(self):
        """Test default values."""
        version = DatasetVersion(
            version="v1.0.0",
            dataset_name="test",
            hash="abc123"
        )
        
        assert version.description == ""
        assert version.metrics == {}
        assert version.provenance == {}
        assert version.file_count == 0
        assert version.total_size_bytes == 0
        assert version.source_datasets == []


class TestDatasetVersionManager:
    """Test dataset version manager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)
    
    @pytest.fixture
    def temp_dataset(self, temp_dir):
        """Create temporary dataset."""
        dataset_dir = temp_dir / "dataset"
        dataset_dir.mkdir()
        
        # Create some files
        (dataset_dir / "file1.txt").write_text("content1")
        (dataset_dir / "file2.txt").write_text("content2")
        (dataset_dir / "subdir").mkdir()
        (dataset_dir / "subdir" / "file3.txt").write_text("content3")
        
        return dataset_dir
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create version manager."""
        return DatasetVersionManager(versions_dir=temp_dir / "versions")
    
    def test_initialization(self, temp_dir):
        """Test manager initialization."""
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        
        assert manager.versions_dir.exists()
        assert isinstance(manager.dvc_enabled, bool)
    
    def test_compute_dataset_hash(self, manager, temp_dataset):
        """Test SHA256 hash computation."""
        hash1 = manager.compute_dataset_hash(temp_dataset)
        
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex length
        
        # Same dataset should produce same hash
        hash2 = manager.compute_dataset_hash(temp_dataset)
        assert hash1 == hash2
    
    def test_hash_deterministic(self, manager, temp_dataset):
        """Test that hash is deterministic."""
        hashes = [manager.compute_dataset_hash(temp_dataset) for _ in range(5)]
        
        assert all(h == hashes[0] for h in hashes)
    
    def test_hash_changes_with_content(self, manager, temp_dataset):
        """Test that hash changes when content changes."""
        hash1 = manager.compute_dataset_hash(temp_dataset)
        
        # Modify content
        (temp_dataset / "file1.txt").write_text("modified content")
        
        hash2 = manager.compute_dataset_hash(temp_dataset)
        
        assert hash1 != hash2
    
    def test_hash_changes_with_new_file(self, manager, temp_dataset):
        """Test that hash changes when files are added."""
        hash1 = manager.compute_dataset_hash(temp_dataset)
        
        # Add new file
        (temp_dataset / "file4.txt").write_text("new content")
        
        hash2 = manager.compute_dataset_hash(temp_dataset)
        
        assert hash1 != hash2
    
    def test_hash_nonexistent_path(self, manager, temp_dir):
        """Test hash computation with nonexistent path."""
        with pytest.raises(FileNotFoundError):
            manager.compute_dataset_hash(temp_dir / "nonexistent")
    
    def test_create_version(self, manager, temp_dataset):
        """Test creating a version."""
        version = manager.create_version(
            dataset_path=temp_dataset,
            dataset_name="test_dataset",
            version="v1.0.0",
            description="Test version",
            metrics={"quality": 0.95},
            provenance={"source": "test"}
        )
        
        assert isinstance(version, DatasetVersion)
        assert version.version == "v1.0.0"
        assert version.dataset_name == "test_dataset"
        assert version.file_count == 3
        assert version.total_size_bytes > 0
    
    def test_version_metadata_saved(self, manager, temp_dataset):
        """Test that version metadata is saved to disk."""
        version = manager.create_version(
            dataset_path=temp_dataset,
            dataset_name="test_dataset",
            version="v1.0.0"
        )
        
        # Check file exists
        metadata_file = manager.versions_dir / "test_dataset_v1.0.0.json"
        assert metadata_file.exists()
        
        # Verify content
        with open(metadata_file, 'r') as f:
            data = json.load(f)
            assert data["version"] == "v1.0.0"
            assert data["dataset_name"] == "test_dataset"
    
    def test_list_versions(self, manager, temp_dataset):
        """Test listing versions."""
        # Create multiple versions
        manager.create_version(temp_dataset, "test_dataset", "v1.0.0")
        manager.create_version(temp_dataset, "test_dataset", "v1.1.0")
        manager.create_version(temp_dataset, "test_dataset", "v2.0.0")
        
        versions = manager.list_versions("test_dataset")
        
        assert len(versions) == 3
        assert all(isinstance(v, DatasetVersion) for v in versions)
        
        # Should be sorted by timestamp (newest first)
        assert versions[0].version == "v2.0.0"
    
    def test_get_version(self, manager, temp_dataset):
        """Test getting specific version."""
        manager.create_version(temp_dataset, "test_dataset", "v1.0.0")
        
        version = manager.get_version("test_dataset", "v1.0.0")
        
        assert version is not None
        assert version.version == "v1.0.0"
    
    def test_get_nonexistent_version(self, manager):
        """Test getting nonexistent version."""
        version = manager.get_version("test_dataset", "v99.0.0")
        
        assert version is None
    
    def test_verify_dataset(self, manager, temp_dataset):
        """Test dataset verification."""
        expected_hash = manager.compute_dataset_hash(temp_dataset)
        
        # Should verify successfully
        assert manager.verify_dataset(temp_dataset, expected_hash) == True
        
        # Should fail with wrong hash
        assert manager.verify_dataset(temp_dataset, "wrong_hash") == False
    
    def test_compare_versions(self, manager, temp_dataset):
        """Test version comparison."""
        # Create first version
        v1 = manager.create_version(
            temp_dataset,
            "test_dataset",
            "v1.0.0",
            metrics={"accuracy": 0.90}
        )
        
        # Modify dataset
        (temp_dataset / "file4.txt").write_text("new content")
        
        # Create second version
        v2 = manager.create_version(
            temp_dataset,
            "test_dataset",
            "v2.0.0",
            metrics={"accuracy": 0.95}
        )
        
        comparison = manager.compare_versions("test_dataset", "v1.0.0", "v2.0.0")
        
        assert comparison["hash_changed"] == True
        assert comparison["file_count_diff"] == 1
        assert comparison["size_diff_bytes"] > 0
        assert comparison["metrics_diff"]["accuracy"] == 0.05
    
    def test_compare_nonexistent_versions(self, manager):
        """Test comparing nonexistent versions."""
        with pytest.raises(ValueError):
            manager.compare_versions("test_dataset", "v1.0.0", "v2.0.0")
    
    def test_source_datasets_tracking(self, manager, temp_dataset):
        """Test tracking of source datasets."""
        version = manager.create_version(
            temp_dataset,
            "derived_dataset",
            "v1.0.0",
            source_datasets=["raw_v1.0", "raw_v1.1"]
        )
        
        assert len(version.source_datasets) == 2
        assert "raw_v1.0" in version.source_datasets


class TestDVCIntegration:
    """Test DVC integration."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)
    
    @pytest.fixture
    def temp_dataset(self, temp_dir):
        """Create temporary dataset."""
        dataset_dir = temp_dir / "dataset"
        dataset_dir.mkdir()
        (dataset_dir / "file1.txt").write_text("content")
        return dataset_dir
    
    @patch('subprocess.run')
    def test_dvc_add_called(self, mock_run, temp_dir, temp_dataset):
        """Test that DVC add is called when enabled."""
        mock_run.return_value = Mock(returncode=0)
        
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        manager.dvc_enabled = True
        
        manager.create_version(temp_dataset, "test", "v1.0.0")
        
        # Should call dvc add
        calls = [str(call) for call in mock_run.call_args_list]
        assert any("dvc" in str(call) for call in calls)
    
    @patch('subprocess.run')
    def test_dvc_not_called_when_disabled(self, mock_run, temp_dir, temp_dataset):
        """Test that DVC is not called when disabled."""
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        manager.dvc_enabled = False
        
        manager.create_version(temp_dataset, "test", "v1.0.0")
        
        # Should not call dvc
        assert not any("dvc" in str(call) for call in mock_run.call_args_list)
    
    @patch('subprocess.run')
    def test_rollback_with_dvc(self, mock_run, temp_dir, temp_dataset):
        """Test rollback with DVC."""
        mock_run.return_value = Mock(returncode=0)
        
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        manager.dvc_enabled = True
        
        # Create version
        manager.create_version(temp_dataset, "test", "v1.0.0")
        
        # Rollback
        result = manager.rollback("test", "v1.0.0", temp_dataset)
        
        assert result == True
    
    def test_rollback_without_dvc(self, temp_dir, temp_dataset):
        """Test rollback fails without DVC."""
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        manager.dvc_enabled = False
        
        manager.create_version(temp_dataset, "test", "v1.0.0")
        
        result = manager.rollback("test", "v1.0.0", temp_dataset)
        
        assert result == False
    
    def test_rollback_nonexistent_version(self, temp_dir, temp_dataset):
        """Test rollback with nonexistent version."""
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        manager.dvc_enabled = True
        
        result = manager.rollback("test", "v99.0.0", temp_dataset)
        
        assert result == False


class TestEdgeCases:
    """Test edge cases."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)
    
    def test_empty_dataset(self, temp_dir):
        """Test with empty dataset."""
        dataset_dir = temp_dir / "empty_dataset"
        dataset_dir.mkdir()
        
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        
        version = manager.create_version(dataset_dir, "empty", "v1.0.0")
        
        assert version.file_count == 0
        assert version.total_size_bytes == 0
    
    def test_large_file_count(self, temp_dir):
        """Test with many files."""
        dataset_dir = temp_dir / "large_dataset"
        dataset_dir.mkdir()
        
        # Create 1000 small files
        for i in range(1000):
            (dataset_dir / f"file{i}.txt").write_text(f"content{i}")
        
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        
        version = manager.create_version(dataset_dir, "large", "v1.0.0")
        
        assert version.file_count == 1000
    
    def test_nested_directories(self, temp_dir):
        """Test with deeply nested directories."""
        dataset_dir = temp_dir / "nested"
        
        # Create nested structure
        current = dataset_dir
        for i in range(10):
            current = current / f"level{i}"
            current.mkdir(parents=True)
            (current / "file.txt").write_text(f"content{i}")
        
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        
        version = manager.create_version(dataset_dir, "nested", "v1.0.0")
        
        assert version.file_count == 10
    
    def test_special_characters_in_filenames(self, temp_dir):
        """Test with special characters in filenames."""
        dataset_dir = temp_dir / "special"
        dataset_dir.mkdir()
        
        # Create files with special characters
        (dataset_dir / "file with spaces.txt").write_text("content")
        (dataset_dir / "file-with-dashes.txt").write_text("content")
        (dataset_dir / "file_with_underscores.txt").write_text("content")
        
        manager = DatasetVersionManager(versions_dir=temp_dir / "versions")
        
        hash1 = manager.compute_dataset_hash(dataset_dir)
        assert isinstance(hash1, str)


@pytest.mark.slow
class TestVersioningPerformance:
    """Performance tests for versioning."""
    
    def test_hash_large_dataset(self, tmp_path):
        """Test hashing performance on large dataset."""
        dataset_dir = tmp_path / "large_dataset"
        dataset_dir.mkdir()
        
        # Create 10MB of data
        for i in range(100):
            (dataset_dir / f"file{i}.txt").write_bytes(b"x" * 100000)
        
        manager = DatasetVersionManager(versions_dir=tmp_path / "versions")
        
        import time
        start = time.time()
        
        hash_value = manager.compute_dataset_hash(dataset_dir)
        
        elapsed = time.time() - start
        
        assert isinstance(hash_value, str)
        assert elapsed < 5.0, f"Hashing too slow: {elapsed}s"
    
    def test_many_versions(self, tmp_path):
        """Test performance with many versions."""
        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()
        (dataset_dir / "file.txt").write_text("content")
        
        manager = DatasetVersionManager(versions_dir=tmp_path / "versions")
        
        import time
        start = time.time()
        
        # Create 100 versions
        for i in range(100):
            manager.create_version(dataset_dir, "test", f"v1.0.{i}")
        
        elapsed = time.time() - start
        
        assert elapsed < 10.0, f"Version creation too slow: {elapsed}s"
        
        # Test listing performance
        start = time.time()
        versions = manager.list_versions("test")
        elapsed = time.time() - start
        
        assert len(versions) == 100
        assert elapsed < 1.0, f"Listing too slow: {elapsed}s"
