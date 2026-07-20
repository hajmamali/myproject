"""
Regression test: EvidenceLinkedVerdictEngine MUST be constructed with a real
ReasoningDependencyContainer, not container=None.

This regression was introduced when a prior remediation that changed
`container=None` to `container=ReasoningDependencyContainer()` at the API
factory site (api/routers/reasoning.py:get_verdict_engine) silently reverted.
Passing container=None disables dependency injection of the contradiction
detector (and the RAG service surface) used by the engine.

This test calls the actual FastAPI factory function used by the API rather
than a hand-constructed engine, so a future revert at the factory cannot slip
through. It runs in the default CI selection (no opt-in marker required).
"""

import pytest

from api.routers.reasoning import get_verdict_engine
from mahoun.reasoning.adapters import ReasoningDependencyContainer


@pytest.fixture
def _reset_engine():
    import api.routers.reasoning as mod

    saved = mod._verdict_engine
    mod._verdict_engine = None
    yield
    mod._verdict_engine = saved


def test_verdict_engine_container_not_none(_reset_engine, monkeypatch):
    """
    The factory used by the API MUST inject a non-None container whose type is
    ReasoningDependencyContainer. container=None is the regression we guard
    against.
    """
    # Force the factory down the production (non-DESKTOP_MINIMAL) branch.
    monkeypatch.setattr(
        "api.routers.reasoning.is_desktop_minimal", lambda: False
    )
    monkeypatch.setattr(
        "api.routers.reasoning.should_skip_graph", lambda: False
    )

    engine = get_verdict_engine()

    assert engine.container is not None, (
        "container is None — the API factory regressed to disabling "
        "ReasoningDependencyContainer injection for the verdict engine."
    )
    assert isinstance(engine.container, ReasoningDependencyContainer), (
        f"engine.container is {type(engine.container).__name__}, "
        "expected ReasoningDependencyContainer."
    )
