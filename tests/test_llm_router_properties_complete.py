import pytest
pytest.importorskip("hypothesis")
"""
Property-Based Tests for LLM Router
====================================
Tests universal properties of LLM routing system.

Property 10: LLM Router Deterministic Selection
Property 11: LLM Router Fallback Chain
"""

import pytest
from hypothesis import given, strategies as st, assume
from pathlib import Path
import tempfile

from mahoun.llm.router import (
    LLMRouter,
    ModelConfig,
    LLMProvider,
    RoutingStrategy,
    CircuitState,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def model_config_strategy(draw):
    """Generate valid ModelConfig instances."""
    name = draw(st.text(min_size=3, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'
    )))
    provider = draw(st.sampled_from(list(LLMProvider)))
    capabilities = draw(st.sets(
        st.sampled_from(["general", "code", "legal", "reasoning", "math"]),
        min_size=1,
        max_size=3
    ))
    priority = draw(st.integers(min_value=1, max_value=100))
    timeout = draw(st.integers(min_value=5, max_value=60))
    
    return ModelConfig(
        name=name,
        provider=provider,
        capabilities=frozenset(capabilities),
        priority=priority,
        timeout=timeout
    )


# =============================================================================
# Property 10: LLM Router Deterministic Selection
# =============================================================================

@given(
    models=st.lists(model_config_strategy(), min_size=1, max_size=5, unique_by=lambda m: m.name),
    prompt=st.text(min_size=10, max_size=100)
)
def test_property_deterministic_selection(models, prompt):
    """
    Property 10: LLM Router Deterministic Selection
    
    For any prompt and capability, the router SHALL return the same model name
    given the same configuration.
    """
    router = LLMRouter(models=models, strategy=RoutingStrategy.PRIORITY)
    
    # Select model multiple times
    selections = []
    for _ in range(3):
        selected = router.select(prompt)
        selections.append(selected)
    
    # All selections should be identical
    assert len(set(selections)) == 1, "Router returned different models for same input"


@given(
    models=st.lists(model_config_strategy(), min_size=2, max_size=5, unique_by=lambda m: m.name),
    prompt=st.text(min_size=10, max_size=100),
    capability=st.sampled_from(["general", "code", "legal", "reasoning"])
)
def test_property_deterministic_with_capability(models, prompt, capability):
    """
    Property: Selection with capability should be deterministic.
    """
    router = LLMRouter(models=models, strategy=RoutingStrategy.PRIORITY)
    
    # Add routing rule
    matching_models = [m for m in models if capability in m.capabilities]
    if matching_models:
        router.add_routing_rule(capability, matching_models[0].name)
        
        # Select multiple times
        selections = []
        for _ in range(3):
            selected = router.select(prompt, capability=capability)
            selections.append(selected)
        
        # All selections should be identical
        assert len(set(selections)) == 1


@given(
    models=st.lists(model_config_strategy(), min_size=1, max_size=5, unique_by=lambda m: m.name),
    prompt=st.text(min_size=10, max_size=100)
)
def test_property_selection_returns_configured_model(models, prompt):
    """
    Property: Router SHALL only return models that were configured.
    """
    router = LLMRouter(models=models, strategy=RoutingStrategy.PRIORITY)
    
    selected = router.select(prompt)
    
    # Selected model must be in configured models
    model_names = [m.name for m in models]
    assert selected in model_names, f"Router returned unconfigured model: {selected}"


# =============================================================================
# Property 11: LLM Router Fallback Chain
# =============================================================================

@given(
    models=st.lists(model_config_strategy(), min_size=2, max_size=5, unique_by=lambda m: m.name)
)
def test_property_fallback_chain_returns_next_model(models):
    """
    Property 11: LLM Router Fallback Chain
    
    For any failed model, the router SHALL return the next model in priority order,
    or None if no fallback available.
    """
    # Sort models by priority for predictable fallback chain
    sorted_models = sorted(models, key=lambda m: m.priority, reverse=True)
    
    router = LLMRouter(models=sorted_models, strategy=RoutingStrategy.PRIORITY)
    
    # Test fallback for each model except the last
    for i in range(len(sorted_models) - 1):
        failed_model = sorted_models[i].name
        fallback = router.get_fallback(failed_model)
        
        # Should return next model in chain
        assert fallback is not None
        assert fallback == sorted_models[i + 1].name
    
    # Last model should have no fallback
    last_model = sorted_models[-1].name
    fallback = router.get_fallback(last_model)
    assert fallback is None


@given(
    models=st.lists(model_config_strategy(), min_size=3, max_size=5, unique_by=lambda m: m.name)
)
def test_property_fallback_chain_skips_unavailable(models):
    """
    Property: Fallback chain should skip models with open circuit breakers.
    """
    sorted_models = sorted(models, key=lambda m: m.priority, reverse=True)
    router = LLMRouter(
        models=sorted_models,
        strategy=RoutingStrategy.PRIORITY,
        enable_circuit_breakers=True
    )
    
    # Fail the second model multiple times to open its circuit
    if len(sorted_models) >= 3:
        second_model = sorted_models[1].name
        for _ in range(10):  # Exceed failure threshold
            router.record_failure(second_model)
        
        # Get fallback for first model
        first_model = sorted_models[0].name
        fallback = router.get_fallback(first_model)
        
        # Should skip second model (circuit open) and go to third
        if len(sorted_models) >= 3:
            assert fallback == sorted_models[2].name


@given(
    models=st.lists(model_config_strategy(), min_size=2, max_size=5, unique_by=lambda m: m.name)
)
def test_property_fallback_records_failure(models):
    """
    Property: Getting fallback should record failure for the failed model.
    """
    router = LLMRouter(models=models, enable_stats=True)
    
    failed_model = models[0].name
    
    # Get initial stats
    initial_stats = router.get_stats(failed_model)
    initial_failures = initial_stats.failed_requests if initial_stats else 0
    
    # Get fallback
    router.get_fallback(failed_model)
    
    # Failure should be recorded
    updated_stats = router.get_stats(failed_model)
    assert updated_stats is not None
    assert updated_stats.failed_requests == initial_failures + 1


@given(
    models=st.lists(model_config_strategy(), min_size=1, max_size=5, unique_by=lambda m: m.name)
)
def test_property_fallback_for_unknown_model(models):
    """
    Property: Fallback for unknown model should return first available model or None.
    """
    router = LLMRouter(models=models)
    
    # Try to get fallback for non-existent model
    fallback = router.get_fallback("unknown-model-xyz")
    
    # Should return None (model not in chain)
    assert fallback is None


@given(
    models=st.lists(model_config_strategy(), min_size=2, max_size=5, unique_by=lambda m: m.name)
)
def test_property_multiple_fallbacks_chain(models):
    """
    Property: Multiple fallbacks should traverse the entire chain.
    """
    sorted_models = sorted(models, key=lambda m: m.priority, reverse=True)
    router = LLMRouter(models=sorted_models)
    
    # Start with first model and follow fallback chain
    current = sorted_models[0].name
    visited = [current]
    
    while True:
        fallback = router.get_fallback(current)
        if fallback is None:
            break
        visited.append(fallback)
        current = fallback
    
    # Should have visited all models in priority order
    expected = [m.name for m in sorted_models]
    assert visited == expected


# =============================================================================
# Additional Properties
# =============================================================================

@given(
    models=st.lists(model_config_strategy(), min_size=1, max_size=5, unique_by=lambda m: m.name)
)
def test_property_circuit_breaker_state_transitions(models):
    """
    Property: Circuit breaker should transition through states correctly.
    """
    router = LLMRouter(models=models, enable_circuit_breakers=True)
    
    model_name = models[0].name
    
    # Initial state should be CLOSED
    state = router.get_circuit_state(model_name)
    assert state == CircuitState.CLOSED
    
    # Record multiple failures to open circuit
    for _ in range(10):
        router.record_failure(model_name)
    
    # State should be OPEN
    state = router.get_circuit_state(model_name)
    assert state == CircuitState.OPEN


@given(
    models=st.lists(model_config_strategy(), min_size=1, max_size=5, unique_by=lambda m: m.name),
    prompt=st.text(min_size=10, max_size=100)
)
def test_property_routing_decision_recorded(models, prompt):
    """
    Property: Every routing decision should be recorded for audit.
    """
    router = LLMRouter(models=models)
    
    # Get initial decision count
    initial_decisions = len(router.get_recent_decisions())
    
    # Make selection
    router.select(prompt)
    
    # Decision should be recorded
    updated_decisions = len(router.get_recent_decisions())
    assert updated_decisions == initial_decisions + 1
    
    # Latest decision should contain the prompt context
    latest = router.get_recent_decisions()[-1]
    assert latest.selected_model in [m.name for m in models]


@given(
    models=st.lists(model_config_strategy(), min_size=1, max_size=5, unique_by=lambda m: m.name)
)
def test_property_stats_accumulation(models):
    """
    Property: Stats should accumulate correctly over multiple requests.
    """
    router = LLMRouter(models=models, enable_stats=True)
    
    model_name = models[0].name
    
    # Record multiple successes
    for i in range(5):
        router.record_success(model_name, latency_ms=100.0 + i, tokens_in=10, tokens_out=20)
    
    # Check stats
    stats = router.get_stats(model_name)
    assert stats is not None
    assert stats.total_requests == 5
    assert stats.successful_requests == 5
    assert stats.total_tokens_in == 50
    assert stats.total_tokens_out == 100
    assert stats.success_rate == 1.0
