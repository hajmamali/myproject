#!/usr/bin/env python3
"""
Simple validation test to verify our modules work
"""

def test_ultra_integrity_validator():
    """Test Ultra Integrity Validator basic functionality"""
    try:
        from mahoun.graph.validation.ultra_integrity_validator import UltraIntegrityValidator
        from mahoun.core.governance.governance_context import GovernanceContext
        from unittest.mock import Mock
        
        # Create mock governance context
        gov_ctx = Mock()
        gov_ctx.correlation_id = "test-123"
        gov_ctx.actor_id = "test-actor"
        
        # Create validator
        validator = UltraIntegrityValidator(gov_ctx)
        
        # Test basic properties
        assert validator.governance_context == gov_ctx
        assert validator.parallel_workers == 4
        assert len(validator.violations) == 0
        
        # Test violation ID generation
        vid1 = validator._generate_violation_id()
        vid2 = validator._generate_violation_id()
        
        assert vid1 != vid2
        assert vid1.startswith("VIO-")
        assert vid2.startswith("VIO-")
        
        print("✅ Ultra Integrity Validator: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Ultra Integrity Validator: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_advanced_model_orchestrator():
    """Test Advanced Model Orchestrator basic functionality"""
    try:
        from mahoun.llm.advanced_model_orchestrator import AdvancedModelOrchestrator, ModelMetrics
        from unittest.mock import Mock
        
        # Create orchestrator WITHOUT ModelManager to avoid /app permission issue
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Test basic properties
        assert orchestrator.enable_ab_testing is True
        assert orchestrator.enable_canary is True
        assert len(orchestrator.active_models) == 0
        
        # Test model registration
        mock_model = Mock()
        success = orchestrator.register_model(
            "test-model", "TestLLM", "1.0", mock_model
        )
        
        assert success is True
        assert "test-model" in orchestrator.active_models
        assert "test-model" in orchestrator.model_metrics
        
        # Test metrics
        orchestrator.record_request("test-model", 100.0, True)
        metrics = orchestrator.model_metrics["test-model"]
        
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.error_rate == 0.0
        
        print("✅ Advanced Model Orchestrator: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Advanced Model Orchestrator: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_metrics_dataclass():
    """Test ModelMetrics dataclass functionality"""
    try:
        from mahoun.llm.advanced_model_orchestrator import ModelMetrics
        
        # Create metrics
        metrics = ModelMetrics("test-id", "TestModel", "1.0")
        
        # Test initialization
        assert metrics.model_id == "test-id"
        assert metrics.model_name == "TestModel"
        assert metrics.total_requests == 0
        assert len(metrics.latency_history) == 0
        
        # Test latency updates
        test_latencies = [100, 150, 200, 75, 300]
        for lat in test_latencies:
            metrics.update_latency(lat)
        
        assert len(metrics.latency_history) == 5
        expected_avg = sum(test_latencies) / len(test_latencies)
        assert abs(metrics.avg_latency_ms - expected_avg) < 0.01
        
        # Test request updates
        metrics.update_request_count(True)
        metrics.update_request_count(False)
        
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 1
        assert abs(metrics.error_rate - 0.5) < 0.01
        
        print("✅ ModelMetrics DataClass: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ ModelMetrics DataClass: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Running Simple Validation Tests...")
    print("=" * 50)
    
    results = []
    results.append(test_ultra_integrity_validator())
    results.append(test_advanced_model_orchestrator()) 
    results.append(test_model_metrics_dataclass())
    
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        exit(0)
    else:
        print(f"💥 SOME TESTS FAILED ({passed}/{total})")
        exit(1)