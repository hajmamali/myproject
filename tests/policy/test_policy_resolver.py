#!/usr/bin/env python3
"""
Policy Resolver Tests - Comprehensive Test Suite
=================================================

Tests for centralized policy resolution engine.

Test Categories:
1. Policy Resolution - Core functionality
2. View Mode Enforcement - Active vs Historical vs Mixed
3. Profile Integration - DESKTOP_MINIMAL vs ENTERPRISE_FULL
4. Security Controls - Authorization and audit requirements
5. Audit Trail - Policy decision logging
6. Edge Cases - Error handling and validation

Version: 1.0.0
Phase: Hard Policy Enforcement - Test Coverage
"""

import pytest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import Mock, MagicMock

from mahoun.core.policy_resolver import (
    PolicyResolver,
    ExecutionPolicy,
    ViewMode,
    EmbeddingMode,
    ReasoningBudget,
    create_default_policy_resolver,
    PolicyDecisionAuditEntry,
)


# ============================================================================
# Mock Fixtures
# ============================================================================

@dataclass
class MockResourceLimits:
    """Mock resource limits"""
    max_memory_gb: float = 4.0
    max_cpu_cores: int = 4
    max_concurrent_requests: int = 10
    max_storage_gb: float = 100.0
    max_graph_nodes: int = 100000
    max_model_size_gb: float = 3.0
    enable_gpu: bool = False


@dataclass
class MockPerformanceTargets:
    """Mock performance targets"""
    target_latency_ms: int = 200
    target_throughput_rps: int = 10
    target_memory_utilization: float = 0.7


@dataclass
class MockDeploymentProfile:
    """Mock deployment profile"""
    profile_name: str = "desktop_minimal"
    resource_limits: MockResourceLimits = None
    performance_targets: MockPerformanceTargets = None
    
    def __post_init__(self):
        if self.resource_limits is None:
            self.resource_limits = MockResourceLimits()
        if self.performance_targets is None:
            self.performance_targets = MockPerformanceTargets()


@dataclass
class MockGovernanceContext:
    """Mock governance context"""
    correlation_id: str = "test-correlation-id"
    actor_id: str = "test-actor"
    context_id: str = "test-context-id"
    execution_mode: str = "test"


class MockProfileManager:
    """Mock profile manager"""
    
    def __init__(self, profile: Optional[MockDeploymentProfile] = None):
        if profile is None:
            profile = MockDeploymentProfile()
        self.profile = profile


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def desktop_minimal_profile():
    """Desktop minimal profile"""
    return MockDeploymentProfile(
        profile_name="desktop_minimal",
        resource_limits=MockResourceLimits(
            max_memory_gb=4.0,
            max_cpu_cores=4,
            max_concurrent_requests=10,
            max_model_size_gb=3.0,
            enable_gpu=False
        ),
        performance_targets=MockPerformanceTargets(
            target_latency_ms=200,
            target_throughput_rps=10
        )
    )


@pytest.fixture
def enterprise_full_profile():
    """Enterprise full profile"""
    return MockDeploymentProfile(
        profile_name="enterprise_full",
        resource_limits=MockResourceLimits(
            max_memory_gb=32.0,
            max_cpu_cores=16,
            max_concurrent_requests=1000,
            max_model_size_gb=70.0,
            enable_gpu=True
        ),
        performance_targets=MockPerformanceTargets(
            target_latency_ms=100,
            target_throughput_rps=1000
        )
    )


@pytest.fixture
def governance_context():
    """Standard governance context"""
    return MockGovernanceContext()


@pytest.fixture
def policy_resolver_desktop(desktop_minimal_profile):
    """Policy resolver with desktop minimal profile"""
    profile_manager = MockProfileManager(desktop_minimal_profile)
    return PolicyResolver(profile_manager=profile_manager)


@pytest.fixture
def policy_resolver_enterprise(enterprise_full_profile):
    """Policy resolver with enterprise full profile"""
    profile_manager = MockProfileManager(enterprise_full_profile)
    return PolicyResolver(profile_manager=profile_manager)


# ============================================================================
# Test Suite 1: Policy Resolution - Core Functionality
# ============================================================================

class TestPolicyResolutionCore:
    """Test core policy resolution functionality"""
    
    @pytest.mark.p2
    def test_default_policy_is_active_view(self, policy_resolver_desktop, governance_context):
        """Default policy should use ACTIVE_VIEW (safe default)"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        assert policy.view_mode == ViewMode.ACTIVE_VIEW
        assert policy.allow_tombstones is False
        assert policy.correlation_id == governance_context.correlation_id
    
    @pytest.mark.p2
    def test_policy_has_unique_id(self, policy_resolver_desktop, governance_context):
        """Each policy resolution should have unique ID"""
        policy1 = policy_resolver_desktop.resolve_policy(governance_context)
        policy2 = policy_resolver_desktop.resolve_policy(governance_context)
        
        # IDs should be different due to different timestamps
        assert policy1.policy_id != policy2.policy_id
    
    @pytest.mark.p2
    def test_policy_is_immutable(self, policy_resolver_desktop, governance_context):
        """ExecutionPolicy should be immutable (frozen dataclass)"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            policy.view_mode = ViewMode.HISTORICAL_VIEW
    
    @pytest.mark.p2
    def test_policy_includes_profile_name(self, policy_resolver_desktop, governance_context):
        """Policy should include profile name"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        assert policy.profile_name == "desktop_minimal"
    
    @pytest.mark.p2
    def test_policy_includes_resolved_timestamp(self, policy_resolver_desktop, governance_context):
        """Policy should include resolved timestamp"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        assert policy.resolved_at
        assert "T" in policy.resolved_at  # ISO format


# ============================================================================
# Test Suite 2: View Mode Enforcement
# ============================================================================

class TestViewModeEnforcement:
    """Test view mode enforcement rules"""
    
    @pytest.mark.p2
    def test_active_view_blocks_tombstones(self, policy_resolver_desktop, governance_context):
        """ACTIVE_VIEW must block tombstones"""
        policy = policy_resolver_desktop.resolve_policy(
            governance_context,
            view_mode=ViewMode.ACTIVE_VIEW
        )
        
        assert policy.view_mode == ViewMode.ACTIVE_VIEW
        assert policy.allow_tombstones is False
    
    @pytest.mark.p2
    def test_historical_view_allows_tombstones(self, policy_resolver_desktop, governance_context):
        """HISTORICAL_VIEW must allow tombstones"""
        policy = policy_resolver_desktop.resolve_policy(
            governance_context,
            view_mode=ViewMode.HISTORICAL_VIEW,
            audit_justification="Forensic analysis of case #12345"
        )
        
        assert policy.view_mode == ViewMode.HISTORICAL_VIEW
        assert policy.allow_tombstones is True
    
    @pytest.mark.p2
    def test_historical_view_requires_justification(self, policy_resolver_desktop, governance_context):
        """HISTORICAL_VIEW without justification should raise error"""
        with pytest.raises(ValueError, match="requires explicit audit_justification"):
            policy_resolver_desktop.resolve_policy(
                governance_context,
                view_mode=ViewMode.HISTORICAL_VIEW
            )
    
    @pytest.mark.p2
    def test_mixed_view_requires_justification(self, policy_resolver_desktop, governance_context):
        """MIXED_VIEW without justification should raise error"""
        with pytest.raises(ValueError, match="requires explicit audit_justification"):
            policy_resolver_desktop.resolve_policy(
                governance_context,
                view_mode=ViewMode.MIXED_VIEW
            )
    
    @pytest.mark.p2
    def test_mixed_view_default_no_tombstones(self, policy_resolver_desktop, governance_context):
        """MIXED_VIEW should default to no tombstones for safety"""
        policy = policy_resolver_desktop.resolve_policy(
            governance_context,
            view_mode=ViewMode.MIXED_VIEW,
            audit_justification="Data migration testing"
        )
        
        assert policy.view_mode == ViewMode.MIXED_VIEW
        assert policy.allow_tombstones is False  # Safe default


# ============================================================================
# Test Suite 3: Profile Integration
# ============================================================================

class TestProfileIntegration:
    """Test integration with deployment profiles"""
    
    @pytest.mark.p2
    def test_desktop_minimal_uses_conservative_depth(self, policy_resolver_desktop, governance_context):
        """Desktop minimal should use conservative graph depth"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        assert policy.max_graph_depth == 3  # Conservative
        assert policy.profile_name == "desktop_minimal"
    
    @pytest.mark.p2
    def test_enterprise_full_uses_deep_depth(self, policy_resolver_enterprise, governance_context):
        """Enterprise full should use deep graph depth"""
        policy = policy_resolver_enterprise.resolve_policy(governance_context)
        
        assert policy.max_graph_depth == 10  # Full capabilities
        assert policy.profile_name == "enterprise_full"
    
    @pytest.mark.p2
    def test_desktop_minimal_disables_semantic_search(self, policy_resolver_desktop, governance_context):
        """Desktop minimal should disable semantic search by default"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        assert policy.semantic_enabled is False
        assert policy.embedding_mode == EmbeddingMode.LIGHT
        assert policy.reasoning_budget == ReasoningBudget.LOW
    
    @pytest.mark.p2
    def test_enterprise_full_enables_semantic_search(self, policy_resolver_enterprise, governance_context):
        """Enterprise full should enable semantic search"""
        policy = policy_resolver_enterprise.resolve_policy(governance_context)
        
        assert policy.semantic_enabled is True
        assert policy.embedding_mode == EmbeddingMode.FULL
        assert policy.reasoning_budget == ReasoningBudget.HIGH
    
    @pytest.mark.p2
    def test_explicit_depth_override(self, policy_resolver_desktop, governance_context):
        """Explicit depth limit should override profile default"""
        policy = policy_resolver_desktop.resolve_policy(
            governance_context,
            explicit_depth_limit=7
        )
        
        assert policy.max_graph_depth == 7  # Overridden
    
    @pytest.mark.p2
    def test_semantic_override(self, policy_resolver_desktop, governance_context):
        """Semantic override should work"""
        policy = policy_resolver_desktop.resolve_policy(
            governance_context,
            semantic_override=True
        )
        
        assert policy.semantic_enabled is True  # Overridden from False


# ============================================================================
# Test Suite 4: Security Controls
# ============================================================================

class TestSecurityControls:
    """Test security and authorization controls"""
    
    @pytest.mark.p2
    def test_policy_includes_actor_id(self, policy_resolver_desktop, governance_context):
        """Policy should include actor ID for accountability"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        assert policy.actor_id == "test-actor"
    
    @pytest.mark.p2
    def test_safe_default_check(self, policy_resolver_desktop, governance_context):
        """Default policy should pass safe default check"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        assert policy.is_safe_default() is True
    
    @pytest.mark.p2
    def test_historical_view_not_safe_default(self, policy_resolver_desktop, governance_context):
        """HISTORICAL_VIEW should not be safe default"""
        policy = policy_resolver_desktop.resolve_policy(
            governance_context,
            view_mode=ViewMode.HISTORICAL_VIEW,
            audit_justification="Audit"
        )
        
        assert policy.is_safe_default() is False
    
    @pytest.mark.p2
    def test_policy_consistency_validation(self, policy_resolver_desktop, governance_context):
        """Policy should validate consistency rules"""
        # This should work (consistent)
        policy = policy_resolver_desktop.resolve_policy(
            governance_context,
            view_mode=ViewMode.ACTIVE_VIEW
        )
        assert policy.view_mode == ViewMode.ACTIVE_VIEW
        assert policy.allow_tombstones is False


# ============================================================================
# Test Suite 5: Audit Trail
# ============================================================================

class TestAuditTrail:
    """Test policy decision audit trail"""
    
    @pytest.mark.p2
    def test_audit_trail_is_recorded(self, policy_resolver_desktop, governance_context):
        """Policy decisions should be audited"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        audit_trail = policy_resolver_desktop.get_audit_trail()
        assert len(audit_trail) > 0
        assert audit_trail[0].policy_id == policy.policy_id
    
    @pytest.mark.p2
    def test_audit_trail_includes_correlation_id(self, policy_resolver_desktop, governance_context):
        """Audit trail should include correlation ID"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        audit_trail = policy_resolver_desktop.get_audit_trail()
        assert audit_trail[0].correlation_id == governance_context.correlation_id
    
    @pytest.mark.p2
    def test_audit_trail_includes_justification(self, policy_resolver_desktop, governance_context):
        """Audit trail should include justification"""
        policy = policy_resolver_desktop.resolve_policy(
            governance_context,
            view_mode=ViewMode.HISTORICAL_VIEW,
            audit_justification="Testing historical access"
        )
        
        audit_trail = policy_resolver_desktop.get_audit_trail()
        assert "Testing historical access" in audit_trail[0].justification
    
    @pytest.mark.p2
    def test_audit_trail_filter_by_correlation(self, policy_resolver_desktop):
        """Audit trail should be filterable by correlation ID"""
        ctx1 = MockGovernanceContext(correlation_id="correlation-1")
        ctx2 = MockGovernanceContext(correlation_id="correlation-2")
        
        policy_resolver_desktop.resolve_policy(ctx1)
        policy_resolver_desktop.resolve_policy(ctx2)
        
        trail_ctx1 = policy_resolver_desktop.get_audit_trail(correlation_id="correlation-1")
        trail_ctx2 = policy_resolver_desktop.get_audit_trail(correlation_id="correlation-2")
        
        assert len(trail_ctx1) == 1
        assert len(trail_ctx2) == 1
        assert trail_ctx1[0].correlation_id == "correlation-1"
        assert trail_ctx2[0].correlation_id == "correlation-2"
    
    @pytest.mark.p2
    def test_policy_statistics(self, policy_resolver_desktop, governance_context):
        """Policy statistics should be available"""
        # Generate some policies
        policy_resolver_desktop.resolve_policy(governance_context)
        policy_resolver_desktop.resolve_policy(
            governance_context,
            view_mode=ViewMode.HISTORICAL_VIEW,
            audit_justification="Test"
        )
        
        stats = policy_resolver_desktop.get_policy_statistics()
        
        assert stats["total_policies"] == 2
        assert "by_view_mode" in stats
        assert "active" in stats["by_view_mode"]
        assert "historical" in stats["by_view_mode"]


# ============================================================================
# Test Suite 6: Edge Cases and Error Handling
# ============================================================================

class TestEdgeCasesAndErrors:
    """Test edge cases and error handling"""
    
    @pytest.mark.p2
    def test_invalid_graph_depth_raises_error(self, policy_resolver_desktop, governance_context):
        """Invalid graph depth should raise error"""
        # Note: Policy validation happens in ExecutionPolicy.__post_init__
        # We test that invalid depth is caught
        with pytest.raises(ValueError):
            policy = policy_resolver_desktop.resolve_policy(
                governance_context,
                explicit_depth_limit=0  # Invalid
            )
    
    @pytest.mark.p2
    def test_policy_to_dict_serialization(self, policy_resolver_desktop, governance_context):
        """Policy should be serializable to dict"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        policy_dict = policy.to_dict()
        
        assert isinstance(policy_dict, dict)
        assert policy_dict["policy_id"] == policy.policy_id
        assert policy_dict["view_mode"] == "active"
        assert policy_dict["profile_name"] == "desktop_minimal"
    
    @pytest.mark.p2
    def test_audit_entry_serialization(self, policy_resolver_desktop, governance_context):
        """Audit entries should be serializable"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        audit_trail = policy_resolver_desktop.get_audit_trail()
        audit_dict = audit_trail[0].to_dict()
        
        assert isinstance(audit_dict, dict)
        assert audit_dict["policy_id"] == policy.policy_id
    
    @pytest.mark.p2
    def test_policy_helpers_laptop_mode(self, policy_resolver_desktop, governance_context):
        """Policy helper methods should work"""
        policy = policy_resolver_desktop.resolve_policy(governance_context)
        
        assert policy.is_laptop_mode() is True
        assert policy.is_enterprise_mode() is False
    
    @pytest.mark.p2
    def test_policy_helpers_enterprise_mode(self, policy_resolver_enterprise, governance_context):
        """Policy helper methods should work for enterprise"""
        policy = policy_resolver_enterprise.resolve_policy(governance_context)
        
        assert policy.is_laptop_mode() is False
        assert policy.is_enterprise_mode() is True
    
    @pytest.mark.p2
    def test_audit_trail_limit(self, policy_resolver_desktop, governance_context):
        """Audit trail should respect limit parameter"""
        # Generate many policies
        for i in range(10):
            ctx = MockGovernanceContext(correlation_id=f"correlation-{i}")
            policy_resolver_desktop.resolve_policy(ctx)
        
        trail = policy_resolver_desktop.get_audit_trail(limit=5)
        assert len(trail) == 5


# ============================================================================
# Test Suite 7: Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.p2
    def test_create_default_resolver_works(self):
        """create_default_policy_resolver() should work"""
        # This will auto-detect profile
        # We can't test actual values without knowing system specs
        # But we can test that it doesn't crash
        try:
            resolver = create_default_policy_resolver()
            assert resolver is not None
            assert isinstance(resolver, PolicyResolver)
        except ImportError:
            # May fail if ProfileManager dependencies not available
            pytest.skip("ProfileManager dependencies not available")
    
    @pytest.mark.p2
    def test_multiple_resolvers_independent(self, desktop_minimal_profile, enterprise_full_profile):
        """Multiple resolvers should be independent"""
        resolver1 = PolicyResolver(MockProfileManager(desktop_minimal_profile))
        resolver2 = PolicyResolver(MockProfileManager(enterprise_full_profile))
        
        ctx = MockGovernanceContext()
        
        policy1 = resolver1.resolve_policy(ctx)
        policy2 = resolver2.resolve_policy(ctx)
        
        assert policy1.profile_name == "desktop_minimal"
        assert policy2.profile_name == "enterprise_full"
        assert policy1.max_graph_depth != policy2.max_graph_depth


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
