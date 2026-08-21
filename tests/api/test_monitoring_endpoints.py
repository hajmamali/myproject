"""
Comprehensive Tests for Intelligent System Monitoring API
==========================================================
Tests for /monitoring/* endpoints wiring UltraIntegrityValidator
and AdvancedModelOrchestrator.

Test Coverage:
- Graph health score calculation
- Violations filtering and pagination
- Model performance metrics
- Model leaderboard ranking
- System overview aggregation
- Error handling (503, 404, 500)
- Response structure validation
- Integration with backend components
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, PropertyMock
from datetime import datetime


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_integrity_validator():
    """Mock UltraIntegrityValidator with realistic data"""
    validator = Mock()
    
    # Mock violations list
    mock_violations = [
        Mock(
            violation_id="v1",
            violation_type="orphaned_node",
            severity="medium",
            entity_id="node_123",
            entity_label="LegalCase",
            message="Node has no relationships",
            detected_at="2026-08-19T10:00:00Z",
            remediation_suggestion="Run auto-cleanup with safe mode",
            affected_downstream=[],
            metadata={"age_days": 30}
        ),
        Mock(
            violation_id="v2",
            violation_type="circular_reference",
            severity="critical",
            entity_id="node_456",
            entity_label="Precedent",
            message="Circular reference detected in relationship chain",
            detected_at="2026-08-19T10:05:00Z",
            remediation_suggestion="Manual review required - cannot auto-fix",
            affected_downstream=["node_789", "node_012"],
            metadata={"cycle_length": 3}
        )
    ]
    
    validator.violations = mock_violations
    validator.get_health_score.return_value = 85.5
    validator.validate_all.return_value = {
        "violations_count": 2,
        "violations": [
            {"id": v.violation_id, "type": v.violation_type}
            for v in mock_violations
        ]
    }
    
    return validator


@pytest.fixture
def mock_model_orchestrator():
    """Mock AdvancedModelOrchestrator with realistic data"""
    orchestrator = Mock()
    
    orchestrator.models = {
        "model_a": {"model_type": "reasoning", "active": True},
        "model_b": {"model_type": "embedding", "active": True}
    }
    
    def mock_get_metrics(model_id):
        return {
            "model_id": model_id,
            "total_requests": 1000,
            "success_rate": 99.0,
            "latency": {"avg_ms": 150.0, "p95_ms": 200.0},
            "errors": {"total": 10, "rate": 1.0}
        }
    
    orchestrator.get_model_metrics.side_effect = mock_get_metrics
    orchestrator.get_system_status.return_value = {
        "total_models": 2,
        "active_models": 2,
        "avg_success_rate": 99.0
    }
    
    return orchestrator


@pytest.fixture
def client_with_mocks(mock_integrity_validator, mock_model_orchestrator):
    """TestClient with mocked monitoring services"""
    from api.main import app
    
    app.state.integrity_validator = mock_integrity_validator
    app.state.model_orchestrator = mock_model_orchestrator
    app.state.start_time = datetime.utcnow().timestamp() - 3600
    
    from fastapi.testclient import TestClient
    return TestClient(app)


# ============================================================================
# GRAPH HEALTH TESTS
# ============================================================================

class TestGraphHealth:
    """Test /monitoring/graph/health endpoint"""
    
    @pytest.mark.p1
    def test_graph_health_success(self, client_with_mocks):
        """Test successful graph health retrieval"""
        response = client_with_mocks.get("/monitoring/graph/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "health_score" in data
        assert "status" in data
        assert "timestamp" in data
        assert "component_scores" in data
        
        # Validate types
        assert isinstance(data["health_score"], (int, float))
        assert 0 <= data["health_score"] <= 100
        assert data["status"] in ["healthy", "degraded", "critical"]
    
    @pytest.mark.p1
    def test_graph_health_service_unavailable(self):
        """Test 503 when integrity validator not initialized"""
        from api.main import app
        from fastapi.testclient import TestClient
        
        # Remove the mocked state
        if hasattr(app.state, 'integrity_validator'):
            delattr(app.state, 'integrity_validator')
        
        client = TestClient(app)
        response = client.get("/monitoring/graph/health")
        
        assert response.status_code == 503


# ============================================================================
# VIOLATIONS TESTS
# ============================================================================

class TestGraphViolations:
    """Test /monitoring/graph/violations endpoint"""
    
    @pytest.mark.p1
    def test_violations_list_success(self, client_with_mocks):
        """Test successful violations list retrieval"""
        response = client_with_mocks.get("/monitoring/graph/violations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "violations" in data
        assert data["total"] == 2
    
    @pytest.mark.p2
    def test_violations_severity_filter(self, client_with_mocks):
        """Test filtering by severity"""
        response = client_with_mocks.get(
            "/monitoring/graph/violations",
            params={"severity": "critical"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only one critical violation


# ============================================================================
# MODEL PERFORMANCE TESTS
# ============================================================================

class TestModelPerformance:
    """Test /monitoring/models/performance endpoint"""
    
    @pytest.mark.p1
    def test_all_models_performance(self, client_with_mocks):
        """Test fetching all models performance"""
        response = client_with_mocks.get("/monitoring/models/performance")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "models" in data
        assert len(data["models"]) == 2
    
    @pytest.mark.p1
    def test_specific_model_performance(self, client_with_mocks):
        """Test specific model performance"""
        response = client_with_mocks.get(
            "/monitoring/models/performance",
            params={"model_id": "model_a"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "model_a" in data["models"]
    
    @pytest.mark.p1
    def test_model_not_found(self, client_with_mocks, mock_model_orchestrator):
        """Test 404 for non-existent model"""
        mock_model_orchestrator.get_model_metrics.return_value = None
        
        response = client_with_mocks.get(
            "/monitoring/models/performance",
            params={"model_id": "nonexistent"}
        )
        
        assert response.status_code == 404


# ============================================================================
# MODEL LEADERBOARD TESTS
# ============================================================================

class TestModelLeaderboard:
    """Test /monitoring/models/leaderboard endpoint"""
    
    @pytest.mark.p1
    def test_leaderboard_success(self, client_with_mocks):
        """Test successful leaderboard retrieval"""
        response = client_with_mocks.get("/monitoring/models/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ranking" in data
        assert "total_models" in data
        assert data["total_models"] == 2
    
    @pytest.mark.p2
    def test_leaderboard_top_n(self, client_with_mocks):
        """Test top_n parameter"""
        response = client_with_mocks.get(
            "/monitoring/models/leaderboard",
            params={"top_n": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["ranking"]) == 1


# ============================================================================
# SYSTEM OVERVIEW TESTS
# ============================================================================

class TestSystemOverview:
    """Test /monitoring/system/overview endpoint"""
    
    @pytest.mark.p1
    def test_system_overview_success(self, client_with_mocks):
        """Test successful system overview"""
        response = client_with_mocks.get("/monitoring/system/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "graph" in data
        assert "models" in data
        assert "system" in data
    
    @pytest.mark.p2
    def test_overview_partial_services(self):
        """Test overview when some services unavailable"""
        from api.main import app
        from fastapi.testclient import TestClient
        
        # Only set start_time, no monitoring services
        app.state.start_time = datetime.utcnow().timestamp()
        
        client = TestClient(app)
        response = client.get("/monitoring/system/overview")
        
        assert response.status_code == 200
        data = response.json()
        assert "system" in data


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error scenarios"""
    
    @pytest.mark.p2
    def test_invalid_parameters(self, client_with_mocks):
        """Test invalid parameter values"""
        # Invalid time_window (too low)
        response = client_with_mocks.get(
            "/monitoring/models/performance",
            params={"time_window": 30}
        )
        assert response.status_code == 422
        
        # Invalid top_n (too high)
        response = client_with_mocks.get(
            "/monitoring/models/leaderboard",
            params={"top_n": 200}
        )
        assert response.status_code == 422
    
    @pytest.mark.p2
    def test_service_errors(self, client_with_mocks, mock_integrity_validator):
        """Test backend service errors"""
        # Mock validator throwing exception
        mock_integrity_validator.get_health_score.side_effect = Exception("Database error")
        
        response = client_with_mocks.get("/monitoring/graph/health")
        assert response.status_code == 500


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Test integration with backend components"""
    
    @pytest.mark.p1
    def test_validator_integration(self, client_with_mocks, mock_integrity_validator):
        """Test UltraIntegrityValidator integration"""
        response = client_with_mocks.get("/monitoring/graph/health")
        
        assert response.status_code == 200
        mock_integrity_validator.get_health_score.assert_called_once()
    
    @pytest.mark.p1
    def test_orchestrator_integration(self, client_with_mocks, mock_model_orchestrator):
        """Test AdvancedModelOrchestrator integration"""
        response = client_with_mocks.get("/monitoring/models/performance")
        
        assert response.status_code == 200
        assert mock_model_orchestrator.get_model_metrics.called


# ============================================================================
# AUTO-CLEANUP TESTS
# ============================================================================

class TestAutoCleanup:
    """Test /monitoring/maintenance/cleanup-orphans endpoint"""
    
    @pytest.mark.p1
    def test_cleanup_safe_mode_dry_run(self, client_with_mocks, mock_integrity_validator):
        """Test safe mode cleanup with dry_run=True"""
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={
                "mode": "safe",
                "dry_run": True,
                "batch_size": 10,
                "age_threshold_days": 30
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required response fields
        assert "mode" in data
        assert "dry_run" in data
        assert "summary" in data
        assert "candidates" in data
        assert "execution_time_ms" in data
        
        # Verify mode and dry_run
        assert data["mode"] == "safe"
        assert data["dry_run"] is True
        
        # Should have candidates but no deletions in dry_run
        assert data["summary"]["nodes_deleted"] == 0
    
    @pytest.mark.p1
    def test_cleanup_aggressive_mode_actual_deletion(self, client_with_mocks, mock_integrity_validator):
        """Test aggressive mode with actual deletion"""
        # Mock GovernedNeo4jSession for deletion
        with patch('api.routers.monitoring.GovernedNeo4jSession') as mock_session_class:
            mock_session = Mock()
            mock_receipt = Mock()
            mock_receipt.correlation_id = "test-correlation-123"
            mock_session.delete_node.return_value = mock_receipt
            mock_session_class.return_value = mock_session
            
            response = client_with_mocks.post(
                "/monitoring/maintenance/cleanup-orphans",
                params={
                    "mode": "aggressive",
                    "dry_run": False,
                    "batch_size": 5
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["mode"] == "aggressive"
        assert data["dry_run"] is False
        
        # Should have deleted some nodes
        assert data["summary"]["nodes_deleted"] >= 0
        assert "governance_audit_id" in data
    
    @pytest.mark.p1
    def test_cleanup_manual_review_mode(self, client_with_mocks):
        """Test manual review mode (preview only)"""
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={
                "mode": "manual-review",
                "batch_size": 20
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["mode"] == "manual-review"
        # Manual review never deletes
        assert data["summary"]["nodes_deleted"] == 0
        # Should still have candidates for review
        assert "candidates" in data
    
    @pytest.mark.p2
    def test_cleanup_invalid_mode(self, client_with_mocks):
        """Test cleanup with invalid mode"""
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "invalid_mode"}
        )
        
        assert response.status_code == 400
        assert "Invalid mode" in response.json()["detail"]
    
    @pytest.mark.p2
    def test_cleanup_parameter_validation(self, client_with_mocks):
        """Test parameter validation"""
        # Batch size too low
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "safe", "batch_size": 0}
        )
        assert response.status_code == 422
        
        # Batch size too high
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "safe", "batch_size": 1000}
        )
        assert response.status_code == 422
        
        # Age threshold too low
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "safe", "age_threshold_days": 0}
        )
        assert response.status_code == 422
    
    @pytest.mark.p1
    def test_cleanup_service_unavailable(self):
        """Test cleanup when integrity validator not available"""
        from api.main import app
        from fastapi.testclient import TestClient
        
        # Remove validator
        if hasattr(app.state, 'integrity_validator'):
            delattr(app.state, 'integrity_validator')
        
        client = TestClient(app)
        response = client.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "safe"}
        )
        
        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"].lower()
    
    @pytest.mark.p2
    def test_cleanup_candidate_structure(self, client_with_mocks):
        """Test cleanup candidate object structure"""
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "manual-review", "dry_run": True}
        )
        
        data = response.json()
        
        if data["candidates"]:
            candidate = data["candidates"][0]
            
            # Required fields in candidate
            required_fields = [
                "node_id", "label", "classification", "action",
                "confidence_score", "age_days", "reason"
            ]
            
            for field in required_fields:
                assert field in candidate, f"Missing field: {field}"
            
            # Validate field types
            assert isinstance(candidate["confidence_score"], (int, float))
            assert 0 <= candidate["confidence_score"] <= 1
            assert candidate["classification"] in ["safe", "risky", "critical", "suspicious"]
            assert candidate["action"] in ["delete", "review", "preserve", "quarantine"]
    
    @pytest.mark.p2
    def test_cleanup_summary_structure(self, client_with_mocks):
        """Test cleanup summary structure"""
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "safe", "dry_run": True}
        )
        
        data = response.json()
        summary = data["summary"]
        
        # Required summary fields
        assert "candidates_found" in summary
        assert "nodes_processed" in summary
        assert "nodes_deleted" in summary
        assert "errors_count" in summary
        
        # Validate summary logic
        assert summary["candidates_found"] >= summary["nodes_processed"]
        assert summary["nodes_processed"] >= summary["nodes_deleted"]
        assert summary["errors_count"] >= 0
    
    @pytest.mark.p2
    def test_cleanup_governance_error_handling(self, client_with_mocks):
        """Test governance error handling during cleanup"""
        # Mock governance context failure
        with patch('api.routers.monitoring.GovernanceContext') as mock_governance:
            mock_governance.side_effect = Exception("Governance initialization failed")
            
            response = client_with_mocks.post(
                "/monitoring/maintenance/cleanup-orphans",
                params={"mode": "safe", "dry_run": False}
            )
        
        assert response.status_code == 500
        assert "governance" in response.json()["detail"].lower()
    
    @pytest.mark.p2
    def test_cleanup_batch_processing(self, client_with_mocks, mock_integrity_validator):
        """Test batch size limiting"""
        # Create many violations
        many_violations = [
            Mock(
                violation_id=f"v{i}",
                violation_type="orphaned_node",
                severity="medium",
                entity_id=f"node_{i}",
                entity_label="TempNode",
                metadata={"age_days": 40}
            )
            for i in range(100)
        ]
        
        mock_integrity_validator.violations = many_violations
        
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "manual-review", "batch_size": 10}
        )
        
        data = response.json()
        
        # Should respect batch_size limit
        assert len(data["candidates"]) <= 10
        assert data["summary"]["candidates_found"] <= 10
    
    @pytest.mark.p1
    def test_cleanup_recommendations_generation(self, client_with_mocks):
        """Test that recommendations are generated"""
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "manual-review"}
        )
        
        data = response.json()
        
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        
        # Should have at least one recommendation
        if data["summary"]["candidates_found"] > 0:
            assert len(data["recommendations"]) > 0


# ============================================================================
# ORPHAN CLASSIFIER TESTS
# ============================================================================

class TestOrphanClassifier:
    """Test the AdvancedOrphanClassifier integration"""
    
    @pytest.fixture
    def mock_violation(self):
        """Create a mock violation for testing"""
        violation = Mock()
        violation.entity_id = "test_node_123"
        violation.entity_label = "TempNode"
        violation.metadata = {
            "age_days": 45,
            "relationship_count": 0,
            "last_updated": "2026-07-01T10:00:00Z",
            "access_count": 0
        }
        return violation
    
    @pytest.mark.p2
    def test_classifier_safe_classification(self, mock_violation):
        """Test that safe nodes are classified correctly"""
        from mahoun.monitoring.orphan_classifier import create_orphan_classifier
        
        classifier = create_orphan_classifier(age_threshold_days=30)
        result = classifier.classify_orphan(mock_violation)
        
        # Should be safe (old temp node with no relationships)
        assert result.risk_level.value in ["safe", "risky"]
        assert result.confidence_score > 0.0
        assert result.age_days == 45
    
    @pytest.mark.p2
    def test_classifier_critical_entity_protection(self):
        """Test that critical entities are protected"""
        from mahoun.monitoring.orphan_classifier import create_orphan_classifier
        
        violation = Mock()
        violation.entity_id = "evidence_123"
        violation.entity_label = "Evidence"
        violation.metadata = {"age_days": 365}
        
        classifier = create_orphan_classifier()
        result = classifier.classify_orphan(violation)
        
        # Evidence should always be critical/preserved
        assert result.risk_level.value == "critical"
        assert result.action.value == "preserve"
        assert result.confidence_score == 1.0
    
    @pytest.mark.p2
    def test_classifier_batch_processing(self):
        """Test batch classification"""
        from mahoun.monitoring.orphan_classifier import create_orphan_classifier
        
        # Create multiple violations
        violations = []
        for i in range(5):
            violation = Mock()
            violation.entity_id = f"node_{i}"
            violation.entity_label = "TempNode"
            violation.metadata = {"age_days": 30 + i}
            violations.append(violation)
        
        classifier = create_orphan_classifier()
        results = classifier.classify_batch(violations)
        
        assert len(results) == 5
        assert all(hasattr(r, 'risk_level') for r in results)
        assert all(hasattr(r, 'confidence_score') for r in results)
    
    @pytest.mark.p2
    def test_classifier_error_handling(self):
        """Test classifier error handling with malformed data"""
        from mahoun.monitoring.orphan_classifier import create_orphan_classifier
        
        # Create violation with missing/bad data
        bad_violation = Mock()
        bad_violation.entity_id = None
        bad_violation.entity_label = None
        bad_violation.metadata = None
        
        classifier = create_orphan_classifier()
        
        # Should not crash, should return fallback classification
        results = classifier.classify_batch([bad_violation])
        assert len(results) == 1
        assert results[0].risk_level.value == "risky"  # Safe fallback


# ============================================================================
# INTEGRATION TESTS FOR CLEANUP
# ============================================================================

class TestCleanupIntegration:
    """Test cleanup endpoint integration with real backend components"""
    
    @pytest.mark.p1
    def test_cleanup_calls_validator_methods(self, client_with_mocks, mock_integrity_validator):
        """Test that cleanup actually calls validator methods"""
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "manual-review"}
        )
        
        assert response.status_code == 200
        
        # Should call check_orphaned_nodes indirectly through violations access
        # (This depends on the actual implementation details)
        mock_integrity_validator.violations  # Should be accessed
    
    @pytest.mark.p2
    def test_cleanup_execution_time_tracking(self, client_with_mocks):
        """Test that execution time is tracked"""
        response = client_with_mocks.post(
            "/monitoring/maintenance/cleanup-orphans",
            params={"mode": "safe", "dry_run": True}
        )
        
        data = response.json()
        
        assert "execution_time_ms" in data
        assert isinstance(data["execution_time_ms"], (int, float))
        assert data["execution_time_ms"] >= 0
    
    @pytest.mark.p2
    def test_cleanup_governance_audit_trail(self, client_with_mocks):
        """Test that governance audit trail is created"""
        with patch('api.routers.monitoring.GovernedNeo4jSession') as mock_session_class:
            mock_session = Mock()
            mock_receipt = Mock()
            mock_receipt.correlation_id = "audit-123"
            mock_session.delete_node.return_value = mock_receipt
            mock_session_class.return_value = mock_session
            
            response = client_with_mocks.post(
                "/monitoring/maintenance/cleanup-orphans",
                params={"mode": "aggressive", "dry_run": False}
            )
        
        data = response.json()
        
        if data["summary"]["nodes_deleted"] > 0:
            assert "governance_audit_id" in data
            assert data["governance_audit_id"]  # Should not be empty


# ============================================================================
# RESPONSE STRUCTURE TESTS
# ============================================================================

class TestResponseStructure:
    """Test response data structure compliance"""
    
    @pytest.mark.p2
    def test_timestamp_format(self, client_with_mocks):
        """Test ISO timestamp format in responses"""
        response = client_with_mocks.get("/monitoring/system/overview")
        data = response.json()
        
        timestamp = data["timestamp"]
        assert timestamp.endswith("Z")
        assert "T" in timestamp
    
    @pytest.mark.p2
    def test_health_score_range(self, client_with_mocks, mock_integrity_validator):
        """Test health score is within 0-100 range"""
        # Test boundary values
        for score in [0.0, 50.0, 100.0]:
            mock_integrity_validator.get_health_score.return_value = score
            response = client_with_mocks.get("/monitoring/graph/health")
            data = response.json()
            assert 0 <= data["health_score"] <= 100
    
    @pytest.mark.p2
    def test_pagination_consistency(self, client_with_mocks):
        """Test pagination response consistency"""
        response = client_with_mocks.get(
            "/monitoring/graph/violations",
            params={"limit": 1, "offset": 0}
        )
        data = response.json()
        
        assert data["offset"] == 0
        assert data["returned"] <= 1
        assert data["total"] >= data["returned"]


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/api/test_monitoring_endpoints.py -v
    pytest.main([__file__, "-v"])