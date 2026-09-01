"""
KG Loader Configuration
=======================

Ultra-advanced configuration for knowledge graph loading with:
- Adaptive worker scaling
- Circuit breaker patterns  
- Memory management
- Performance profiling
- Observability integration
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
import psutil


class ExecutionMode(str, Enum):
    """Execution modes with different resource profiles"""
    MINIMAL = "minimal"      # 8GB RAM, 2 workers, basic features
    STANDARD = "standard"    # 16GB RAM, 4 workers, full features
    PERFORMANCE = "performance"  # 32GB+ RAM, 8+ workers, aggressive caching
    STRESS_TEST = "stress_test"  # Maximum load for testing


class BatchStrategy(str, Enum):
    """Batching strategies for graph operations"""
    SINGLE = "single"          # One entity at a time (safest)
    MICRO = "micro"           # 10 entities per batch
    SMALL = "small"           # 50 entities per batch
    MEDIUM = "medium"         # 100 entities per batch
    LARGE = "large"           # 500 entities per batch
    BULK = "bulk"             # 1000+ entities per batch (fastest, needs RAM)


@dataclass
class ResourceLimitsConfig:
    """Resource limits to prevent OOM/CPU exhaustion"""
    max_memory_mb: Optional[float] = None      # Max memory per worker
    max_memory_percent: float = 80.0           # Max system memory %
    max_cpu_percent: float = 90.0              # Max CPU utilization
    max_concurrent_neo4j_queries: int = 10     # Max parallel Neo4j writes
    max_batch_size: int = 1000                 # Max entities per batch write
    
    def __post_init__(self):
        """Auto-detect memory if not specified"""
        if self.max_memory_mb is None:
            # Set per-worker memory to 1/4 of available RAM
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
            self.max_memory_mb = available_mb / 4


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker to prevent cascade failures"""
    enabled: bool = True
    failure_threshold: int = 5          # Open circuit after N failures
    recovery_timeout: float = 60.0      # Try recovery after N seconds
    half_open_attempts: int = 3         # Test recovery with N requests


@dataclass
class CheckpointConfig:
    """Checkpoint/resume configuration"""
    enabled: bool = True
    path: Optional[Path] = None
    interval: int = 100                 # Checkpoint every N jobs
    auto_resume: bool = True            # Resume from last checkpoint on restart
    keep_history: int = 3               # Keep last N checkpoints


@dataclass
class MetricsConfig:
    """Metrics and observability configuration"""
    enabled: bool = True
    prometheus_port: int = 9090
    grafana_enabled: bool = False
    grafana_dashboard_id: Optional[str] = None
    export_interval: float = 10.0       # Export metrics every N seconds
    
    # Custom metric labels
    labels: Dict[str, str] = field(default_factory=lambda: {
        'environment': 'production',
        'service': 'kg_loader',
        'version': '1.0.0'
    })


@dataclass
class DLQConfig:
    """Dead Letter Queue configuration"""
    enabled: bool = True
    path: Optional[Path] = None
    max_size: int = 10000               # Max unresolved items in DLQ
    export_format: str = "json"         # json | csv | parquet
    auto_retry_enabled: bool = False    # Auto-retry DLQ items


@dataclass
class KGLoaderConfig:
    """
    Ultra-Advanced Knowledge Graph Loader Configuration
    
    Features:
    - Execution mode presets (MINIMAL, STANDARD, PERFORMANCE)
    - Adaptive resource management
    - Circuit breaker fault tolerance
    - Comprehensive checkpointing
    - Full observability stack
    - Dead letter queue with retry
    
    Usage:
        # Minimal mode (8GB RAM, development)
        config = KGLoaderConfig.for_minimal(corpus_path="corpus.txt")
        
        # Performance mode (32GB+ RAM, production)
        config = KGLoaderConfig.for_performance(corpus_path="corpus.txt")
        
        # Custom configuration
        config = KGLoaderConfig(
            corpus_path="corpus.txt",
            execution_mode=ExecutionMode.STANDARD,
            num_workers=8,
        )
    """
    
    # ========== REQUIRED ==========
    corpus_path: Path
    
    # ========== EXECUTION ==========
    execution_mode: ExecutionMode = ExecutionMode.STANDARD
    batch_strategy: BatchStrategy = BatchStrategy.MEDIUM
    
    # ========== WORKERS ==========
    num_workers: int = 4
    worker_timeout: float = 300.0       # 5 minutes per job
    worker_heartbeat_interval: float = 5.0
    enable_auto_scaling: bool = True    # Auto-adjust workers based on load
    min_workers: int = 2
    max_workers: int = 16
    
    # ========== QUEUE ==========
    max_queue_size: int = 10000
    enable_priority: bool = True
    queue_timeout: float = 60.0
    
    # ========== RETRY ==========
    max_retries: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True    # Exponential retry delay
    
    # ========== RESOURCE LIMITS ==========
    resource_limits: ResourceLimitsConfig = field(default_factory=ResourceLimitsConfig)
    
    # ========== CIRCUIT BREAKER ==========
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # ========== CHECKPOINTING ==========
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)
    
    # ========== METRICS ==========
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    
    # ========== DLQ ==========
    dlq: DLQConfig = field(default_factory=DLQConfig)
    
    # ========== MODE ==========
    dry_run: bool = False
    verbose: bool = False
    debug: bool = False
    
    # ========== FEATURES ==========
    enable_citation_resolution: bool = True     # Resolve citations
    enable_semantic_enrichment: bool = False    # Extract concepts (Phase 2)
    enable_temporal_metadata: bool = False      # Add temporal data (Phase 3)
    skip_existing: bool = True                  # Skip already-loaded entities
    
    def __post_init__(self):
        """Validate and set defaults"""
        # Ensure corpus_path is Path
        if not isinstance(self.corpus_path, Path):
            self.corpus_path = Path(self.corpus_path)
        
        # Validate corpus exists
        if not self.dry_run and not self.corpus_path.exists():
            raise FileNotFoundError(f"Corpus file not found: {self.corpus_path}")
        
        # Set checkpoint path default
        if self.checkpoint.enabled and self.checkpoint.path is None:
            self.checkpoint.path = Path(f"/tmp/kg_loader_{self.corpus_path.stem}_checkpoint.json")
        
        # Set DLQ path default
        if self.dlq.enabled and self.dlq.path is None:
            self.dlq.path = Path(f"/tmp/kg_loader_{self.corpus_path.stem}_dlq.json")
        
        # Apply execution mode presets
        self._apply_execution_mode()
        
        # Validate worker counts
        if self.num_workers < 1:
            raise ValueError("num_workers must be >= 1")
        if self.enable_auto_scaling:
            if self.min_workers < 1:
                raise ValueError("min_workers must be >= 1")
            if self.max_workers < self.min_workers:
                raise ValueError("max_workers must be >= min_workers")
    
    def _apply_execution_mode(self):
        """Apply execution mode preset configurations"""
        if self.execution_mode == ExecutionMode.MINIMAL:
            # 8GB RAM, minimal resources
            self.num_workers = 2
            self.max_workers = 4
            self.batch_strategy = BatchStrategy.MICRO
            self.resource_limits.max_memory_mb = 2048  # 2GB per worker
            self.resource_limits.max_batch_size = 50
            self.checkpoint.interval = 50
            self.enable_auto_scaling = False
            
        elif self.execution_mode == ExecutionMode.STANDARD:
            # 16GB RAM, balanced
            self.num_workers = 4
            self.max_workers = 8
            self.batch_strategy = BatchStrategy.MEDIUM
            self.resource_limits.max_memory_mb = 4096  # 4GB per worker
            self.resource_limits.max_batch_size = 100
            self.checkpoint.interval = 100
            
        elif self.execution_mode == ExecutionMode.PERFORMANCE:
            # 32GB+ RAM, aggressive
            self.num_workers = 8
            self.max_workers = 16
            self.batch_strategy = BatchStrategy.LARGE
            self.resource_limits.max_memory_mb = 8192  # 8GB per worker
            self.resource_limits.max_batch_size = 500
            self.checkpoint.interval = 200
            
        elif self.execution_mode == ExecutionMode.STRESS_TEST:
            # Maximum load for testing
            self.num_workers = 16
            self.max_workers = 32
            self.batch_strategy = BatchStrategy.BULK
            self.resource_limits.max_memory_mb = None  # No limit
            self.resource_limits.max_batch_size = 1000
            self.checkpoint.interval = 500
    
    @classmethod
    def for_minimal(cls, corpus_path: str | Path, **kwargs) -> "KGLoaderConfig":
        """Create config for minimal resources (8GB RAM)"""
        return cls(
            corpus_path=Path(corpus_path),
            execution_mode=ExecutionMode.MINIMAL,
            **kwargs
        )
    
    @classmethod
    def for_standard(cls, corpus_path: str | Path, **kwargs) -> "KGLoaderConfig":
        """Create config for standard deployment (16GB RAM)"""
        return cls(
            corpus_path=Path(corpus_path),
            execution_mode=ExecutionMode.STANDARD,
            **kwargs
        )
    
    @classmethod
    def for_performance(cls, corpus_path: str | Path, **kwargs) -> "KGLoaderConfig":
        """Create config for high performance (32GB+ RAM)"""
        return cls(
            corpus_path=Path(corpus_path),
            execution_mode=ExecutionMode.PERFORMANCE,
            **kwargs
        )
    
    @classmethod
    def for_stress_test(cls, corpus_path: str | Path, **kwargs) -> "KGLoaderConfig":
        """Create config for stress testing (maximum load)"""
        return cls(
            corpus_path=Path(corpus_path),
            execution_mode=ExecutionMode.STRESS_TEST,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            'corpus_path': str(self.corpus_path),
            'execution_mode': self.execution_mode.value,
            'batch_strategy': self.batch_strategy.value,
            'num_workers': self.num_workers,
            'worker_timeout': self.worker_timeout,
            'max_queue_size': self.max_queue_size,
            'resource_limits': {
                'max_memory_mb': self.resource_limits.max_memory_mb,
                'max_cpu_percent': self.resource_limits.max_cpu_percent,
                'max_batch_size': self.resource_limits.max_batch_size,
            },
            'checkpoint_enabled': self.checkpoint.enabled,
            'metrics_enabled': self.metrics.enabled,
            'dlq_enabled': self.dlq.enabled,
            'dry_run': self.dry_run,
        }
    
    def validate_system_requirements(self) -> tuple[bool, List[str]]:
        """
        Validate system can meet configuration requirements
        
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Check available memory
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        required_mb = (self.resource_limits.max_memory_mb or 0) * self.num_workers
        
        if required_mb > available_mb:
            warnings.append(
                f"Insufficient memory: need {required_mb:.0f}MB, "
                f"available {available_mb:.0f}MB"
            )
        
        # Check CPU cores
        cpu_count = psutil.cpu_count()
        if self.num_workers > cpu_count * 2:
            warnings.append(
                f"Too many workers ({self.num_workers}) for CPU cores ({cpu_count})"
            )
        
        # Check disk space for checkpoints
        if self.checkpoint.enabled and self.checkpoint.path:
            try:
                disk = psutil.disk_usage(self.checkpoint.path.parent)
                if disk.free < 1024 * 1024 * 1024:  # <1GB free
                    warnings.append(f"Low disk space for checkpoints: {disk.free / (1024**3):.1f}GB")
            except:
                pass
        
        return len(warnings) == 0, warnings
