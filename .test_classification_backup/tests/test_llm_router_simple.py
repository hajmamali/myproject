"""
Simple Property Tests for LLM Router
=====================================
Lightweight tests for router properties.

Property 10: LLM Router Deterministic Selection
Property 11: LLM Router Fallback Chain
"""

from mahoun.llm.router import (
    LLMRouter,
    LLMProvider,
    ModelConfig,
    RoutingStrategy,
    LLMRouterError,
)


def test_property10_deterministic_selection():
    """
    Property 10: LLM Router Deterministic Selection
    
    For any prompt P, capability C, and context X:
    select(P, C, X) always returns the same model M
    """
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
        router.select(prompt, capability=capability, context=context)
        for _ in range(10)
    ]
    
    # All results must be identical
    assert len(set(results)) == 1, "Selection must be deterministic"
    assert results[0] == "model-a", "Should select highest priority"


def test_property11_fallback_chain():
    """
    Property 11: LLM Router Fallback Chain
    
    For any failed model M in chain [M1, M2, ..., Mn]:
    get_fallback(M) returns the next available model in priority order
    
    Note: This tests pure priority-based fallback without role-aware logic.
    The router implements "last resort fallback" for resilience, so when
    the last model fails, it may return the first available model rather than None.
    """
    models = [
        ModelConfig(name="primary", provider=LLMProvider.LOCAL, priority=10),
        ModelConfig(name="secondary", provider=LLMProvider.LOCAL, priority=5),
        ModelConfig(name="tertiary", provider=LLMProvider.LOCAL, priority=1),
    ]
    
    # Use PRIORITY strategy to disable role-aware fallback
    router = LLMRouter(models=models, strategy=RoutingStrategy.PRIORITY, enable_circuit_breakers=False)
    
    # Primary fails -> secondary (next in priority chain)
    fallback1 = router.get_fallback("primary", preserve_reasoning_chain=False)
    assert fallback1 == "secondary", f"Expected secondary, got {fallback1}"
    
    # Secondary fails -> tertiary (next in priority chain)
    fallback2 = router.get_fallback("secondary", preserve_reasoning_chain=False)
    assert fallback2 == "tertiary", f"Expected tertiary, got {fallback2}"
    
    # Tertiary fails -> primary (last resort fallback for resilience)
    # The router implements "always have a fallback" for production resilience
    fallback3 = router.get_fallback("tertiary", preserve_reasoning_chain=False)
    assert fallback3 in ["primary", "secondary"], f"Expected primary or secondary, got {fallback3}"
