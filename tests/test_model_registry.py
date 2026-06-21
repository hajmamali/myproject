"""
Tests for Model Registry
========================
"""

import json
import tempfile
from pathlib import Path

import pytest

from mahoun.finetuning.model_registry import (
    ModelRegistry,
    ModelMetadata,
)


@pytest.fixture
def temp_registry():
    """Create a temporary registry for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "test_registry.json"
        registry = ModelRegistry(registry_path=str(registry_path))
        yield registry


@pytest.fixture
def sample_metadata():
    """Create sample model metadata"""
    return ModelMetadata(
        job_id="test_job_001",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test",
        output_dir="./models/test_job_001",
        gguf_paths={
            "q4_k_m": "./models/test_job_001/gguf_q4_k_m/model.gguf",
            "q5_k_m": "./models/test_job_001/gguf_q5_k_m/model.gguf",
        },
        metrics={"final_loss": 0.25, "perplexity": 1.28},
        domain="legal",
        status="completed",
        tags=["contracts", "test"]
    )


def test_register_model(temp_registry, sample_metadata):
    """Test registering a new model"""
    temp_registry.register(sample_metadata)
    
    # Verify registration
    retrieved = temp_registry.get_model(sample_metadata.job_id)
    assert retrieved is not None
    assert retrieved.job_id == sample_metadata.job_id
    assert retrieved.domain == "legal"
    assert retrieved.status == "completed"


def test_update_status(temp_registry, sample_metadata):
    """Test updating model status"""
    temp_registry.register(sample_metadata)
    
    # Update status
    temp_registry.update_status(sample_metadata.job_id, "failed")
    
    # Verify update
    retrieved = temp_registry.get_model(sample_metadata.job_id)
    assert retrieved.status == "failed"


def test_update_metrics(temp_registry, sample_metadata):
    """Test updating model metrics"""
    temp_registry.register(sample_metadata)
    
    # Update metrics
    new_metrics = {"accuracy": 0.95, "f1_score": 0.93}
    temp_registry.update_metrics(sample_metadata.job_id, new_metrics)
    
    # Verify update
    retrieved = temp_registry.get_model(sample_metadata.job_id)
    assert retrieved.metrics["accuracy"] == 0.95
    assert retrieved.metrics["f1_score"] == 0.93
    assert retrieved.metrics["final_loss"] == 0.25  # Original metric preserved


def test_add_gguf_path(temp_registry, sample_metadata):
    """Test adding GGUF export path"""
    temp_registry.register(sample_metadata)
    
    # Add new GGUF path
    temp_registry.add_gguf_path(sample_metadata.job_id, "f16", "./models/test/gguf_f16/model.gguf")
    
    # Verify addition
    retrieved = temp_registry.get_model(sample_metadata.job_id)
    assert "f16" in retrieved.gguf_paths
    assert retrieved.gguf_paths["f16"] == "./models/test/gguf_f16/model.gguf"


def test_list_models_no_filter(temp_registry, sample_metadata):
    """Test listing all models"""
    # Register multiple models
    temp_registry.register(sample_metadata)
    
    metadata2 = ModelMetadata(
        job_id="test_job_002",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test2",
        output_dir="./models/test_job_002",
        domain="medical",
        status="training"
    )
    temp_registry.register(metadata2)
    
    # List all
    models = temp_registry.list_models()
    assert len(models) == 2


def test_list_models_filter_domain(temp_registry, sample_metadata):
    """Test listing models filtered by domain"""
    # Register models with different domains
    temp_registry.register(sample_metadata)
    
    metadata2 = ModelMetadata(
        job_id="test_job_002",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test2",
        output_dir="./models/test_job_002",
        domain="medical",
        status="completed"
    )
    temp_registry.register(metadata2)
    
    # Filter by domain
    legal_models = temp_registry.list_models(domain="legal")
    assert len(legal_models) == 1
    assert legal_models[0].domain == "legal"
    
    medical_models = temp_registry.list_models(domain="medical")
    assert len(medical_models) == 1
    assert medical_models[0].domain == "medical"


def test_list_models_filter_status(temp_registry, sample_metadata):
    """Test listing models filtered by status"""
    # Register models with different statuses
    temp_registry.register(sample_metadata)
    
    metadata2 = ModelMetadata(
        job_id="test_job_002",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test2",
        output_dir="./models/test_job_002",
        domain="legal",
        status="training"
    )
    temp_registry.register(metadata2)
    
    # Filter by status
    completed = temp_registry.list_models(status="completed")
    assert len(completed) == 1
    assert completed[0].status == "completed"
    
    training = temp_registry.list_models(status="training")
    assert len(training) == 1
    assert training[0].status == "training"


def test_list_models_filter_tags(temp_registry, sample_metadata):
    """Test listing models filtered by tags"""
    # Register models with different tags
    temp_registry.register(sample_metadata)
    
    metadata2 = ModelMetadata(
        job_id="test_job_002",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test2",
        output_dir="./models/test_job_002",
        domain="legal",
        status="completed",
        tags=["disputes", "test"]
    )
    temp_registry.register(metadata2)
    
    # Filter by tags
    contract_models = temp_registry.list_models(tags=["contracts"])
    assert len(contract_models) == 1
    assert "contracts" in contract_models[0].tags
    
    test_models = temp_registry.list_models(tags=["test"])
    assert len(test_models) == 2  # Both have "test" tag


def test_get_best_model(temp_registry):
    """Test getting best model by metric"""
    # Register models with different metrics
    metadata1 = ModelMetadata(
        job_id="test_job_001",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test1",
        output_dir="./models/test_job_001",
        metrics={"final_loss": 0.25},
        domain="legal",
        status="completed"
    )
    temp_registry.register(metadata1)
    
    metadata2 = ModelMetadata(
        job_id="test_job_002",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test2",
        output_dir="./models/test_job_002",
        metrics={"final_loss": 0.18},
        domain="legal",
        status="completed"
    )
    temp_registry.register(metadata2)
    
    # Get best (lowest loss)
    best = temp_registry.get_best_model(metric="final_loss", domain="legal")
    assert best is not None
    assert best.job_id == "test_job_002"
    assert best.metrics["final_loss"] == 0.18


def test_get_best_model_maximize(temp_registry):
    """Test getting best model by maximizing metric"""
    # Register models with accuracy metrics
    metadata1 = ModelMetadata(
        job_id="test_job_001",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test1",
        output_dir="./models/test_job_001",
        metrics={"accuracy": 0.85},
        domain="legal",
        status="completed"
    )
    temp_registry.register(metadata1)
    
    metadata2 = ModelMetadata(
        job_id="test_job_002",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test2",
        output_dir="./models/test_job_002",
        metrics={"accuracy": 0.92},
        domain="legal",
        status="completed"
    )
    temp_registry.register(metadata2)
    
    # Get best (highest accuracy)
    best = temp_registry.get_best_model(metric="accuracy", domain="legal", minimize=False)
    assert best is not None
    assert best.job_id == "test_job_002"
    assert best.metrics["accuracy"] == 0.92


def test_delete_model(temp_registry, sample_metadata):
    """Test deleting a model"""
    temp_registry.register(sample_metadata)
    
    # Verify registration
    assert temp_registry.get_model(sample_metadata.job_id) is not None
    
    # Delete
    result = temp_registry.delete_model(sample_metadata.job_id)
    assert result is True
    
    # Verify deletion
    assert temp_registry.get_model(sample_metadata.job_id) is None


def test_persistence(temp_registry, sample_metadata):
    """Test that registry persists to disk"""
    # Register model
    temp_registry.register(sample_metadata)
    
    # Create new registry instance with same path
    registry2 = ModelRegistry(registry_path=str(temp_registry.registry_path))
    
    # Verify model was loaded
    retrieved = registry2.get_model(sample_metadata.job_id)
    assert retrieved is not None
    assert retrieved.job_id == sample_metadata.job_id


def test_get_statistics(temp_registry, sample_metadata):
    """Test getting registry statistics"""
    # Register multiple models
    temp_registry.register(sample_metadata)
    
    metadata2 = ModelMetadata(
        job_id="test_job_002",
        base_model="unsloth/llama-3-8b-bnb-4bit",
        dataset_path="./datasets/test2",
        output_dir="./models/test_job_002",
        domain="medical",
        status="training"
    )
    temp_registry.register(metadata2)
    
    # Get statistics
    stats = temp_registry.get_statistics()
    
    assert stats["total_models"] == 2
    assert stats["by_domain"]["legal"] == 1
    assert stats["by_domain"]["medical"] == 1
    assert stats["by_status"]["completed"] == 1
    assert stats["by_status"]["training"] == 1


def test_export_summary(temp_registry, sample_metadata):
    """Test exporting registry summary"""
    temp_registry.register(sample_metadata)
    
    # Export summary
    with tempfile.TemporaryDirectory() as tmpdir:
        summary_path = Path(tmpdir) / "summary.md"
        temp_registry.export_summary(str(summary_path))
        
        # Verify file was created
        assert summary_path.exists()
        
        # Verify content
        content = summary_path.read_text()
        assert "Fine-Tuned Models Registry" in content
        assert sample_metadata.job_id in content
        assert sample_metadata.domain in content
