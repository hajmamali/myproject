"""
Property Tests for LLM Router
==============================
Tests universal correctness properties of the LLM router.

Property 10: LLM Router Deterministic Selection
Property 11: LLM Router Fallback Chain
"""

import pytest
from mahoun.llm.router import (
    LLMRouter,
    LLMProvider,
    ModelConfig,
    RoutingStrategy,
    LLMRouterError,
)


# =============================================================================
# Property 10: Deterministic Selection
# =============================================================================

class TestProperty10_DeterministicSelection:
    """
    Property 10: LLM Router Deterministic Selection
    
    Universal Property:
        For any prompt P, capability C, and context X:
        select(P, C, X) always returns the same model M
        
    This ensures reproducibility and auditability.
    """
    
    def test_same_inputs_same_output(self):
        """Same inputs must produce same output."""
        models = [
            ModelConfig(
                name="model-a",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["general"]),
                priority=10
            ),
            ModelConfig(
                name="model-b",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["general"]),
                priority=5
            ),
        ]
        
        router = LLMRouter(models=models, strategy=RoutingStrategy.PRIORITY)
        
        prompt = "Hello, world!"
        capability = "general"
        context = {"user_id": "123"}
        
        # Call multiple times
        results = [
            router.select(prompt, capability, context)
            for _ in range(10)
        ]
        
        # All results must be identical
        assert len(set(results)) == 1, "Selection must be deterministic"
        assert results[0] == "model-a", "Should select highest priority"
    
    def test_deterministic_with_routing_rules(self):
        """Routing rules must be deterministic."""
        models = [
            ModelConfig(
                name="code-model",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["code"]),
                priority=10
            ),
            ModelConfig(
                name="general-model",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["general"]),
                priority=5
            ),
        ]
        
        router = LLMRouter(models=models)
        router.add_routing_rule("code", "code-model", priority=100)
        
        prompt = "Write a Python function"
        
        # Call multiple times
        results = [router.select(prompt, capability="code") for _ in range(10)]
        
        # All results must be identical
        assert len(set(results)) == 1
        assert results[0] == "code-model"
    
    def test_deterministic_across_router_instances(self):
        """Same configuration must produce same results across instances."""
        models = [
            ModelConfig(
                name="model-a",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["general"]),
                priority=10
            ),
            ModelConfig(
                name="model-b",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["general"]),
                priority=5
            ),
        ]
        
        router1 = LLMRouter(models=models, strategy=RoutingStrategy.PRIORITY)
        router2 = LLMRouter(models=models, strategy=RoutingStrategy.PRIORITY)
        
        prompt = "Test prompt"
        
        result1 = router1.select(prompt)
        result2 = router2.select(prompt)
        
        assert result1 == result2, "Different instances must produce same result"
    
    def test_deterministic_with_capability_matching(self):
        """Capability matching must be deterministic."""
        models = [
            ModelConfig(
                name="specialized",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["legal", "analysis"]),
                priority=10
            ),
            ModelConfig(
                name="general",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["general"]),
                priority=5
            ),
        ]
        
        router = LLMRouter(models=models)
        
        # Call multiple times with same capability
        results = [router.select("Analyze this contract", capability="legal") for _ in range(10)]
        
        assert len(set(results)) == 1
        assert results[0] == "specialized"
    
    def test_deterministic_priority_ordering(self):
        """Priority ordering must be stable and deterministic."""
        models = [
            ModelConfig(name="p10", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="p5", provider=LLMProvider.LOCAL, priority=5),
            ModelConfig(name="p1", provider=LLMProvider.LOCAL, priority=1),
        ]
        
        router = LLMRouter(models=models, strategy=RoutingStrategy.PRIORITY)
        
        # Multiple selections
        results = [router.select("test") for _ in range(20)]
        
        # All must select highest priority
        assert all(r == "p10" for r in results)
    
    def test_deterministic_with_context(self):
        """Context-based routing must be deterministic."""
        models = [
            ModelConfig(name="model-a", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="model-b", provider=LLMProvider.LOCAL, priority=5),
        ]
        
        router = LLMRouter(models=models)
        router.add_routing_rule(
            "special",
            "model-b",
            priority=100,
            conditions={"env": "production"}
        )
        
        context = {"env": "production"}
        
        # Multiple calls with same context
        results = [router.select("test", capability="special", context=context) for _ in range(10)]
        
        assert len(set(results)) == 1
        assert results[0] == "model-b"


# =============================================================================
# Property 11: Fallback Chain
# =============================================================================

class TestProperty11_FallbackChain:
    """
    Property 11: LLM Router Fallback Chain
    
    Universal Property:
        For any failed model M in chain [M1, M2, ..., Mn]:
        get_fallback(M) returns the next available model in priority order
        
    This ensures resilience and high availability.
    """
    
    def test_fallback_returns_next_in_chain(self):
        """Fallback must return next model in priority order."""
        models = [
            ModelConfig(name="primary", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="secondary", provider=LLMProvider.LOCAL, priority=5),
            ModelConfig(name="tertiary", provider=LLMProvider.LOCAL, priority=1),
        ]
        
        router = LLMRouter(models=models)
        
        # Primary fails -> secondary
        fallback1 = router.get_fallback("primary")
        assert fallback1 == "secondary"
        
        # Secondary fails -> tertiary
        fallback2 = router.get_fallback("secondary")
        assert fallback2 == "tertiary"
        
        # Tertiary fails -> None
        fallback3 = router.get_fallback("tertiary")
        assert fallback3 is None
    
    def test_fallback_chain_completeness(self):
        """Every model except last must have a fallback."""
        models = [
            ModelConfig(name=f"model-{i}", provider=LLMProvider.LOCAL, priority=10-i)
            for i in range(5)
        ]
        
        router = LLMRouter(models=models)
        
        # All models except last should have fallback
        for i in range(4):
            model_name = f"model-{i}"
            fallback = router.get_fallback(model_name)
            assert fallback is not None, f"{model_name} must have fallback"
            assert fallback == f"model-{i+1}", "Fallback must be next in priority"
        
        # Last model has no fallback
        assert router.get_fallback("model-4") is None
    
    def test_fallback_respects_circuit_breakers(self):
        """Fallback must skip models with open circuits."""
        models = [
            ModelConfig(name="primary", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="secondary", provider=LLMProvider.LOCAL, priority=5),
            ModelConfig(name="tertiary", provider=LLMProvider.LOCAL, priority=1),
        ]
        
        router = LLMRouter(models=models, enable_circuit_breakers=True)
        
        # Open circuit for secondary by recording failures
        for _ in range(10):
            router.record_failure("secondary")
        
        # Primary fails -> should skip secondary (circuit open) -> tertiary
        fallback = router.get_fallback("primary")
        assert fallback == "tertiary", "Must skip models with open circuits"
    
    def test_fallback_chain_exhaustion(self):
        """When all models fail, fallback returns None."""
        models = [
            ModelConfig(name="model-a", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="model-b", provider=LLMProvider.LOCAL, priority=5),
        ]
        
        router = LLMRouter(models=models)
        
        # Fail both models
        router.record_failure("model-a")
        router.record_failure("model-b")
        
        # Get fallback for model-a
        fallback1 = router.get_fallback("model-a")
        assert fallback1 == "model-b"
        
        # Get fallback for model-b
        fallback2 = router.get_fallback("model-b")
        assert fallback2 is None, "No more fallbacks available"
    
    def test_fallback_with_capability_filtering(self):
        """Fallback should prefer models with matching capabilities."""
        models = [
            ModelConfig(
                name="code-primary",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["code"]),
                priority=10
            ),
            ModelConfig(
                name="code-secondary",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["code"]),
                priority=5
            ),
            ModelConfig(
                name="general",
                provider=LLMProvider.LOCAL,
                capabilities=frozenset(["general"]),
                priority=3
            ),
        ]
        
        router = LLMRouter(models=models)
        
        # Primary code model fails
        fallback = router.get_fallback("code-primary")
        
        # Should fallback to secondary code model
        assert fallback == "code-secondary"
    
    def test_fallback_updates_circuit_breaker(self):
        """Calling get_fallback must update circuit breaker state."""
        models = [
            ModelConfig(name="primary", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="secondary", provider=LLMProvider.LOCAL, priority=5),
        ]
        
        router = LLMRouter(models=models, enable_circuit_breakers=True)
        
        # Get initial circuit state
        from mahoun.llm.router import CircuitState
        initial_state = router.get_circuit_state("primary")
        assert initial_state == CircuitState.CLOSED
        
        # Record multiple failures to open circuit
        for _ in range(10):
            router.get_fallback("primary")
        
        # Circuit should be open
        final_state = router.get_circuit_state("primary")
        assert final_state == CircuitState.OPEN
    
    def test_fallback_chain_with_single_model(self):
        """Single model configuration should return None on fallback."""
        models = [
            ModelConfig(name="only-model", provider=LLMProvider.LOCAL, priority=10),
        ]
        
        router = LLMRouter(models=models)
        
        fallback = router.get_fallback("only-model")
        assert fallback is None, "Single model has no fallback"
    
    def test_fallback_chain_ordering_stability(self):
        """Fallback chain order must be stable across calls."""
        models = [
            ModelConfig(name="a", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="b", provider=LLMProvider.LOCAL, priority=5),
            ModelConfig(name="c", provider=LLMProvider.LOCAL, priority=1),
        ]
        
        router = LLMRouter(models=models)
        
        # Get fallback chain multiple times
        chains = []
        for _ in range(10):
            chain = []
            current = "a"
            while current:
                current = router.get_fallback(current)
                if current:
                    chain.append(current)
            chains.append(tuple(chain))
        
        # All chains must be identical
        assert len(set(chains)) == 1
        assert chains[0] == ("b", "c")


# =============================================================================
# Integration Tests
# =============================================================================

class TestRouterIntegration:
    """Integration tests for router with fallback."""
    
    def test_select_with_automatic_fallback(self):
        """Router should automatically use fallback on failure."""
        models = [
            ModelConfig(name="primary", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="backup", provider=LLMProvider.LOCAL, priority=5),
        ]
        
        router = LLMRouter(models=models, enable_circuit_breakers=True)
        
        # Open circuit for primary
        for _ in range(10):
            router.record_failure("primary")
        
        # Selection should automatically use backup
        selected = router.select("test prompt")
        assert selected == "backup", "Should automatically fallback"
    
    def test_circuit_breaker_recovery(self):
        """Circuit breaker should allow recovery after timeout."""
        import time
        from mahoun.llm.router import CircuitState
        
        models = [
            ModelConfig(name="flaky", provider=LLMProvider.LOCAL, priority=10),
        ]
        
        router = LLMRouter(models=models, enable_circuit_breakers=True)
        
        # Open circuit
        for _ in range(10):
            router.record_failure("flaky")
        
        assert router.get_circuit_state("flaky") == CircuitState.OPEN
        
        # Wait for timeout (circuit breaker timeout is 60s, but we can't wait that long)
        # Instead, manually set the last_failure_time to simulate timeout
        cb = router._circuit_breakers["flaky"]
        from datetime import datetime, timedelta
        cb.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=61)
        
        # Circuit should transition to HALF_OPEN
        assert cb.is_available(), "Circuit should allow requests after timeout"
        
        # Record success to close circuit
        for _ in range(5):
            router.record_success("flaky", latency_ms=100)
        
        assert router.get_circuit_state("flaky") == CircuitState.CLOSED
    
    def test_routing_decision_audit_trail(self):
        """Router should maintain audit trail of decisions."""
        models = [
            ModelConfig(name="model-a", provider=LLMProvider.LOCAL, priority=10),
        ]
        
        router = LLMRouter(models=models)
        
        # Make several selections
        for i in range(5):
            router.select(f"prompt-{i}")
        
        # Check audit trail
        decisions = router.get_recent_decisions()
        assert len(decisions) >= 5
        
        # Verify decision structure
        decision = decisions[-1]
        assert hasattr(decision, "timestamp")
        assert hasattr(decision, "selected_model")
        assert hasattr(decision, "reason")
        assert decision.selected_model == "model-a"


# =============================================================================
# Edge Cases
# =============================================================================

class TestRouterEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_no_models_raises_error(self):
        """Router with no models should raise error on select."""
        router = LLMRouter(models=[])
        
        with pytest.raises(LLMRouterError, match="No models available"):
            router.select("test")
    
    def test_all_circuits_open_raises_error(self):
        """All circuits open should raise error."""
        models = [
            ModelConfig(name="model-a", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="model-b", provider=LLMProvider.LOCAL, priority=5),
        ]
        
        router = LLMRouter(models=models, enable_circuit_breakers=True)
        
        # Open all circuits
        for model_name in ["model-a", "model-b"]:
            for _ in range(10):
                router.record_failure(model_name)
        
        with pytest.raises(LLMRouterError, match="all circuits open"):
            router.select("test")
    
    def test_unknown_model_in_routing_rule(self):
        """Adding rule for unknown model should raise error."""
        models = [
            ModelConfig(name="model-a", provider=LLMProvider.LOCAL, priority=10),
        ]
        
        router = LLMRouter(models=models)
        
        with pytest.raises(LLMRouterError, match="Unknown model"):
            router.add_routing_rule("code", "nonexistent-model")
    
    def test_remove_model_cleans_up_rules(self):
        """Removing model should clean up routing rules."""
        models = [
            ModelConfig(name="model-a", provider=LLMProvider.LOCAL, priority=10),
            ModelConfig(name="model-b", provider=LLMProvider.LOCAL, priority=5),
        ]
        
        router = LLMRouter(models=models)
        router.add_routing_rule("code", "model-a")
        
        # Remove model
        router.remove_model("model-a")
        
        # Rule should be removed
        assert "model-a" not in router.list_models()
        
        # Selecting with code capability should use model-b
        selected = router.select("test", capability="code")
        assert selected == "model-b"
