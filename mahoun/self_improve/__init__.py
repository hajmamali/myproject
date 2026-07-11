"""self_improve package — INTENTIONALLY DISABLED FOR RELEASE.

Per AGENTS.md, this module exists only to preserve historical analysis
and baseline reports. It is NOT to be used, extended, or imported from
production code paths. The conditional imports below are wrapped in
try/except to make the module inert: any import failure (e.g. missing
pandas/torch) silently disables the entire subsystem.

Do NOT add new callers from production code.
"""

# Hard disable: require an explicit opt-in via env var to even attempt
# loading the subsystem. This is the "belt and suspenders" safeguard.
import os as _os

_SELF_IMPROVE_DISABLED = _os.environ.get("MAHOUN_ENABLE_SELF_IMPROVE", "").lower() not in (
    "1",
    "true",
    "yes",
)

__all__: list[str] = []


if _SELF_IMPROVE_DISABLED:
    # Module is intentionally inert. All symbols resolve to None.
    UltraSelfImprovementSystem = None  # type: ignore[assignment]
    UltraRLAgent = None  # type: ignore[assignment]
    UltraActiveLearner = None  # type: ignore[assignment]
    UltraBanditSystem = None  # type: ignore[assignment]
    UnifiedPerformanceMonitor = None  # type: ignore[assignment]
    CausalABBridge = None  # type: ignore[assignment]
    UltraSelfImproveIntegration = None  # type: ignore[assignment]
else:
    # Opt-in path (for historical/audit runs only — not production).
    try:
        from .ultra_self_improvement_system import UltraSelfImprovementSystem
        from .ultra_rl_agent import UltraRLAgent
        from .ultra_active_learning import UltraActiveLearner
        from .ultra_bandit_system import UltraBanditSystem
        from .ultra_performance_monitoring import UltraPerformanceMonitor as UnifiedPerformanceMonitor
        from .ultra_causal_ab_integration import UltraCausalABIntegration as CausalABBridge
        from .ultra_self_improve_integration import UltraSelfImproveIntegration
    except ImportError:
        UltraSelfImprovementSystem = None  # type: ignore[assignment]
        UltraRLAgent = None  # type: ignore[assignment]
        UltraActiveLearner = None  # type: ignore[assignment]
        UltraBanditSystem = None  # type: ignore[assignment]
        UnifiedPerformanceMonitor = None  # type: ignore[assignment]
        CausalABBridge = None  # type: ignore[assignment]
        UltraSelfImproveIntegration = None  # type: ignore[assignment]
