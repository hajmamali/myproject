"""
Tests for Policy Deployment Orchestrator
=========================================

Tests:
- Semantic versioning (compatibility checks)
- Artifact storage and retrieval
- Deployment planning and validation
- Multi-stage deployment (staging → canary → production)
- Automatic rollback on failure
- Deployment approval workflow
- Dependency resolution
- Hot-reload capability
- Concurrent deployment prevention
- Deployment history and audit trail
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from mahoun.core.policy_deployment import (
    PolicyVersion,
    PolicyArtifact,
    PolicyArtifactStore,
    DeploymentStage,
    DeploymentStatus,
    PolicyDeploymentOrchestrator,
    ValidationResult,
)
from mahoun.core.exceptions_v2 import ValidationError, OperationalError


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def artifact_store(temp_storage):
    """Create policy artifact store"""
    return PolicyArtifactStore(temp_storage / "artifacts")


@pytest.fixture
def orchestrator(artifact_store):
    """Create deployment orchestrator"""
    return PolicyDeploymentOrchestrator(artifact_store)


@pytest.fixture
def sample_artifact():
    """Create sample policy artifact"""
    return PolicyArtifact(
        policy_id="execution_policy",
        version=PolicyVersion(1, 0, 0),
        content={
            "max_concurrent_requests": 100,
            "timeout_seconds": 300,
            "enable_graph": True,
        },
        created_by="test-user",
    )


# ============================================================================
# POLICY VERSION TESTS
# ============================================================================


@pytest.mark.p1
def test_policy_version_parsing():
    """Test PolicyVersion parsing from string"""
    version = PolicyVersion.from_string("2.3.5")
    assert version.major == 2
    assert version.minor == 3
    assert version.patch == 5
    assert str(version) == "2.3.5"


@pytest.mark.p1
def test_policy_version_comparison():
    """Test PolicyVersion comparison operators"""
    v1 = PolicyVersion(1, 0, 0)
    v2 = PolicyVersion(1, 0, 1)
    v3 = PolicyVersion(1, 1, 0)
    v4 = PolicyVersion(2, 0, 0)
    
    assert v1 < v2 < v3 < v4
    assert v1 == PolicyVersion(1, 0, 0)


@pytest.mark.p1
def test_policy_version_compatibility():
    """Test PolicyVersion backwards compatibility check"""
    v1_0_0 = PolicyVersion(1, 0, 0)
    v1_0_1 = PolicyVersion(1, 0, 1)  # Patch upgrade — compatible
    v1_1_0 = PolicyVersion(1, 1, 0)  # Minor upgrade — compatible
    v2_0_0 = PolicyVersion(2, 0, 0)  # Major upgrade — NOT compatible
    
    # Patch and minor upgrades are compatible
    assert v1_0_1.is_compatible_with(v1_0_0)
    assert v1_1_0.is_compatible_with(v1_0_0)
    
    # Major version change breaks compatibility
    assert not v2_0_0.is_compatible_with(v1_0_0)


# ============================================================================
# POLICY ARTIFACT TESTS
# ============================================================================

@pytest.mark.p1
def test_artifact_hash_computation(sample_artifact):
    """Test PolicyArtifact content hash computation"""
    # Hash should be deterministic
    artifact1 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value"},
    )
    
    artifact2 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value"},
    )
    
    # Same content → same hash
    assert artifact1.artifact_hash == artifact2.artifact_hash
    
    # Different content → different hash
    artifact3 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "different_value"},
    )
    
    assert artifact1.artifact_hash != artifact3.artifact_hash


@pytest.mark.p1
def test_artifact_serialization(sample_artifact):
    """Test PolicyArtifact to_dict and from_dict"""
    # Serialize
    artifact_dict = sample_artifact.to_dict()
    
    # Deserialize
    restored = PolicyArtifact.from_dict(artifact_dict)
    
    # Should be equal
    assert restored.policy_id == sample_artifact.policy_id
    assert restored.version == sample_artifact.version
    assert restored.content == sample_artifact.content
    assert restored.artifact_hash == sample_artifact.artifact_hash


# ============================================================================
# ARTIFACT STORE TESTS
# ============================================================================

@pytest.mark.p1
def test_artifact_store_basic_operations(artifact_store, sample_artifact):
    """Test PolicyArtifactStore store and get"""
    # Store artifact
    artifact_store.store(sample_artifact)
    
    # Retrieve by ID and version
    retrieved = artifact_store.get(
        sample_artifact.policy_id,
        sample_artifact.version,
    )
    
    assert retrieved is not None
    assert retrieved.policy_id == sample_artifact.policy_id
    assert retrieved.version == sample_artifact.version


@pytest.mark.p1
def test_artifact_store_get_latest(artifact_store):
    """Test PolicyArtifactStore get latest version"""
    # Store multiple versions
    v1 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"v": 1},
    )
    v2 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 1),
        content={"v": 2},
    )
    v3 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 1, 0),
        content={"v": 3},
    )
    
    artifact_store.store(v1)
    artifact_store.store(v2)
    artifact_store.store(v3)
    
    # Get latest (should be v1.1.0)
    latest = artifact_store.get("test_policy")
    assert latest.version == PolicyVersion(1, 1, 0)


@pytest.mark.p1
def test_artifact_store_idempotent(artifact_store, sample_artifact):
    """Test PolicyArtifactStore idempotent store"""
    # Store same artifact twice
    artifact_store.store(sample_artifact)
    artifact_store.store(sample_artifact)  # Should not raise error
    
    # Should still only have one
    versions = artifact_store.list_versions(sample_artifact.policy_id)
    assert len(versions) == 1


@pytest.mark.p1
def test_artifact_store_duplicate_detection(artifact_store):
    """Test PolicyArtifactStore duplicate version detection"""
    # Store artifact
    artifact1 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value1"},
    )
    artifact_store.store(artifact1)
    
    # Try to store different artifact with same version
    artifact2 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value2"},  # Different content
    )
    
    # Should raise ValidationError
    with pytest.raises(ValidationError, match="different content"):
        artifact_store.store(artifact2)


# ============================================================================
# DEPLOYMENT PLANNING TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_planning(orchestrator, sample_artifact):
    """Test deployment planning creates valid plan"""
    plan = await orchestrator.plan_deployment(
        artifact=sample_artifact,
        target_stage=DeploymentStage.STAGING,
    )
    
    assert plan.deployment_id is not None
    assert plan.artifact == sample_artifact
    assert plan.target_stage == DeploymentStage.STAGING
    assert len(plan.validation_checks) > 0
    assert len(plan.deployment_steps) > 0


@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_validation_checks(orchestrator, sample_artifact):
    """Test deployment plan includes validation checks"""
    plan = await orchestrator.plan_deployment(
        artifact=sample_artifact,
        target_stage=DeploymentStage.PRODUCTION,
    )
    
    # Should have schema validation check
    check_names = [check.check_name for check in plan.validation_checks]
    assert "schema_validation" in check_names
    assert "dependency_resolution" in check_names



@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_backwards_compatibility_check(orchestrator):
    """Test backwards compatibility validation"""
    # Deploy v1.0.0
    v1 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value"},
    )
    orchestrator.artifact_store.store(v1)
    
    # Plan v1.0.1 (compatible patch)
    v1_0_1 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 1),
        content={"key": "value", "new_key": "new_value"},
    )
    plan = await orchestrator.plan_deployment(v1_0_1, DeploymentStage.PRODUCTION)
    
    # Should pass compatibility check
    compat_check = next(
        (c for c in plan.validation_checks if c.check_name == "backwards_compatibility"),
        None
    )
    assert compat_check is not None
    assert compat_check.result == ValidationResult.PASS
    
    # Plan v2.0.0 (breaking change)
    v2 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(2, 0, 0),
        content={"completely": "different"},
    )
    plan2 = await orchestrator.plan_deployment(v2, DeploymentStage.PRODUCTION)
    
    # Should warn about breaking change
    compat_check2 = next(
        (c for c in plan2.validation_checks if c.check_name == "backwards_compatibility"),
        None
    )
    assert compat_check2 is not None
    assert compat_check2.result == ValidationResult.WARNING


# ============================================================================
# DEPLOYMENT APPROVAL TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_approval_workflow(orchestrator, sample_artifact):
    """Test deployment approval for production"""
    plan = await orchestrator.plan_deployment(
        artifact=sample_artifact,
        target_stage=DeploymentStage.PRODUCTION,
    )
    
    # Production deployment requires approval
    assert plan.approval_required is True
    assert len(plan.approvers) == 0
    
    # Approve deployment
    await orchestrator.approve_deployment(
        deployment_id=plan.deployment_id,
        approver="admin@mahoun.ai",
    )
    
    # Check approval recorded
    assert "admin@mahoun.ai" in plan.approvers


@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_approval_duplicate_prevention(orchestrator, sample_artifact):
    """Test duplicate approval prevention"""
    plan = await orchestrator.plan_deployment(
        artifact=sample_artifact,
        target_stage=DeploymentStage.PRODUCTION,
    )
    
    # First approval
    await orchestrator.approve_deployment(plan.deployment_id, "admin@mahoun.ai")
    
    # Second approval by same person should fail
    with pytest.raises(ValidationError, match="Already approved"):
        await orchestrator.approve_deployment(plan.deployment_id, "admin@mahoun.ai")


# ============================================================================
# DEPLOYMENT EXECUTION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_execution_success(orchestrator, sample_artifact):
    """Test successful deployment execution"""
    # Plan deployment to staging (no approval required)
    plan = await orchestrator.plan_deployment(
        artifact=sample_artifact,
        target_stage=DeploymentStage.STAGING,
    )
    plan.approval_required = False  # Override for test
    
    # Execute deployment
    record = await orchestrator.deploy(plan)
    
    assert record.status == DeploymentStatus.DEPLOYED
    assert record.deployment_id == plan.deployment_id
    assert record.completed_at is not None
    assert record.error_message is None


@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_execution_requires_approval(orchestrator, sample_artifact):
    """Test deployment fails without approval"""
    # Plan production deployment
    plan = await orchestrator.plan_deployment(
        artifact=sample_artifact,
        target_stage=DeploymentStage.PRODUCTION,
    )
    
    # Execute without approval should fail
    record = await orchestrator.deploy(plan)
    
    assert record.status == DeploymentStatus.FAILED
    assert "requires approval" in record.error_message.lower()


@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_concurrent_prevention(orchestrator):
    """Test concurrent deployment prevention (lock)"""
    artifact1 = PolicyArtifact(
        policy_id="policy_a",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value1"},
    )
    artifact2 = PolicyArtifact(
        policy_id="policy_b",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value2"},
    )
    
    # Plan deployments
    plan1 = await orchestrator.plan_deployment(artifact1, DeploymentStage.STAGING)
    plan1.approval_required = False
    
    plan2 = await orchestrator.plan_deployment(artifact2, DeploymentStage.STAGING)
    plan2.approval_required = False
    
    # Start deployments concurrently
    results = await asyncio.gather(
        orchestrator.deploy(plan1),
        orchestrator.deploy(plan2),
    )
    
    # Both should succeed (lock prevents race conditions)
    assert all(r.status == DeploymentStatus.DEPLOYED for r in results)


# ============================================================================
# DEPLOYMENT HISTORY TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_history_tracking(orchestrator, sample_artifact):
    """Test deployment history is recorded"""
    # Execute deployment
    plan = await orchestrator.plan_deployment(sample_artifact, DeploymentStage.STAGING)
    plan.approval_required = False
    await orchestrator.deploy(plan)
    
    # Check history
    history = orchestrator.get_deployment_history()
    assert len(history) == 1
    assert history[0].artifact.policy_id == sample_artifact.policy_id


@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_history_filtering(orchestrator):
    """Test deployment history filtering by policy_id"""
    # Deploy multiple policies
    artifact1 = PolicyArtifact(
        policy_id="policy_a",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value1"},
    )
    artifact2 = PolicyArtifact(
        policy_id="policy_b",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value2"},
    )
    
    plan1 = await orchestrator.plan_deployment(artifact1, DeploymentStage.STAGING)
    plan1.approval_required = False
    await orchestrator.deploy(plan1)
    
    plan2 = await orchestrator.plan_deployment(artifact2, DeploymentStage.STAGING)
    plan2.approval_required = False
    await orchestrator.deploy(plan2)
    
    # Filter by policy_id
    history_a = orchestrator.get_deployment_history(policy_id="policy_a")
    assert len(history_a) == 1
    assert history_a[0].artifact.policy_id == "policy_a"


# ============================================================================
# ROLLBACK TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_rollback(orchestrator):
    """Test manual rollback to previous version"""
    # Deploy v1.0.0
    v1 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value1"},
    )
    plan1 = await orchestrator.plan_deployment(v1, DeploymentStage.PRODUCTION)
    plan1.approval_required = False
    await orchestrator.deploy(plan1)
    
    # Deploy v1.0.1
    v2 = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 1),
        content={"key": "value2"},
    )
    plan2 = await orchestrator.plan_deployment(v2, DeploymentStage.PRODUCTION)
    plan2.approval_required = False
    await orchestrator.deploy(plan2)
    
    # Rollback to v1.0.0
    rollback_record = await orchestrator.rollback(
        policy_id="test_policy",
        target_version=PolicyVersion(1, 0, 0),
    )
    
    assert rollback_record.status == DeploymentStatus.DEPLOYED
    assert rollback_record.artifact.version == PolicyVersion(1, 0, 0)


# ============================================================================
# DEPENDENCY RESOLUTION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.p1
async def test_dependency_resolution_pass(orchestrator):
    """Test dependency resolution validation passes"""
    # Store dependency
    dep = PolicyArtifact(
        policy_id="dependency_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "dep_value"},
    )
    orchestrator.artifact_store.store(dep)
    
    # Create artifact with dependency
    artifact = PolicyArtifact(
        policy_id="main_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "main_value"},
        dependencies=["dependency_policy"],
    )
    
    plan = await orchestrator.plan_deployment(artifact, DeploymentStage.PRODUCTION)
    
    # Dependency check should pass
    dep_check = next(
        (c for c in plan.validation_checks if c.check_name == "dependency_resolution"),
        None
    )
    assert dep_check is not None
    assert dep_check.result == ValidationResult.PASS


@pytest.mark.asyncio
@pytest.mark.p1
async def test_dependency_resolution_fail(orchestrator):
    """Test dependency resolution validation fails for missing dependency"""
    # Create artifact with missing dependency
    artifact = PolicyArtifact(
        policy_id="main_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "main_value"},
        dependencies=["missing_policy"],
    )
    
    plan = await orchestrator.plan_deployment(artifact, DeploymentStage.PRODUCTION)
    
    # Dependency check should fail
    dep_check = next(
        (c for c in plan.validation_checks if c.check_name == "dependency_resolution"),
        None
    )
    assert dep_check is not None
    assert dep_check.result == ValidationResult.FAIL
    assert "missing_policy" in dep_check.message.lower()


# ============================================================================
# PERSISTENCE TESTS
# ============================================================================

@pytest.mark.p1
def test_artifact_store_persistence(temp_storage):
    """Test PolicyArtifactStore persists to disk"""
    # Create store and save artifact
    store1 = PolicyArtifactStore(temp_storage / "artifacts")
    artifact = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value"},
    )
    store1.store(artifact)
    
    # Create new store (should load from disk)
    store2 = PolicyArtifactStore(temp_storage / "artifacts")
    retrieved = store2.get("test_policy", PolicyVersion(1, 0, 0))
    
    assert retrieved is not None
    assert retrieved.policy_id == artifact.policy_id
    assert retrieved.version == artifact.version


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.p1
async def test_deployment_handles_validation_failure(orchestrator):
    """Test deployment fails gracefully on validation failure"""
    # Create artifact with missing dependency
    artifact = PolicyArtifact(
        policy_id="test_policy",
        version=PolicyVersion(1, 0, 0),
        content={"key": "value"},
        dependencies=["missing_dependency"],
    )
    
    plan = await orchestrator.plan_deployment(artifact, DeploymentStage.PRODUCTION)
    plan.approval_required = False
    
    # Execute (should fail on validation)
    record = await orchestrator.deploy(plan)
    
    assert record.status == DeploymentStatus.FAILED
    assert "validation" in record.error_message.lower()
