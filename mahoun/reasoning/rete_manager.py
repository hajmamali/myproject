"""
Rete Algorithm Manager
======================

Classification: CRITICAL / PERFORMANCE / OPTIONAL
Purpose: Manage Rete algorithm integration with fallback and monitoring

This module provides:
- Safe integration of Rete algorithm into production
- Feature flag control (MAHOUN_USE_RETE)
- Automatic fallback to traditional ForwardChaining on failure
- Performance monitoring and metrics
- Memory usage tracking
- Equivalence validation with traditional engine

Architecture:
    ReteManager
        ├── try ReteForwardChaining (if enabled)
        ├── fallback to ForwardChaining on failure
        ├── monitor performance and memory
        └── validate equivalence (optional)

Feature Flags:
    MAHOUN_USE_RETE=true/false - Enable/disable Rete (default: false for safety)
    MAHOUN_RETE_MAX_MEMORY=10000 - Maximum memory items before fallback (default: 10000)
    MAHOUN_RETE_VALIDATE_EQUIVALENCE=true/false - Validate Rete vs ForwardChaining (default: false)

Author: MAHOUN Team
Version: 1.0.0
"""

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from reasoning_logic import (
    ForwardChaining,
    ForwardChainingStats,
    KnowledgeBase,
    ReteForwardChaining,
)
from reasoning_logic.core import Fact, Rule

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class ReteMode(str, Enum):
    """Rete algorithm operational modes"""
    DISABLED = "disabled"        # Always use traditional ForwardChaining
    ENABLED = "enabled"          # Use Rete when possible, fallback on failure
    FORCED = "forced"           # Always use Rete, fail if not possible
    VALIDATED = "validated"      # Use Rete with equivalence validation


@dataclass
class ReteConfig:
    """Configuration for Rete algorithm manager"""
    mode: ReteMode = ReteMode.ENABLED
    max_memory_items: int = 10000
    validate_equivalence: bool = False
    fallback_on_failure: bool = True
    max_execution_time_ms: float = 5000.0  # 5 seconds
    
    @classmethod
    def from_environment(cls) -> "ReteConfig":
        """Load configuration from environment variables"""
        mode_str = os.environ.get("MAHOUN_USE_RETE", "enabled").lower()
        
        # Map environment strings to ReteMode
        mode_map = {
            "true": ReteMode.ENABLED,
            "1": ReteMode.ENABLED,
            "enabled": ReteMode.ENABLED,
            "false": ReteMode.DISABLED,
            "0": ReteMode.DISABLED,
            "disabled": ReteMode.DISABLED,
            "forced": ReteMode.FORCED,
            "forced=true": ReteMode.FORCED,
            "validated": ReteMode.VALIDATED,
        }
        mode = mode_map.get(mode_str, ReteMode.ENABLED)
        
        max_memory = int(os.environ.get("MAHOUN_RETE_MAX_MEMORY", "10000"))
        validate_eq = os.environ.get("MAHOUN_RETE_VALIDATE_EQUIVALENCE", "false").lower() == "true"
        fallback = os.environ.get("MAHOUN_RETE_FALLBACK", "true").lower() == "true"
        max_time = float(os.environ.get("MAHOUN_RETE_MAX_TIME_MS", "5000"))
        
        return cls(
            mode=mode,
            max_memory_items=max_memory,
            validate_equivalence=validate_eq,
            fallback_on_failure=fallback,
            max_execution_time_ms=max_time,
        )


# ============================================================================
# Execution Metrics
# ============================================================================

@dataclass
class ReteExecutionMetrics:
    """Metrics for Rete execution monitoring"""
    algorithm: str = "unknown"  # "rete" or "forward_chaining"
    execution_time_ms: float = 0.0
    facts_derived: int = 0
    iterations: int = 0
    rules_fired: int = 0
    memory_usage: Dict[str, int] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    fallback_triggered: bool = False
    equivalence_validated: bool = False
    equivalence_differences: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization"""
        return {
            "algorithm": self.algorithm,
            "execution_time_ms": round(self.execution_time_ms, 3),
            "facts_derived": self.facts_derived,
            "iterations": self.iterations,
            "rules_fired": self.rules_fired,
            "memory_usage": self.memory_usage,
            "success": self.success,
            "error": self.error,
            "fallback_triggered": self.fallback_triggered,
            "equivalence_validated": self.equivalence_validated,
            "equivalence_differences": self.equivalence_differences,
        }


# ============================================================================
# Rete Manager Core
# ============================================================================

class ReteManager:
    """
    Manager for Rete algorithm integration with safety features.
    
    Provides:
    - Safe execution with fallback
    - Performance monitoring
    - Memory tracking
    - Optional equivalence validation
    - Configurable behavior
    
    Usage:
        manager = ReteManager(config=ReteConfig.from_environment())
        
        # Execute with automatic algorithm selection
        metrics = manager.execute(kb, timeout_seconds=30)
        
        # Get derived facts
        derived_facts = manager.get_derived_facts()
        
        # Check if Rete was used
        if metrics.algorithm == "rete":
            print(f"Rete executed in {metrics.execution_time_ms}ms")
    """
    
    def __init__(self, config: Optional[ReteConfig] = None):
        """
        Initialize Rete Manager.
        
        Args:
            config: Rete configuration (defaults to environment-based config)
        """
        self.config = config or ReteConfig.from_environment()
        self._last_metrics: Optional[ReteExecutionMetrics] = None
        self._last_derived_facts: List[Fact] = []
        self._last_stats: Optional[ForwardChainingStats] = None
        
        # Statistics
        self.stats = {
            "total_executions": 0,
            "rete_executions": 0,
            "forward_chaining_executions": 0,
            "fallbacks": 0,
            "errors": 0,
            "equivalence_failures": 0,
        }
        
        logger.info(
            f"ReteManager initialized: mode={self.config.mode.value}, "
            f"max_memory={self.config.max_memory_items}, "
            f"validate_equivalence={self.config.validate_equivalence}, "
            f"fallback_on_failure={self.config.fallback_on_failure}"
        )
    
    def execute(
        self, 
        kb: KnowledgeBase, 
        timeout_seconds: int = 0,
        max_iterations: int = 1000
    ) -> ReteExecutionMetrics:
        """
        Execute forward chaining with Rete (if enabled) and fallback support.
        
        Args:
            kb: Knowledge base with facts and rules
            timeout_seconds: Timeout in seconds (0 = no timeout)
            max_iterations: Maximum iterations
            
        Returns:
            Execution metrics including algorithm used, performance, and results
        """
        self.stats["total_executions"] += 1
        start_time = time.perf_counter()
        
        # Determine which algorithm to use
        use_rete = self._should_use_rete()
        metrics = ReteExecutionMetrics(algorithm="forward_chaining")
        
        try:
            if use_rete:
                metrics = self._execute_with_rete(kb, timeout_seconds, max_iterations)
                self.stats["rete_executions"] += 1
            else:
                metrics = self._execute_with_forward_chaining(kb, timeout_seconds, max_iterations)
                self.stats["forward_chaining_executions"] += 1
                
        except Exception as e:
            logger.error(f"Rete/ForwardChaining execution failed: {e}")
            metrics.success = False
            metrics.error = str(e)
            self.stats["errors"] += 1
            
            # Fallback if configured
            if self.config.fallback_on_failure and use_rete:
                logger.warning("Falling back to ForwardChaining after Rete failure")
                metrics = self._execute_with_forward_chaining(kb, timeout_seconds, max_iterations)
                metrics.fallback_triggered = True
                self.stats["fallbacks"] += 1
        
        metrics.execution_time_ms = (time.perf_counter() - start_time) * 1000
        self._last_metrics = metrics
        
        # Log execution
        logger.debug(
            f"ReteManager execution completed: "
            f"algorithm={metrics.algorithm}, "
            f"time={metrics.execution_time_ms:.2f}ms, "
            f"facts_derived={metrics.facts_derived}, "
            f"success={metrics.success}"
        )
        
        return metrics
    
    def _should_use_rete(self) -> bool:
        """Determine if Rete should be used based on configuration"""
        if self.config.mode == ReteMode.DISABLED:
            return False
        if self.config.mode == ReteMode.FORCED:
            return True
        return True  # Default to enabled for ENABLED and VALIDATED modes
    
    def _execute_with_rete(
        self, 
        kb: KnowledgeBase, 
        timeout_seconds: int = 0,
        max_iterations: int = 1000
    ) -> ReteExecutionMetrics:
        """Execute using Rete algorithm"""
        metrics = ReteExecutionMetrics(algorithm="rete")
        
        try:
            # Create Rete engine
            rete_engine = ReteForwardChaining(kb.rules)
            
            # Execute
            derived_facts = rete_engine.run(kb.facts, max_iterations)
            
            # Get memory usage
            if hasattr(rete_engine, 'network') and hasattr(rete_engine.network, 'get_memory_usage'):
                metrics.memory_usage = rete_engine.network.get_memory_usage()
            
            # Check memory limit
            total_memory = metrics.memory_usage.get('total_memory_items', 0)
            if total_memory > self.config.max_memory_items:
                logger.warning(
                    f"Rete memory usage exceeded limit: {total_memory} > {self.config.max_memory_items}"
                )
                metrics.fallback_triggered = True
                if self.config.fallback_on_failure:
                    return self._execute_with_forward_chaining(kb, timeout_seconds, max_iterations)
            
            # Store results
            metrics.facts_derived = len(derived_facts)
            metrics.iterations = 1  # Rete doesn't iterate like traditional FC
            metrics.success = True
            self._last_derived_facts = derived_facts
            
            # Validate equivalence if configured
            if self.config.validate_equivalence:
                self._validate_equivalence(kb, derived_facts, metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Rete execution failed: {e}")
            metrics.success = False
            metrics.error = str(e)
            raise
    
    def _execute_with_forward_chaining(
        self, 
        kb: KnowledgeBase, 
        timeout_seconds: int = 0,
        max_iterations: int = 1000
    ) -> ReteExecutionMetrics:
        """Execute using traditional ForwardChaining"""
        metrics = ReteExecutionMetrics(algorithm="forward_chaining")
        
        try:
            # Create traditional engine (with use_rete=False to ensure non-Rete)
            fc_engine = ForwardChaining(
                kb, 
                max_iterations=max_iterations,
                enable_profiling=False,
                use_rete=False  # Force traditional algorithm
            )
            
            # Execute
            stats = fc_engine.run(timeout_seconds=timeout_seconds)
            
            # Store results
            metrics.facts_derived = stats.facts_derived
            metrics.iterations = stats.iterations
            metrics.rules_fired = stats.rules_fired
            metrics.success = True
            self._last_derived_facts = fc_engine.derived_facts
            self._last_stats = stats
            
            return metrics
            
        except Exception as e:
            logger.error(f"ForwardChaining execution failed: {e}")
            metrics.success = False
            metrics.error = str(e)
            raise
    
    def _validate_equivalence(
        self, 
        kb: KnowledgeBase, 
        rete_facts: List[Fact],
        metrics: ReteExecutionMetrics
    ) -> None:
        """Validate that Rete produces equivalent results to traditional ForwardChaining"""
        try:
            logger.debug("Validating Rete equivalence with traditional ForwardChaining")
            
            # Run traditional ForwardChaining
            fc_engine = ForwardChaining(
                kb, 
                max_iterations=1000,
                enable_profiling=False,
                use_rete=False
            )
            fc_stats = fc_engine.run(timeout_seconds=0)
            fc_facts = fc_engine.derived_facts
            
            # Compare results (as sets of string representations for comparison)
            rete_fact_strs = {str(f) for f in rete_facts}
            fc_fact_strs = {str(f) for f in fc_facts}
            
            if rete_fact_strs == fc_fact_strs:
                metrics.equivalence_validated = True
                logger.debug("Rete equivalence validated: results match")
            else:
                metrics.equivalence_validated = False
                metrics.equivalence_differences = list(rete_fact_strs ^ fc_fact_strs)
                self.stats["equivalence_failures"] += 1
                logger.warning(
                    f"Rete equivalence validation failed. "
                    f"Differences: {metrics.equivalence_differences[:5]}"
                )
                
                # Fallback if equivalence fails
                if self.config.fallback_on_failure:
                    logger.warning("Falling back to ForwardChaining due to equivalence failure")
                    fc_metrics = self._execute_with_forward_chaining(kb)
                    metrics.algorithm = fc_metrics.algorithm
                    metrics.facts_derived = fc_metrics.facts_derived
                    metrics.fallback_triggered = True
                    self._last_derived_facts = fc_engine.derived_facts
                    
        except Exception as e:
            logger.error(f"Equivalence validation failed: {e}")
            metrics.equivalence_validated = False
            metrics.error = f"Equivalence validation error: {e}"
    
    def get_derived_facts(self) -> List[Fact]:
        """Get derived facts from last execution"""
        return self._last_derived_facts
    
    def get_last_stats(self) -> Optional[ForwardChainingStats]:
        """Get statistics from last execution"""
        return self._last_stats
    
    def get_last_metrics(self) -> Optional[ReteExecutionMetrics]:
        """Get metrics from last execution"""
        return self._last_metrics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics"""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset aggregate statistics"""
        self.stats = {
            "total_executions": 0,
            "rete_executions": 0,
            "forward_chaining_executions": 0,
            "fallbacks": 0,
            "errors": 0,
            "equivalence_failures": 0,
        }


# ============================================================================
# Convenience Functions
# ============================================================================

# Global ReteManager instance (lazy initialization)
_rete_manager: Optional[ReteManager] = None


def get_rete_manager() -> ReteManager:
    """Get or create the global ReteManager instance"""
    global _rete_manager
    if _rete_manager is None:
        _rete_manager = ReteManager()
    return _rete_manager


def reset_rete_manager() -> None:
    """Reset the global ReteManager instance"""
    global _rete_manager
    if _rete_manager is not None:
        _rete_manager.reset_stats()
    _rete_manager = None


# ============================================================================
# Safe ForwardChaining Wrapper
# ============================================================================

class SafeForwardChaining:
    """
    Drop-in replacement for ForwardChaining that uses Rete when configured.
    
    This class provides the same interface as ForwardChaining but automatically
    uses Rete algorithm when enabled via environment variables.
    
    Usage:
        # Instead of:
        # engine = ForwardChaining(kb, max_iterations=1000)
        # stats = engine.run(timeout_seconds=30)
        # derived_facts = engine.derived_facts
        
        # Use:
        engine = SafeForwardChaining(kb, max_iterations=1000)
        metrics = engine.run(timeout_seconds=30)
        derived_facts = engine.get_derived_facts()
    """
    
    def __init__(
        self, 
        kb: KnowledgeBase, 
        max_iterations: int = 1000,
        config: Optional[ReteConfig] = None
    ):
        """
        Initialize SafeForwardChaining.
        
        Args:
            kb: Knowledge base with facts and rules
            max_iterations: Maximum iterations
            config: Optional Rete configuration
        """
        self.kb = kb
        self.max_iterations = max_iterations
        self.config = config or ReteConfig.from_environment()
        self._manager = ReteManager(self.config)
        self._timeout_seconds = 0
    
    def run(self, timeout_seconds: int = 0) -> ReteExecutionMetrics:
        """
        Run forward chaining with Rete (if enabled).
        
        Args:
            timeout_seconds: Timeout in seconds
            
        Returns:
            Execution metrics
        """
        self._timeout_seconds = timeout_seconds
        return self._manager.execute(
            self.kb, 
            timeout_seconds=timeout_seconds,
            max_iterations=self.max_iterations
        )
    
    def get_derived_facts(self) -> List[Fact]:
        """Get derived facts from last execution"""
        return self._manager.get_derived_facts()
    
    def get_metrics(self) -> Optional[ReteExecutionMetrics]:
        """Get metrics from last execution"""
        return self._manager.get_last_metrics()
    
    def get_stats(self) -> Optional[ForwardChainingStats]:
        """Get ForwardChaining stats (for backward compatibility)"""
        metrics = self._manager.get_last_metrics()
        if metrics and metrics.algorithm == "forward_chaining":
            # Return a compatible ForwardChainingStats
            return ForwardChainingStats(
                iterations=metrics.iterations,
                rules_fired=metrics.rules_fired,
                facts_derived=metrics.facts_derived,
                execution_time_ms=metrics.execution_time_ms,
            )
        return None
    
    @property
    def derived_facts(self) -> List[Fact]:
        """Derived facts (for backward compatibility)"""
        return self.get_derived_facts()
    
    def infer(self) -> List[Fact]:
        """
        Infer new facts using forward chaining (backward compatibility).
        This method runs the engine and returns derived facts.
        """
        self.run(timeout_seconds=0)
        return self.get_derived_facts()


# ============================================================================
# Module Initialization
# ============================================================================

logger.info(
    "ReteManager module loaded: "
    f"MAHOUN_USE_RETE={os.environ.get('MAHOUN_USE_RETE', 'not set')}"
)
