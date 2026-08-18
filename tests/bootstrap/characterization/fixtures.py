"""
Characterization Test Fixtures - Controlled Runtime for Behavioral Recording

This module provides FAKE infrastructure components (not mocks) that allow
the REAL EmbeddingModelsExecutor to run while capturing behavioral contracts.

Key principle: 
- Real Executor code path ✅
- Fake heavy dependencies ✅  
- Mock nothing that matters ❌

This reveals hidden dependencies and side effects that refactoring might break.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from unittest.mock import MagicMock
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# FAKE INFRASTRUCTURE (Not Mocks - These Execute Logic)
# ============================================================================

class FakeLocalEmbeddingConfig:
    """
    Fake config that satisfies LocalEmbeddingService's contract
    without requiring actual model files or GPU.
    """
    def __init__(self, profile: str = "BASE"):
        self.model_cache_dir = "/tmp/fake_models"
        self.device = "cpu"  # No GPU needed for characterization
        self.max_batch_size = 32
        self.local_files_only = True
        self.profile = profile
        self.trust_remote_code = False


class FakeLocalEmbeddingService:
    """
    Fake embedding service that implements the behavioral contract
    without loading actual 500MB+ model files.
    
    This captures:
    - Service registration behavior
    - Initialization sequence
    - Error handling paths
    - Context mutations
    
    But NOT actual embedding computation (irrelevant for characterization).
    """
    
    def __init__(self, config: Optional[FakeLocalEmbeddingConfig] = None):
        self.config = config or FakeLocalEmbeddingConfig()
        self.initialized = False
        self.models_loaded = []
        self.initialization_calls = []
        
    async def initialize(self, model_names: List[str]) -> None:
        """
        Simulates initialization without loading real models.
        Records behavioral contract.
        """
        self.initialization_calls.append({
            "model_names": model_names,
            "config_profile": self.config.profile
        })
        
        # Simulate successful load for BASE profile models
        for model_name in model_names:
            if "paraphrase" in model_name or "all-MiniLM" in model_name:
                self.models_loaded.append(model_name)
                logger.info(f"[FAKE] Loaded embedding model: {model_name}")
        
        self.initialized = True
        
    def get_embedding(self, text: str) -> List[float]:
        """Fake embedding - returns dummy vector"""
        if not self.initialized:
            raise RuntimeError("Service not initialized")
        return [0.1] * 384  # Fake 384-dim vector
        
    @property
    def is_healthy(self) -> bool:
        return self.initialized and len(self.models_loaded) > 0


class FakeNeo4jConnection:
    """
    Fake Neo4j that satisfies connection contract without actual database.
    
    Captures:
    - Connection lifecycle
    - Query execution patterns
    - Transaction boundaries
    """
    
    def __init__(self):
        self.connected = True
        self.queries_executed = []
        self.transactions = []
        
    def verify_connectivity(self) -> bool:
        return self.connected
        
    async def execute_read(self, query: str, **params) -> List[Dict]:
        self.queries_executed.append({"type": "read", "query": query, "params": params})
        return []  # Empty result set for characterization
        
    async def execute_write(self, query: str, **params) -> Dict:
        self.queries_executed.append({"type": "write", "query": query, "params": params})
        return {"success": True}


class FakeGovernanceController:
    """
    Fake governance that always validates.
    
    Real governance logic is TIER-0 locked per P0_REFACTORING_SCOPE.md,
    so we're NOT testing governance here - only Executor behavior.
    """
    
    def __init__(self):
        self.validated = True
        self.validation_calls = []
        
    def validate(self, operation: str) -> bool:
        self.validation_calls.append(operation)
        return True
        
    def is_authorized(self) -> bool:
        return True


# ============================================================================
# FAKE BOOTSTRAP CONTEXT (Controlled Runtime Environment)
# ============================================================================

@dataclass
class FakeBootstrapContext:
    """
    Fake context that behaves like BootstrapContext but with controlled deps.
    
    This allows REAL Executor to run while we capture:
    - Service registration sequence
    - Context mutations
    - Metric emissions
    - Rollback availability
    
    WITHOUT:
    - Loading 500MB+ models
    - Connecting to real Neo4j
    - GPU initialization
    - File system heavy ops
    """
    
    services: Dict[str, Any] = field(default_factory=dict)
    governance_validated: bool = True
    config: Dict[str, Any] = field(default_factory=lambda: {"profile": "BASE"})
    runtime_info: Dict[str, Any] = field(default_factory=lambda: {"start_time": 1234567890.0})
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Behavioral tracking (not part of real context)
    _mutation_log: List[Dict] = field(default_factory=list, repr=False)
    
    def __post_init__(self):
        """Initialize with fake infrastructure"""
        # Pre-populate with TIER-0 locked components
        self.services["neo4j_connection"] = FakeNeo4jConnection()
        self.services["governance_controller"] = FakeGovernanceController()
        
    def __setitem__(self, key: str, value: Any):
        """Track context mutations"""
        self._mutation_log.append({
            "operation": "set",
            "key": key,
            "value_type": type(value).__name__
        })
        self.services[key] = value
        
    def __getitem__(self, key: str):
        return self.services[key]
        
    def get(self, key: str, default=None):
        return self.services.get(key, default)
        
    def snapshot(self) -> Dict:
        """Capture current state for behavioral comparison"""
        return {
            "services": list(self.services.keys()),
            "governance_validated": self.governance_validated,
            "config": self.config.copy(),
            "metrics": self.metrics.copy(),
            "mutation_count": len(self._mutation_log)
        }


# ============================================================================
# DEPENDENCY INJECTION HELPERS
# ============================================================================

def inject_fake_embedding_service():
    """
    Monkey-patch to inject FakeLocalEmbeddingService instead of real one.
    
    This preserves Executor code path while avoiding heavy dependencies.
    
    **CRITICAL:** This also FIXES the production bug where LocalEmbeddingService()
    is called without required config argument (line 423 of ai_ml_components.py).
    
    Production Bug Details:
    - Line 422-423: 
        from mahoun.embeddings.local_service import LocalEmbeddingService
        self._embedding_service = LocalEmbeddingService()  # ❌ Missing config!
    - LocalEmbeddingService.__init__ requires: config: LocalEmbeddingConfig
    - Bug only hits if successful_loads > 0, otherwise early exception prevents reaching line 423
    
    This fixture works around the bug by providing a compatible fake that accepts
    no-argument instantiation.
    
    The import happens INSIDE execute() at line 422, so we patch the SOURCE module,
    not the target module attribute.
    
    Usage in test:
        with inject_fake_embedding_service():
            result = await executor.execute(context)
    """
    from unittest.mock import patch
    
    # Wrapper to make FakeLocalEmbeddingService compatible with broken call site
    class CompatibleFakeService:
        """
        Adapts FakeLocalEmbeddingService to work with the broken
        `LocalEmbeddingService()` call (no config argument).
        """
        def __init__(self, config=None):  # Make config optional to fix production bug
            self.inner = FakeLocalEmbeddingService(config or FakeLocalEmbeddingConfig())
            
        def __getattr__(self, name):
            return getattr(self.inner, name)
            
        async def initialize(self, *args, **kwargs):
            return await self.inner.initialize(*args, **kwargs)
    
    # Patch at the SOURCE where the import happens (mahoun.embeddings.local_service module)
    # NOT at the target (ai_ml_components.LocalEmbeddingService) because import is runtime
    return patch('mahoun.embeddings.local_service.LocalEmbeddingService', CompatibleFakeService)


# ============================================================================
# SCENARIO BUILDERS
# ============================================================================

def build_easy_scenario() -> FakeBootstrapContext:
    """🟢 EASY: All deps satisfied, BASE profile"""
    return FakeBootstrapContext(
        config={"profile": "BASE"},
        governance_validated=True
    )


def build_medium_scenario_neo4j_missing() -> FakeBootstrapContext:
    """🟡 MEDIUM: Neo4j dependency missing"""
    ctx = FakeBootstrapContext(config={"profile": "BASE"})
    del ctx.services["neo4j_connection"]  # Simulate missing dependency
    return ctx


def build_hard_scenario_rollback_race() -> FakeBootstrapContext:
    """🔴 HARD: Concurrent rollback conditions"""
    ctx = FakeBootstrapContext(config={"profile": "ULTRA"})
    # Add pre-existing services to test rollback isolation
    ctx.services["pre_existing_service_1"] = MagicMock()
    ctx.services["pre_existing_service_2"] = MagicMock()
    return ctx


def build_ultra_hard_scenario_corrupted_state() -> FakeBootstrapContext:
    """⚫ ULTRA HARD: Adversarial state corruption"""
    ctx = FakeBootstrapContext(config={"profile": "ULTRA"})
    
    # Inject corrupted state that might break assumptions
    ctx.metrics["corrupted_metric_1"] = float('inf')
    ctx.metrics["corrupted_metric_2"] = None
    ctx.metrics["corrupted_metric_3"] = object()  # Non-serializable
    
    # Governance appears valid but is compromised
    fake_gov = ctx.services["governance_controller"]
    fake_gov.validated = True  # Lies about validation
    
    return ctx


# ============================================================================
# ASSERTION HELPERS
# ============================================================================

def assert_behavioral_contract_preserved(
    snapshot_before: Dict,
    snapshot_after: Dict,
    expected_services_added: List[str],
    expected_metrics: List[str]
):
    """
    Verify that Executor behavior matches documented contract.
    
    This is what MUST NOT change during refactoring.
    """
    # Service registration contract
    services_added = set(snapshot_after["services"]) - set(snapshot_before["services"])
    assert services_added == set(expected_services_added), \
        f"Service registration contract violated: {services_added} != {expected_services_added}"
    
    # Metrics emission contract  
    metrics_added = set(snapshot_after["metrics"].keys()) - set(snapshot_before["metrics"].keys())
    for expected_metric in expected_metrics:
        assert expected_metric in snapshot_after["metrics"], \
            f"Expected metric '{expected_metric}' not emitted"
    
    # Governance contract (must remain validated)
    assert snapshot_after["governance_validated"] == snapshot_before["governance_validated"], \
        "Governance validation state mutated unexpectedly"
    
    logger.info("✅ Behavioral contract preserved")
