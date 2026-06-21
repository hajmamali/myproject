"""
Orchestrator Module
===================

Manages and coordinates all self-improvement components.

Note: Lazy imports to prevent circular import issues
"""

__all__ = [
    "SelfImprovementOrchestrator",
    "OrchestratorState",
    "ComponentStatus",
    "run_e2e_smoke_test_desktop_minimal",
]

def __getattr__(name):
    """Lazy loading of orchestrator components"""
    if name in __all__:
        # Let ImportError propagate naturally (don't mask it with None)
        if name == "run_e2e_smoke_test_desktop_minimal":
            from .smoke_tests import run_e2e_smoke_test_desktop_minimal
            return run_e2e_smoke_test_desktop_minimal
        else:
            from .orchestrator import (
                SelfImprovementOrchestrator,
                OrchestratorState,
                ComponentStatus,
            )
            if name == "SelfImprovementOrchestrator":
                return SelfImprovementOrchestrator
            elif name == "OrchestratorState":
                return OrchestratorState
            elif name == "ComponentStatus":
                return ComponentStatus
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
