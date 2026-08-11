"""
Simple TIER 1 production validation test
Tests the core validation without complex mocking
"""

import pytest


def test_reasoning_config_has_strict_default():
    """Test that ReasoningConfig defaults to STRICT mode"""
    from mahoun.reasoning.reasoning_chain import ReasoningConfig, ReasoningMode
    
    config = ReasoningConfig()
    assert config.mode == ReasoningMode.STRICT, f"Expected STRICT, got {config.mode}"


def test_reasoning_chain_has_atomic_counters():
    """Test that ReasoningChain uses thread-safe atomic counters"""
    from mahoun.reasoning.reasoning_chain import ReasoningChain
    import inspect
    
    source = inspect.getsource(ReasoningChain)
    assert 'AtomicCounter' in source, "ReasoningChain should use AtomicCounter"
    assert 'AtomicFloat' in source, "ReasoningChain should use AtomicFloat"


def test_reasoning_chain_has_nli_verification():
    """Test that NLI verification method exists"""
    from mahoun.reasoning.reasoning_chain import ReasoningChain
    import inspect
    
    source = inspect.getsource(ReasoningChain)
    assert '_verify_nli' in source, "ReasoningChain should have _verify_nli method"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])