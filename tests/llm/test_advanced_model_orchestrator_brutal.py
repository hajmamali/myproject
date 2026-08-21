"""
Brutal Tests for Advanced Model Orchestrator
==========================================

The most ruthless, comprehensive test suite for the Advanced Model Orchestrator.
Zero tolerance. Maximum scrutiny. Production-grade validation.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from collections import deque

from mahoun.llm.advanced_model_orchestrator import (
    AdvancedModelOrchestrator,
    ModelMetrics,
    ABTestConfig, 
    CanaryDeployment,
    create_orchestrator
)
from mahoun.llm.model_manager import ModelManager
from mahoun.core.exceptions import ModelLoadError

import logging
logger = logging.getLogger(__name__)


@pytest.fixture
def mock_model_manager():
    """Fixture to provide mocked ModelManager to avoid /app permission issues"""
    return Mock()


@pytest.fixture  
def orchestrator(mock_model_manager):
    """Fixture to provide AdvancedModelOrchestrator with mocked ModelManager"""
    return AdvancedModelOrchestrator(base_model_manager=mock_model_manager)


class TestOrchestratorFoundationalRequirements:
    """Core foundational tests - if these fail, everything else is meaningless"""
    
    def test_orchestrator_initialization_strict_validation(self):
        """Test initialization with brutal parameter validation"""
        # Valid initialization with mocked ModelManager to avoid /app permission issues
        orchestrator = AdvancedModelOrchestrator(
            base_model_manager=Mock(),
            enable_ab_testing=True,
            enable_canary=True,
            enable_auto_scale=True
        )
        
        assert orchestrator.enable_ab_testing is True
        assert orchestrator.enable_canary is True
        assert orchestrator.enable_auto_scale is True
        assert orchestrator.routing_strategy == 'round_robin'
        assert len(orchestrator.active_models) == 0
        assert len(orchestrator.model_metrics) == 0
        assert orchestrator._routing_counter == 0
        
        # Test with custom ModelManager
        custom_manager = Mock(spec=ModelManager)
        orchestrator_custom = AdvancedModelOrchestrator(
            base_model_manager=custom_manager
        )
        assert orchestrator_custom.model_manager == custom_manager
    
    def test_factory_function_compliance(self):
        """Factory function MUST work perfectly"""
        orchestrator = create_orchestrator(
            enable_ab_testing=False,
            enable_canary=True
        )
        
        assert isinstance(orchestrator, AdvancedModelOrchestrator)
        assert orchestrator.enable_ab_testing is False
        assert orchestrator.enable_canary is True


class TestModelRegistrationAndLifecycle:
    """Model registration and lifecycle management tests"""
    
    def test_model_registration_success_path(self, mock_model_manager):
        """Test successful model registration with complete validation"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=mock_model_manager)
        
        # Mock model instance
        mock_model = Mock()
        mock_model.predict = Mock(return_value="test prediction")
        
        # Register model
        success = orchestrator.register_model(
            model_id="test-model-001",
            model_name="TestLLM",
            version="1.0.0",
            model_instance=mock_model,
            metadata={"type": "language_model", "size": "7B"}
        )
        
        assert success is True
        assert "test-model-001" in orchestrator.active_models
        assert "test-model-001" in orchestrator.model_metrics
        
        # Verify model data
        model_data = orchestrator.active_models["test-model-001"]
        assert model_data["model"] == mock_model
        assert model_data["name"] == "TestLLM"
        assert model_data["version"] == "1.0.0"
        assert model_data["status"] == "active"
        assert model_data["metadata"]["type"] == "language_model"
        
        # Verify metrics initialization
        metrics = orchestrator.model_metrics["test-model-001"]
        assert metrics.model_id == "test-model-001"
        assert metrics.model_name == "TestLLM"
        assert metrics.version == "1.0.0"
        assert metrics.total_requests == 0
        assert metrics.error_rate == 0.0
    
    def test_model_registration_duplicate_rejection(self, mock_model_manager):
        """Test that duplicate model registration is properly rejected"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=mock_model_manager)
        
        mock_model = Mock()
        
        # First registration should succeed
        success1 = orchestrator.register_model("dup-test", "TestModel", "1.0", mock_model)
        assert success1 is True
        
        # Second registration with same ID should fail
        success2 = orchestrator.register_model("dup-test", "TestModel2", "2.0", mock_model)
        assert success2 is False
        
        # Original should remain unchanged
        assert orchestrator.active_models["dup-test"]["name"] == "TestModel"
        assert orchestrator.active_models["dup-test"]["version"] == "1.0"
    
    def test_model_unregistration_complete_cleanup(self):
        """Test complete cleanup during model unregistration"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register model
        mock_model = Mock()
        orchestrator.register_model("cleanup-test", "CleanupModel", "1.0", mock_model)
        
        # Add some metrics
        orchestrator.record_request("cleanup-test", 100.5, True)
        assert orchestrator.model_metrics["cleanup-test"].total_requests == 1
        
        # Unregister
        success = orchestrator.unregister_model("cleanup-test")
        assert success is True
        
        # Verify complete cleanup
        assert "cleanup-test" not in orchestrator.active_models
        assert "cleanup-test" not in orchestrator.model_metrics
        
        # Unregistering non-existent model should return False
        success2 = orchestrator.unregister_model("non-existent")
        assert success2 is False


class TestModelMetricsDataClass:
    """Comprehensive ModelMetrics dataclass testing"""
    
    def test_model_metrics_initialization(self):
        """Test ModelMetrics proper initialization"""
        metrics = ModelMetrics("test-id", "TestModel", "1.0")
        
        assert metrics.model_id == "test-id"
        assert metrics.model_name == "TestModel"
        assert metrics.version == "1.0"
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.avg_latency_ms == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.first_request_at is None
        assert metrics.last_request_at is None
        assert isinstance(metrics.latency_history, deque)
        assert metrics.latency_history.maxlen == 1000
    
    def test_latency_update_calculations(self):
        """Test latency update calculations with statistical accuracy"""
        metrics = ModelMetrics("test", "Test", "1.0")
        
        # Add latency samples
        test_latencies = [100, 150, 200, 75, 300, 120, 180]
        for lat in test_latencies:
            metrics.update_latency(lat)
        
        # Verify calculations
        expected_avg = sum(test_latencies) / len(test_latencies)
        assert abs(metrics.avg_latency_ms - expected_avg) < 0.01
        
        # Verify percentiles
        sorted_lat = sorted(test_latencies)
        expected_p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
        expected_p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
        
        assert metrics.p95_latency_ms == expected_p95
        assert metrics.p99_latency_ms == expected_p99
    
    def test_request_count_updates_and_error_rate(self):
        """Test request count updates and error rate calculations"""
        metrics = ModelMetrics("test", "Test", "1.0")
        
        # Simulate requests: 7 successful, 3 failed
        success_pattern = [True, True, False, True, True, True, False, True, True, False]
        
        for success in success_pattern:
            metrics.update_request_count(success)
        
        assert metrics.total_requests == 10
        assert metrics.successful_requests == 7
        assert metrics.failed_requests == 3
        assert abs(metrics.error_rate - 0.3) < 0.01  # 30% error rate
        
        # Timestamps should be set
        assert metrics.first_request_at is not None
        assert metrics.last_request_at is not None
        
        # Last should be >= First
        first_time = datetime.fromisoformat(metrics.first_request_at)
        last_time = datetime.fromisoformat(metrics.last_request_at)
        assert last_time >= first_time
    
    def test_latency_history_circular_buffer(self):
        """Test latency history circular buffer behavior"""
        metrics = ModelMetrics("test", "Test", "1.0")
        
        # Add more than maxlen (1000) entries
        for i in range(1200):
            metrics.update_latency(float(i))
        
        # Should only keep last 1000
        assert len(metrics.latency_history) == 1000
        
        # Should contain values 200-1199 (last 1000)
        history_list = list(metrics.latency_history)
        assert history_list[0] == 200.0
        assert history_list[-1] == 1199.0


class TestSmartRouting:
    """Smart routing algorithm tests"""
    
    def test_round_robin_routing_fairness(self):
        """Test round robin routing distributes requests fairly"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register multiple models of same type
        models = ["model-1", "model-2", "model-3"]
        for i, model_id in enumerate(models):
            mock_model = Mock()
            orchestrator.register_model(
                model_id, "TestType", f"1.{i}", mock_model
            )
        
        # Route 9 requests
        routed_models = []
        for _ in range(9):
            routed = orchestrator.route_request("TestType", "round_robin")
            routed_models.append(routed)
        
        # Should distribute evenly: 3 requests per model
        for model_id in models:
            count = routed_models.count(model_id)
            assert count == 3, f"Model {model_id} got {count} requests, expected 3"
    
    def test_least_loaded_routing_accuracy(self):
        """Test least loaded routing chooses model with fewest requests"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register models and give them different request loads
        models_and_loads = [("heavy", 100), ("medium", 50), ("light", 10)]
        
        for model_id, load in models_and_loads:
            mock_model = Mock()
            orchestrator.register_model(model_id, "LoadTest", "1.0", mock_model)
            
            # Simulate load
            for _ in range(load):
                orchestrator.record_request(model_id, 100.0, True)
        
        # Route request - should go to "light" model
        routed = orchestrator.route_request("LoadTest", "least_loaded")
        assert routed == "light"
        
        # Route several more - should still prefer "light"
        for _ in range(5):
            routed = orchestrator.route_request("LoadTest", "least_loaded")
            orchestrator.record_request(routed, 100.0, True)
        
        # "light" should still be chosen (10+5=15 < 50)
        routed = orchestrator.route_request("LoadTest", "least_loaded") 
        assert routed == "light"
    
    def test_best_performance_routing_with_insufficient_data(self):
        """Test best performance routing fallback when insufficient data"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register models with minimal request history
        models = ["new-1", "new-2", "new-3"]
        for model_id in models:
            mock_model = Mock()
            orchestrator.register_model(model_id, "NewType", "1.0", mock_model)
            
            # Give minimal requests (less than 10 threshold)
            for _ in range(5):
                orchestrator.record_request(model_id, 100.0, True)
        
        # Should fallback to first available model
        routed = orchestrator.route_request("NewType", "best_performance")
        assert routed == "new-1"  # First in list
    
    def test_routing_no_available_models(self):
        """Test routing behavior when no models are available"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # No models registered
        routed = orchestrator.route_request("NonExistent", "round_robin")
        assert routed is None
        
        # Models registered but wrong type
        mock_model = Mock()
        orchestrator.register_model("wrong-type", "WrongType", "1.0", mock_model)
        
        routed = orchestrator.route_request("CorrectType", "round_robin")
        assert routed is None

class TestABTestingFramework:
    """A/B Testing framework comprehensive testing"""
    
    def test_ab_test_creation_validation(self):
        """Test A/B test creation with strict validation"""
        orchestrator = AdvancedModelOrchestrator(enable_ab_testing=True)
        
        # Register models for testing
        model_a = Mock()
        model_b = Mock()
        orchestrator.register_model("model-a", "TestModel", "1.0", model_a)
        orchestrator.register_model("model-b", "TestModel", "2.0", model_b)
        
        # Create A/B test
        success = orchestrator.start_ab_test(
            "test-001", "model-a", "model-b", 
            traffic_split=0.6, min_requests=50
        )
        
        assert success is True
        assert "test-001" in orchestrator.ab_tests
        
        test_config = orchestrator.ab_tests["test-001"]
        assert test_config.model_a == "model-a"
        assert test_config.model_b == "model-b"
        assert test_config.traffic_split == 0.6
        assert test_config.min_requests == 50
        assert test_config.status == "active"
        assert test_config.winner is None
    
    def test_ab_test_creation_failure_conditions(self):
        """Test A/B test creation failure scenarios"""
        orchestrator = AdvancedModelOrchestrator(enable_ab_testing=True)
        
        # Test with AB testing disabled
        orchestrator_disabled = AdvancedModelOrchestrator(base_model_manager=Mock(), enable_ab_testing=False)
        success = orchestrator_disabled.start_ab_test("test", "a", "b")
        assert success is False
        
        # Test with non-existent models
        success = orchestrator.start_ab_test("test-bad", "non-existent-a", "non-existent-b")
        assert success is False
        
        # Register only one model
        orchestrator.register_model("only-one", "Test", "1.0", Mock())
        success = orchestrator.start_ab_test("test-partial", "only-one", "missing")
        assert success is False
        
        # Test duplicate test ID
        model_a, model_b = Mock(), Mock()
        orchestrator.register_model("a", "Test", "1.0", model_a)
        orchestrator.register_model("b", "Test", "2.0", model_b)
        
        orchestrator.start_ab_test("duplicate", "a", "b")
        success = orchestrator.start_ab_test("duplicate", "a", "b")  # Same ID
        assert success is False
    
    def test_ab_test_traffic_routing_distribution(self):
        """Test A/B test traffic routing follows specified distribution"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Setup A/B test with 30/70 split
        model_a, model_b = Mock(), Mock()
        orchestrator.register_model("model-a", "Test", "1.0", model_a)
        orchestrator.register_model("model-b", "Test", "2.0", model_b)
        orchestrator.start_ab_test("split-test", "model-a", "model-b", traffic_split=0.3)
        
        # Route many requests and check distribution
        routes = []
        for _ in range(1000):
            routed = orchestrator.get_ab_test_model("split-test")
            routes.append(routed)
        
        model_a_count = routes.count("model-a")
        model_b_count = routes.count("model-b")
        
        # Should be approximately 30% model-a, 70% model-b
        # Allow 5% tolerance for randomness
        model_a_ratio = model_a_count / 1000
        assert 0.25 <= model_a_ratio <= 0.35, f"Model A ratio: {model_a_ratio}, expected ~0.30"
        
        model_b_ratio = model_b_count / 1000
        assert 0.65 <= model_b_ratio <= 0.75, f"Model B ratio: {model_b_ratio}, expected ~0.70"
    
    def test_ab_test_evaluation_insufficient_data(self):
        """Test A/B test evaluation with insufficient data"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Setup test
        model_a, model_b = Mock(), Mock()
        orchestrator.register_model("eval-a", "Test", "1.0", model_a)
        orchestrator.register_model("eval-b", "Test", "2.0", model_b) 
        orchestrator.start_ab_test("eval-test", "eval-a", "eval-b", min_requests=100)
        
        # Add insufficient data
        for _ in range(20):
            orchestrator.record_request("eval-a", 100.0, True)
        for _ in range(30):
            orchestrator.record_request("eval-b", 150.0, True)
        
        result = orchestrator.evaluate_ab_test("eval-test")
        
        assert result['status'] == 'insufficient_data'
        assert result['requests'] == 50  # 20 + 30
        assert result['required'] == 100
    
    def test_ab_test_evaluation_winner_determination(self):
        """Test A/B test winner determination with sufficient data"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Setup test
        model_a, model_b = Mock(), Mock()
        orchestrator.register_model("winner-a", "Test", "1.0", model_a)
        orchestrator.register_model("winner-b", "Test", "2.0", model_b)
        orchestrator.start_ab_test("winner-test", "winner-a", "winner-b", min_requests=100)
        
        # Make model-a clearly better (lower latency, no errors)
        for _ in range(60):
            orchestrator.record_request("winner-a", 50.0, True)  # Fast, no errors
        
        for _ in range(60):
            orchestrator.record_request("winner-b", 200.0, True)  # Slower
        
        result = orchestrator.evaluate_ab_test("winner-test")
        
        assert 'winner' in result
        assert result['winner'] == "winner-a"  # Should win due to lower latency
        assert result['confidence'] > 0
        assert 'model_a_score' in result
        assert 'model_b_score' in result
        
        # Test should be marked completed
        test_config = orchestrator.ab_tests["winner-test"]
        assert test_config.status == "completed"
        assert test_config.winner == "winner-a"


class TestCanaryDeployments:
    """Canary deployment system testing"""
    
    def test_canary_deployment_creation(self):
        """Test canary deployment creation and initial state"""
        orchestrator = AdvancedModelOrchestrator(enable_canary=True)
        
        # Setup models
        stable_model, canary_model = Mock(), Mock()
        orchestrator.register_model("stable", "Production", "1.0", stable_model)
        orchestrator.register_model("canary", "Production", "2.0", canary_model)
        
        success = orchestrator.start_canary_deployment(
            "canary-001", "stable", "canary", 
            initial_traffic_percent=5.0, increment_percent=5.0
        )
        
        assert success is True
        assert "canary-001" in orchestrator.canary_deployments
        
        canary = orchestrator.canary_deployments["canary-001"]
        assert canary.stable_model == "stable"
        assert canary.canary_model == "canary"
        assert canary.current_traffic_percent == 5.0
        assert canary.increment_percent == 5.0
        assert canary.status == "active"
    
    def test_canary_deployment_failure_conditions(self):
        """Test canary deployment creation failure scenarios"""
        # Disabled canary
        orchestrator_disabled = AdvancedModelOrchestrator(base_model_manager=Mock(), enable_canary=False)
        success = orchestrator_disabled.start_canary_deployment("test", "a", "b")
        assert success is False
        
        # Missing models
        orchestrator = AdvancedModelOrchestrator(enable_canary=True)
        success = orchestrator.start_canary_deployment("test", "missing", "also-missing")
        assert success is False
        
        # Duplicate canary ID
        stable, canary = Mock(), Mock()
        orchestrator.register_model("stable", "Test", "1.0", stable)
        orchestrator.register_model("canary", "Test", "2.0", canary)
        
        orchestrator.start_canary_deployment("dup", "stable", "canary")
        success = orchestrator.start_canary_deployment("dup", "stable", "canary")
        assert success is False
    
    def test_canary_health_check_rollback_on_high_error_rate(self):
        """Test canary rollback when error rate exceeds threshold"""
        orchestrator = AdvancedModelOrchestrator(enable_canary=True)
        
        # Setup canary with 5% max error rate
        stable, canary = Mock(), Mock()
        orchestrator.register_model("stable-rollback", "Test", "1.0", stable)
        orchestrator.register_model("canary-rollback", "Test", "2.0", canary)
        orchestrator.start_canary_deployment("rollback-test", "stable-rollback", "canary-rollback")
        
        # Set low max error rate for testing
        orchestrator.canary_deployments["rollback-test"].max_error_rate = 0.05  # 5%
        
        # Simulate high error rate for canary (10% errors)
        for i in range(100):
            success = i % 10 != 0  # 10% failure rate
            orchestrator.record_request("canary-rollback", 100.0, success)
        
        # Check health - should trigger rollback
        result = orchestrator.check_canary_health("rollback-test")
        
        assert result['decision'] == 'rolled_back'
        assert 'Error rate' in result['reason']
        
        # Canary should be marked as rolled back
        canary_config = orchestrator.canary_deployments["rollback-test"]
        assert canary_config.status == 'rolled_back'
        assert canary_config.current_traffic_percent == 0.0

class TestMetricsAndMonitoring:
    """Metrics and monitoring comprehensive tests"""
    
    def test_request_recording_accuracy(self):
        """Test request recording with accurate metrics calculation"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register model
        mock_model = Mock()
        orchestrator.register_model("metrics-test", "MetricsModel", "1.0", mock_model)
        
        # Record various requests
        test_data = [
            (50.0, True),   # Fast success
            (100.0, True),  # Slow success  
            (75.0, False),  # Medium fail
            (200.0, True),  # Very slow success
            (25.0, False),  # Fast fail
        ]
        
        for latency, success in test_data:
            orchestrator.record_request("metrics-test", latency, success)
        
        metrics = orchestrator.model_metrics["metrics-test"]
        
        # Verify counts
        assert metrics.total_requests == 5
        assert metrics.successful_requests == 3
        assert metrics.failed_requests == 2
        assert abs(metrics.error_rate - 0.4) < 0.01  # 40% error rate
        
        # Verify latency calculations
        expected_avg = sum([lat for lat, _ in test_data]) / len(test_data)
        assert abs(metrics.avg_latency_ms - expected_avg) < 0.01
    
    def test_get_model_metrics_comprehensive(self):
        """Test comprehensive model metrics retrieval"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register multiple models
        models = ["model-1", "model-2", "model-3"]
        for model_id in models:
            mock_model = Mock()
            orchestrator.register_model(model_id, "TestType", "1.0", mock_model)
            
            # Add some metrics
            orchestrator.record_request(model_id, 100.0, True)
        
        # Test single model metrics
        single_metrics = orchestrator.get_model_metrics("model-1")
        assert single_metrics['model_id'] == "model-1"
        assert single_metrics['total_requests'] == 1
        assert single_metrics['error_rate'] == 0.0
        
        # Test all models metrics
        all_metrics = orchestrator.get_model_metrics()
        assert len(all_metrics) == 3
        for model_id in models:
            assert model_id in all_metrics
            assert all_metrics[model_id]['total_requests'] == 1
        
        # Test non-existent model
        missing_metrics = orchestrator.get_model_metrics("non-existent")
        assert 'error' in missing_metrics
    
    def test_system_status_comprehensive(self):
        """Test system status reporting accuracy"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Initial empty state
        status = orchestrator.get_system_status()
        assert status['active_models'] == 0
        assert status['active_ab_tests'] == 0
        assert status['total_requests'] == 0
        
        # Add models and tests
        model_a, model_b = Mock(), Mock()
        orchestrator.register_model("status-a", "StatusTest", "1.0", model_a)
        orchestrator.register_model("status-b", "StatusTest", "2.0", model_b)
        
        # Add A/B test
        orchestrator.start_ab_test("status-test", "status-a", "status-b")
        
        # Add some requests
        orchestrator.record_request("status-a", 100.0, True)
        orchestrator.record_request("status-b", 150.0, True)
        
        # Check updated status
        status = orchestrator.get_system_status()
        assert status['active_models'] == 2
        assert status['active_ab_tests'] == 1
        assert status['total_requests'] == 2


class TestThreadSafetyAndConcurrency:
    """Thread safety and concurrency tests"""
    
    def test_concurrent_model_registration(self):
        """Test thread-safe model registration"""
        import threading
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        registration_results = []
        registration_lock = threading.Lock()
        
        def register_model(model_id):
            mock_model = Mock()
            result = orchestrator.register_model(
                f"concurrent-{model_id}", "ConcurrentTest", "1.0", mock_model
            )
            with registration_lock:
                registration_results.append((model_id, result))
        
        # Start 10 concurrent registrations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_model, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should succeed (unique IDs)
        assert len(registration_results) == 10
        for _, result in registration_results:
            assert result is True
        
        # Verify all models are registered
        assert len(orchestrator.active_models) == 10
    
    def test_concurrent_request_recording(self):
        """Test thread-safe request recording"""
        import threading
        import time
        
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register model
        mock_model = Mock()
        orchestrator.register_model("concurrent-requests", "ConcurrentTest", "1.0", mock_model)
        
        def record_requests(num_requests):
            for i in range(num_requests):
                latency = 50.0 + (i % 10) * 10  # Varying latency
                success = i % 3 != 0  # ~67% success rate
                orchestrator.record_request("concurrent-requests", latency, success)
                time.sleep(0.001)  # Small delay
        
        # Start 5 threads, each recording 20 requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_requests, args=(20,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify total requests
        metrics = orchestrator.model_metrics["concurrent-requests"]
        assert metrics.total_requests == 100  # 5 threads * 20 requests
        
        # Verify counts are consistent
        assert metrics.successful_requests + metrics.failed_requests == 100
        assert 0 <= metrics.error_rate <= 1


class TestEdgeCasesAndErrorHandling:
    """Edge cases and error handling tests"""
    
    def test_routing_with_inactive_models(self):
        """Test routing behavior with inactive models"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register models
        active_model = Mock()
        inactive_model = Mock() 
        
        orchestrator.register_model("active", "TestType", "1.0", active_model)
        orchestrator.register_model("inactive", "TestType", "2.0", inactive_model)
        
        # Mark one as inactive
        orchestrator.active_models["inactive"]["status"] = "inactive"
        
        # Routing should only consider active models
        routed = orchestrator.route_request("TestType")
        assert routed == "active"
        
        # Multiple routes should still work
        for _ in range(5):
            routed = orchestrator.route_request("TestType")
            assert routed == "active"
    
    def test_ab_test_with_non_existent_test_id(self):
        """Test A/B test operations with invalid test IDs"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Try to get model for non-existent test
        result = orchestrator.get_ab_test_model("non-existent")
        assert result is None
        
        # Try to evaluate non-existent test  
        result = orchestrator.evaluate_ab_test("non-existent")
        assert result['error'] == 'Test not found'
    
    def test_canary_health_check_missing_canary(self):
        """Test canary health check with missing deployment"""
        orchestrator = AdvancedModelOrchestrator(enable_canary=True)
        
        result = orchestrator.check_canary_health("non-existent")
        assert result['error'] == 'Canary not found'
    
    def test_model_score_calculation_edge_cases(self):
        """Test model score calculation with edge cases"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Test with zero requests
        metrics_zero = ModelMetrics("test", "Test", "1.0")
        score = orchestrator._calculate_model_score(metrics_zero)
        assert isinstance(score, float)
        assert 0 <= score <= 1
        
        # Test with perfect performance
        metrics_perfect = ModelMetrics("test", "Test", "1.0")
        metrics_perfect.avg_latency_ms = 0.0
        metrics_perfect.error_rate = 0.0
        score_perfect = orchestrator._calculate_model_score(metrics_perfect)
        assert score_perfect == 1.0
        
        # Test with terrible performance
        metrics_bad = ModelMetrics("test", "Test", "1.0") 
        metrics_bad.avg_latency_ms = 2000.0  # 2 seconds
        metrics_bad.error_rate = 1.0  # 100% errors
        score_bad = orchestrator._calculate_model_score(metrics_bad)
        assert score_bad == 0.0


@pytest.mark.stress
class TestStressAndPerformance:
    """Stress and performance validation tests"""
    
    def test_large_scale_model_management(self):
        """Test managing large numbers of models"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register 100 models
        model_ids = []
        start_time = time.time()
        
        for i in range(100):
            model_id = f"stress-model-{i:03d}"
            mock_model = Mock()
            
            success = orchestrator.register_model(
                model_id, f"StressType-{i%5}", f"1.{i}", mock_model
            )
            assert success is True
            model_ids.append(model_id)
        
        registration_time = time.time() - start_time
        
        # Should register quickly (less than 5 seconds)
        assert registration_time < 5.0
        
        # Test routing performance
        start_time = time.time()
        for _ in range(1000):
            routed = orchestrator.route_request("StressType-0")
            assert routed is not None
        
        routing_time = time.time() - start_time
        
        # Should route quickly (less than 1 second for 1000 routes)
        assert routing_time < 1.0
        
        # Cleanup should also be fast
        start_time = time.time()
        for model_id in model_ids:
            orchestrator.unregister_model(model_id)
        
        cleanup_time = time.time() - start_time
        assert cleanup_time < 2.0
        assert len(orchestrator.active_models) == 0
    
    def test_high_frequency_metrics_recording(self):
        """Test high-frequency metrics recording performance"""
        orchestrator = AdvancedModelOrchestrator(base_model_manager=Mock())
        
        # Register model
        mock_model = Mock()
        orchestrator.register_model("stress-metrics", "StressTest", "1.0", mock_model)
        
        # Record 10,000 requests rapidly
        start_time = time.time()
        
        for i in range(10000):
            latency = 50.0 + (i % 100)  # Varying latency
            success = i % 10 != 0  # 90% success rate
            orchestrator.record_request("stress-metrics", latency, success)
        
        recording_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 10 seconds)
        assert recording_time < 10.0
        
        # Verify accuracy
        metrics = orchestrator.model_metrics["stress-metrics"]
        assert metrics.total_requests == 10000
        assert metrics.successful_requests == 9000
        assert metrics.failed_requests == 1000
        assert abs(metrics.error_rate - 0.1) < 0.01  # 10% error rate


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])