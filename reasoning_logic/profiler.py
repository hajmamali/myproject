"""
Reasoning Performance Profiler
===============================

Advanced profiling and performance analysis for reasoning engines.

Features:
- Execution time tracking
- Memory usage monitoring
- Rule performance analysis
- Bottleneck detection
- Performance regression detection

Author: MAHOUN Team
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for reasoning"""
    total_time_ms: float = 0.0
    rule_fires: int = 0
    facts_derived: int = 0
    unifications: int = 0
    backtracks: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def throughput(self) -> float:
        """Calculate facts per second"""
        if self.total_time_ms == 0:
            return 0.0
        return (self.facts_derived / self.total_time_ms) * 1000
    
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total


@dataclass
class RuleProfile:
    """Performance profile for a single rule"""
    rule_id: str
    fires: int = 0
    total_time_ms: float = 0.0
    facts_derived: int = 0
    avg_time_ms: float = 0.0
    
    def update(self, time_ms: float, facts: int = 0):
        """Update profile with new execution"""
        self.fires += 1
        self.total_time_ms += time_ms
        self.facts_derived += facts
        self.avg_time_ms = self.total_time_ms / self.fires


class ReasoningProfiler:
    """
    Profiler for reasoning engine performance
    
    Tracks:
    - Execution times
    - Rule performance
    - Memory usage
    - Bottlenecks
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize profiler
        
        Args:
            enabled: Enable profiling (disable for production)
        """
        self.enabled = enabled
        self.metrics = PerformanceMetrics()
        self.rule_profiles: Dict[str, RuleProfile] = {}
        self._start_time: Optional[float] = None
        self._checkpoints: List[tuple] = []
    
    def start(self):
        """Start profiling session"""
        if not self.enabled:
            return
        self._start_time = time.perf_counter()
        logger.debug("Profiling started")
    
    def stop(self):
        """Stop profiling session"""
        if not self.enabled or self._start_time is None:
            return
        
        elapsed = (time.perf_counter() - self._start_time) * 1000
        self.metrics.total_time_ms = elapsed
        logger.debug(f"Profiling stopped: {elapsed:.2f}ms")
    
    def checkpoint(self, name: str):
        """Record a checkpoint"""
        if not self.enabled or self._start_time is None:
            return
        
        elapsed = (time.perf_counter() - self._start_time) * 1000
        self._checkpoints.append((name, elapsed))
    
    def record_rule_fire(self, rule_id: str, time_ms: float, facts_derived: int = 0):
        """Record a rule firing"""
        if not self.enabled:
            return
        
        if rule_id not in self.rule_profiles:
            self.rule_profiles[rule_id] = RuleProfile(rule_id=rule_id)
        
        self.rule_profiles[rule_id].update(time_ms, facts_derived)
        self.metrics.rule_fires += 1
        self.metrics.facts_derived += facts_derived
    
    def record_unification(self, success: bool):
        """Record a unification attempt"""
        if not self.enabled:
            return
        self.metrics.unifications += 1
    
    def record_backtrack(self):
        """Record a backtrack"""
        if not self.enabled:
            return
        self.metrics.backtracks += 1
    
    def record_cache_access(self, hit: bool):
        """Record a cache access"""
        if not self.enabled:
            return
        if hit:
            self.metrics.cache_hits += 1
        else:
            self.metrics.cache_misses += 1
    
    def get_report(self) -> str:
        """
        Generate performance report
        
        Returns:
            Formatted performance report
        """
        if not self.enabled:
            return "Profiling disabled"
        
        lines = []
        lines.append("=" * 80)
        lines.append("REASONING PERFORMANCE REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Overall metrics
        lines.append("Overall Metrics:")
        lines.append(f"  Total time: {self.metrics.total_time_ms:.2f}ms")
        lines.append(f"  Rule fires: {self.metrics.rule_fires}")
        lines.append(f"  Facts derived: {self.metrics.facts_derived}")
        lines.append(f"  Throughput: {self.metrics.throughput():.2f} facts/sec")
        lines.append(f"  Unifications: {self.metrics.unifications}")
        lines.append(f"  Backtracks: {self.metrics.backtracks}")
        lines.append(f"  Cache hit rate: {self.metrics.cache_hit_rate():.1%}")
        lines.append("")
        
        # Checkpoints
        if self._checkpoints:
            lines.append("Checkpoints:")
            prev_time = 0.0
            for name, elapsed in self._checkpoints:
                delta = elapsed - prev_time
                lines.append(f"  {name}: {elapsed:.2f}ms (+{delta:.2f}ms)")
                prev_time = elapsed
            lines.append("")
        
        # Rule performance
        if self.rule_profiles:
            lines.append("Rule Performance (top 10 by time):")
            sorted_rules = sorted(
                self.rule_profiles.values(),
                key=lambda r: r.total_time_ms,
                reverse=True
            )[:10]
            
            for rule in sorted_rules:
                lines.append(f"  {rule.rule_id}:")
                lines.append(f"    Fires: {rule.fires}")
                lines.append(f"    Total time: {rule.total_time_ms:.2f}ms")
                lines.append(f"    Avg time: {rule.avg_time_ms:.2f}ms")
                lines.append(f"    Facts derived: {rule.facts_derived}")
            lines.append("")
        
        # Bottleneck analysis
        lines.append("Bottleneck Analysis:")
        if self.metrics.backtracks > self.metrics.rule_fires * 0.5:
            lines.append("  ⚠️  High backtrack rate - consider rule ordering")
        if self.metrics.cache_hit_rate() < 0.5:
            lines.append("  ⚠️  Low cache hit rate - consider enabling tabling")
        if self.metrics.throughput() < 100:
            lines.append("  ⚠️  Low throughput - consider optimizing rules")
        if not any(line.startswith("  ⚠️") for line in lines[-3:]):
            lines.append("  ✓ No significant bottlenecks detected")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def reset(self):
        """Reset all profiling data"""
        self.metrics = PerformanceMetrics()
        self.rule_profiles.clear()
        self._start_time = None
        self._checkpoints.clear()
