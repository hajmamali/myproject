#!/usr/bin/env python3
"""
Unified Governance Controller Tests
====================================

Comprehensive test suite for UnifiedGovernanceController integration.

Test Coverage:
--------------
1. Two-layer coordination (Kernel + Policy)
2. Query transformation (tombstone filtering, depth limits)
3. View mode enforcement (ACTIVE_VIEW vs HISTORICAL_VIEW)
4. Profile integration (DESKTOP_MINIMAL vs ENTERPRISE_FULL)
5. Audit trail generation
6. Security checks (mutation authorization, forbidden queries)
7. Edge cases and error handling

Author: MAHOUN Test Engineering Team
Date: 2026-06-18
"""

import pytest
from mahoun.ai.profile_manager import ProfileManager
from mahoun.core.governance.governance_context import GovernanceContext, GovernanceContextManager
from mahoun.core.governance_kernel.kernel import QueryType, set_governance_authority, reset_governance_authority
from mahoun.core.policy_resolver import PolicyResolver, ViewMode, ExecutionPolicy
from mahoun.core.unified_governance import (
    UnifiedGovernanceController,
    UnifiedGovernanceDecision,
    create_default_unified_controller,
    validate_query_with_unified_governance,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_profile_manager():
    """Create mock profile manager for testing."""
    # Use real ProfileManager instead of mock to avoid attribute issues
    manager = ProfileManager(auto_select=True)
    # Force desktop_minimal profile for testing
    if manager.profile.profile_name != "desktop_minimal":
        # If not desktop_minimal, create a desktop_minimal instance
        import os
        os.environ["MAHOUN_EXECUTION_MODE"] = "minimal"
        manager = ProfileManager(auto_select=True)
    return manager


@pytest.fixture
def policy_resolver(mock_profile_manager):
    """Create PolicyResolver instance."""
    return PolicyResolver(profile_manager=mock_profile_manager)


@pytest.fixture
def unified_controller(policy_resolver):
    """Create UnifiedGovernanceController instance."""
    return UnifiedGovernanceController(
        policy_resolver=policy_resolver,
        enable_query_transformation=True,
        enable_audit_logging=True,
        strict_mode=True
    )


@pytest.fixture
def governance_context():
    """Create test governance context."""
    return GovernanceContextManager.create_context(
        correlation_id="test-correlation-123",
        execution_mode="STRICT",
        actor_id="test_actor"
    )


# ============================================================================
# Test: Basic Coordination (Kernel + Policy)
# ============================================================================

def test_read_query_approved(unified_controller, governance_context):
    """Test that read queries are approved by both layers."""
    query = "MATCH (n:Law) WHERE n.status = 'active' RETURN n LIMIT 10"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # Assertions
    assert decision.approved is True
    assert decision.query_type == "READ"
    assert decision.kernel_check_passed is True
    assert decision.policy_check_passed is True
    assert decision.view_mode == "active"
    assert decision.allow_tombstones is False


def test_write_query_unauthorized(unified_controller, governance_context):
    """Test that write queries without authorization are denied."""
    query = "CREATE (n:Law {id: 'test'}) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # Assertions
    assert decision.approved is False
    assert decision.query_type == "WRITE"
    assert decision.kernel_check_passed is False
    assert "UNAUTHORIZED" in decision.kernel_message


def test_write_query_authorized(unified_controller, governance_context):
    """Test that write queries with authorization are approved."""
    query = "CREATE (n:Law {id: 'test'}) RETURN n"
    
    # Set authorization
    token = set_governance_authority(True)
    try:
        decision = unified_controller.prepare_query_execution(
            query=query,
            context=governance_context
        )
        
        # Assertions
        assert decision.approved is True
        assert decision.query_type == "WRITE"
        assert decision.kernel_check_passed is True
        assert decision.mutation_authorized is True
    finally:
        reset_governance_authority(token)


def test_forbidden_query_denied(unified_controller, governance_context):
    """Test that forbidden queries (apoc, dbms) are always denied."""
    query = "CALL apoc.periodic.iterate('MATCH (n) RETURN n', 'DELETE n', {})"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # Assertions
    assert decision.approved is False
    assert decision.query_type == "FORBIDDEN"
    assert decision.kernel_check_passed is False
    assert "FORBIDDEN" in decision.kernel_message


# ============================================================================
# Test: View Mode Enforcement
# ============================================================================

def test_active_view_default(unified_controller, governance_context):
    """Test that ACTIVE_VIEW is the default."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    assert decision.view_mode == "active"
    assert decision.allow_tombstones is False


def test_historical_view_requires_justification(unified_controller, governance_context):
    """Test that HISTORICAL_VIEW requires audit justification."""
    query = "MATCH (n:Law) RETURN n"
    
    # Without justification - should return denied decision (NOT raise)
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context,
        view_mode=ViewMode.HISTORICAL_VIEW
        # Missing: audit_justification
    )
    
    # Decision should be created but policy layer should fail
    assert decision.approved is False
    assert decision.policy_check_passed is False


def test_historical_view_with_justification(unified_controller, governance_context):
    """Test that HISTORICAL_VIEW works with proper justification."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context,
        view_mode=ViewMode.HISTORICAL_VIEW,
        audit_justification="Forensic analysis of case #12345"
    )
    
    # Policy layer should approve
    assert decision.policy_check_passed is True
    assert decision.view_mode == "historical"
    assert decision.allow_tombstones is True


# ============================================================================
# Test: Query Transformation
# ============================================================================

def test_tombstone_filter_injection_active_view(unified_controller, governance_context):
    """Test that tombstone filters are injected for ACTIVE_VIEW."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context,
        view_mode=ViewMode.ACTIVE_VIEW
    )
    
    # Transformation should occur
    assert decision.query_transformed is True
    assert "tombstone_filter_active_view" in decision.transformations_applied
    assert "_deleted IS NULL" in decision.transformed_query


def test_no_tombstone_filter_historical_view(unified_controller, governance_context):
    """Test that tombstone filters are NOT injected for HISTORICAL_VIEW."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context,
        view_mode=ViewMode.HISTORICAL_VIEW,
        audit_justification="Forensic analysis"
    )
    
    # No tombstone transformation for HISTORICAL_VIEW
    transformations = decision.transformations_applied
    assert "tombstone_filter_active_view" not in transformations


def test_depth_limiting_transformation(unified_controller, governance_context):
    """Test that depth limits are applied based on profile."""
    query = "MATCH path = (a)-[:*]-(b) RETURN path"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # Desktop minimal profile should have depth limit 3
    assert decision.policy.max_graph_depth == 3
    
    # Check if depth transformation was applied
    if "[:*]" in query:
        assert decision.query_transformed is True
        assert any("depth_limit" in t for t in decision.transformations_applied)
        assert "[:*1..3]" in decision.transformed_query


def test_limit_injection(unified_controller, governance_context):
    """Test that LIMIT is injected when missing."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # LIMIT should be added
    assert "LIMIT" in decision.transformed_query.upper()
    assert any("default_limit" in t for t in decision.transformations_applied)


def test_no_transformation_when_disabled(policy_resolver, governance_context):
    """Test that transformation can be disabled."""
    controller = UnifiedGovernanceController(
        policy_resolver=policy_resolver,
        enable_query_transformation=False
    )
    
    query = "MATCH (n:Law) RETURN n"
    
    decision = controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # No transformation should occur
    assert decision.query_transformed is False
    assert len(decision.transformations_applied) == 0
    assert decision.original_query == decision.transformed_query


# ============================================================================
# Test: Profile Integration
# ============================================================================

def test_desktop_minimal_constraints(unified_controller, governance_context):
    """Test that DESKTOP_MINIMAL profile applies conservative constraints."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    policy = decision.policy
    assert policy.profile_name == "desktop_minimal"
    assert policy.max_graph_depth == 3
    assert policy.semantic_enabled is False
    assert policy.embedding_mode.value == "light"
    assert policy.reasoning_budget.value == "low"


def test_enterprise_full_capabilities(governance_context):
    """Test that ENTERPRISE_FULL profile enables full capabilities."""
    # This test validates that when profile_name is enterprise_full,
    # the PolicyResolver correctly maps it to full capabilities.
    # 
    # Since we're on laptop (desktop_minimal), we mock the profile to simulate enterprise.
    
    from unittest.mock import MagicMock
    
    # Create a mock profile that simulates ENTERPRISE_FULL
    mock_profile_manager = MagicMock()
    mock_profile_manager.profile = MagicMock()
    mock_profile_manager.profile.profile_name = "enterprise_full"
    mock_profile_manager.profile.resource_limits = MagicMock(
        max_concurrent_requests=1000,
        max_model_size_gb=32,
        enable_gpu=True
    )
    mock_profile_manager.profile.performance_targets = MagicMock(
        target_latency_ms=100,
        target_throughput_rps=100
    )
    
    policy_resolver = PolicyResolver(profile_manager=mock_profile_manager)
    controller = UnifiedGovernanceController(policy_resolver=policy_resolver)
    
    query = "MATCH (n:Law) RETURN n"
    
    decision = controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    policy = decision.policy
    assert policy.profile_name == "enterprise_full"
    assert policy.max_graph_depth == 10
    assert policy.semantic_enabled is True
    assert policy.embedding_mode.value == "full"
    assert policy.reasoning_budget.value == "high"


# ============================================================================
# Test: Audit Trail
# ============================================================================

def test_audit_trail_creation(unified_controller, governance_context):
    """Test that audit trail is created for every decision."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # Check audit trail
    audit_trail = unified_controller.get_audit_trail(
        correlation_id=governance_context.correlation_id
    )
    
    assert len(audit_trail) > 0
    assert audit_trail[0].decision_id == decision.decision_id
    assert audit_trail[0].correlation_id == governance_context.correlation_id


def test_audit_trail_filtering(unified_controller, governance_context):
    """Test audit trail filtering capabilities."""
    # Execute multiple queries
    for i in range(5):
        query = f"MATCH (n:Law) WHERE n.id = '{i}' RETURN n"
        unified_controller.prepare_query_execution(query, governance_context)
    
    # Get audit trail
    trail = unified_controller.get_audit_trail(
        correlation_id=governance_context.correlation_id,
        limit=3
    )
    
    assert len(trail) <= 3


def test_statistics_generation(unified_controller, governance_context):
    """Test statistics generation from audit trail."""
    # Execute various queries
    queries = [
        "MATCH (n:Law) RETURN n",  # READ
        "CREATE (n:Law {id: 'test'}) RETURN n",  # WRITE (unauthorized)
        "MATCH (n:Verdict) RETURN n",  # READ
    ]
    
    for query in queries:
        unified_controller.prepare_query_execution(query, governance_context)
    
    stats = unified_controller.get_statistics()
    
    assert stats["total_decisions"] == 3
    assert "by_query_type" in stats
    assert "by_view_mode" in stats
    assert "transformation_stats" in stats


# ============================================================================
# Test: Utility Functions
# ============================================================================

def test_create_default_unified_controller():
    """Test default controller creation."""
    controller = create_default_unified_controller()
    
    assert isinstance(controller, UnifiedGovernanceController)
    assert controller.enable_query_transformation is True
    assert controller.enable_audit_logging is True
    assert controller.strict_mode is True


def test_validate_query_convenience_function(governance_context):
    """Test validate_query_with_unified_governance convenience function."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = validate_query_with_unified_governance(
        query=query,
        context=governance_context
    )
    
    assert isinstance(decision, UnifiedGovernanceDecision)
    assert decision.approved is True


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_empty_query(unified_controller, governance_context):
    """Test handling of empty query - MUST be READ (safe default)."""
    query = ""
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # Empty query MUST be treated as READ (safe default, not flaky)
    assert decision.query_type == "READ"
    assert decision.approved is True
    assert decision.kernel_check_passed is True


def test_complex_query_with_multiple_clauses(unified_controller, governance_context):
    """Test complex query with multiple MATCH clauses."""
    query = """
    MATCH (a:Law)
    WHERE a.status = 'active'
    MATCH (b:Verdict)
    WHERE b.court_level = 'Supreme'
    MATCH path = (a)-[:CITES*1..5]->(b)
    RETURN path
    """
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    assert decision.approved is True
    assert decision.query_type == "READ"
    
    # Check transformations
    assert decision.query_transformed is True


def test_decision_helper_methods(unified_controller, governance_context):
    """Test UnifiedGovernanceDecision helper methods."""
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # Test helper methods
    assert decision.is_safe_read() is True
    assert decision.requires_elevated_privileges() is False
    
    # Test serialization
    decision_dict = decision.to_dict()
    assert "decision_id" in decision_dict
    assert "policy" in decision_dict
    assert "approved" in decision_dict


def test_concurrent_decisions_isolated(unified_controller):
    """Test that concurrent decisions are properly isolated."""
    # Create two different contexts
    ctx1 = GovernanceContextManager.create_context(correlation_id="ctx-1")
    ctx2 = GovernanceContextManager.create_context(correlation_id="ctx-2")
    
    query = "MATCH (n:Law) RETURN n"
    
    decision1 = unified_controller.prepare_query_execution(query, ctx1)
    decision2 = unified_controller.prepare_query_execution(query, ctx2)
    
    # Decisions should be independent
    assert decision1.correlation_id != decision2.correlation_id
    assert decision1.decision_id != decision2.decision_id


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_policy_resolution_failure_handling(unified_controller, governance_context):
    """Test handling of policy resolution failures."""
    # Request HISTORICAL_VIEW without justification
    query = "MATCH (n:Law) RETURN n"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context,
        view_mode=ViewMode.HISTORICAL_VIEW
        # Missing audit_justification - will cause policy failure
    )
    
    # Decision should be created but policy_check_passed should be False
    assert decision.policy_check_passed is False
    assert decision.approved is False


# ============================================================================
# Test: Integration Scenarios
# ============================================================================

def test_production_reasoning_workflow(unified_controller, governance_context):
    """Test typical production reasoning workflow."""
    # Scenario: Legal reasoning query in production
    query = """
    MATCH (law:Law)-[:APPLIES_TO]->(case:Case)
    WHERE law.status = 'active' 
    AND case.id = $case_id
    MATCH path = (law)-[:CITES*1..3]->(precedent:Verdict)
    WHERE precedent.authority_score > 0.7
    RETURN law, path, precedent
    ORDER BY precedent.authority_score DESC
    """
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context,
        view_mode=ViewMode.ACTIVE_VIEW
    )
    
    # Should be approved with transformations
    assert decision.approved is True
    assert decision.view_mode == "active"
    assert decision.query_transformed is True
    
    # Should have tombstone filters
    assert "_deleted IS NULL" in decision.transformed_query


def test_forensic_audit_workflow(unified_controller, governance_context):
    """Test forensic audit workflow with HISTORICAL_VIEW."""
    # Scenario: Forensic analysis needs to see deleted entities
    query = """
    MATCH (law:Law)
    WHERE law.id = $law_id
    RETURN law, law._deleted, law._deleted_at
    """
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context,
        view_mode=ViewMode.HISTORICAL_VIEW,
        audit_justification="Legal audit for case #54321 - investigating document history"
    )
    
    # Should be approved for HISTORICAL_VIEW
    assert decision.approved is True
    assert decision.view_mode == "historical"
    assert decision.allow_tombstones is True
    
    # Should NOT have tombstone filters
    transformations = decision.transformations_applied
    assert "tombstone_filter_active_view" not in transformations


def test_laptop_performance_mode(unified_controller, governance_context):
    """Test laptop mode with conservative resource limits."""
    query = "MATCH path = (a)-[:*]-(b) RETURN path"
    
    decision = unified_controller.prepare_query_execution(
        query=query,
        context=governance_context
    )
    
    # Laptop mode should have strict limits
    assert decision.policy.max_graph_depth == 3
    assert decision.policy.profile_name == "desktop_minimal"
    
    # Depth should be limited in transformed query
    assert "[:*1..3]" in decision.transformed_query


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
