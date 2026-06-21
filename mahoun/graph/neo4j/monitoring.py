"""
Neo4j Monitoring and Metrics
=============================

Track performance and health metrics.
"""


import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np: Optional[Any] = None
@dataclass
class Neo4jMetrics:
    """Metrics tracker for Neo4j operations"""
    
    query_count: int = 0
    query_times: List[float] = field(default_factory=list)
    errors: int = 0
    slow_queries: int = 0
    slow_query_threshold: float = 1.0  # seconds
    
    def record_query(self, duration: float):
        """Record query execution time"""
        self.query_count += 1
        self.query_times.append(duration)
        
        if duration > self.slow_query_threshold:
            self.slow_queries += 1
    
    def record_error(self):
        """Record an error"""
        self.errors += 1
    
    def get_stats(self) -> Dict[str, float]:
        """Get statistics"""
        if not self.query_times:
            return {
                "query_count": 0,
                "errors": self.errors,
                "slow_queries": 0
            }
        
        result = {
            "query_count": self.query_count,
            "total_time": sum(self.query_times),
            "min_time": min(self.query_times),
            "max_time": max(self.query_times),
            "errors": self.errors,
            "error_rate": self.errors / self.query_count if self.query_count > 0 else 0,
            "slow_queries": self.slow_queries,
            "slow_query_rate": self.slow_queries / self.query_count if self.query_count > 0 else 0
        }
        
        # Add numpy-based statistics if available
        if HAS_NUMPY and np:
            result["mean_time"] = np.mean(self.query_times)
            result["median_time"] = np.median(self.query_times)
            result["p95_time"] = np.percentile(self.query_times, 95)
            result["p99_time"] = np.percentile(self.query_times, 99)
        else:
            # Fallback to basic statistics
            result["mean_time"] = sum(self.query_times) / len(self.query_times) if self.query_times else 0
        
        return result
    
    def reset(self):
        """Reset metrics"""
        self.query_count = 0
        self.query_times = []
        self.errors = 0
        self.slow_queries = 0
    
    def print_stats(self):
        """Print statistics"""
        stats = self.get_stats()
        
        print("\n" + "="*50)
        print("Neo4j Performance Metrics")
        print("="*50)
        print(f"Total Queries: {stats.get('query_count', 0)}")
        print(f"Total Time: {stats.get('total_time', 0):.2f}s")
        print(f"Mean Time: {stats.get('mean_time', 0)*1000:.2f}ms")
        print(f"Median Time: {stats.get('median_time', 0)*1000:.2f}ms")
        print(f"P95 Time: {stats.get('p95_time', 0)*1000:.2f}ms")
        print(f"P99 Time: {stats.get('p99_time', 0)*1000:.2f}ms")
        print(f"Errors: {stats.get('errors', 0)} ({stats.get('error_rate', 0)*100:.1f}%)")
        print(f"Slow Queries: {stats.get('slow_queries', 0)} ({stats.get('slow_query_rate', 0)*100:.1f}%)")
        print("="*50 + "\n")
