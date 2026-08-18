"""
Enterprise Batch Processing System
==================================

Production-ready batch processing with advanced features

Components:
- models.py: BatchJob, BatchConfig, BatchResult, JobStatus, JobPriority
- queue.py: JobQueue (FIFO), PriorityQueue (max-heap based)
- worker.py: Worker, WorkerPool, ResourceLimits, WorkerStats, WorkerState
- processor.py: BatchProcessor, ProcessorConfig (wrapper for easy usage)

Usage:
    from mahoun.graph.batch import (
        JobQueue, PriorityQueue,
        Worker, WorkerPool,
        BatchJob, JobStatus, JobPriority,
        BatchConfig, BatchResult,
        BatchProcessor, ProcessorConfig
    )
"""

# Core data models
from .models import (
    BatchJob,
    BatchConfig,
    BatchResult,
    JobStatus,
    JobPriority,
)

# Queue implementations
from .queue import (
    JobQueue,
    PriorityQueue,
    QueueMetrics,
    SchedulingStrategy,
)

# Worker pool implementation
from .worker import (
    Worker,
    WorkerPool,
    WorkerState,
    ResourceLimits,
    WorkerStats,
)

# Processor wrapper (high-level interface)
from .processor import (
    BatchProcessor,
    ProcessorConfig,
)

__all__ = [
    # Models
    'BatchJob',
    'BatchConfig',
    'BatchResult',
    'JobStatus',
    'JobPriority',
    # Queues
    'JobQueue',
    'PriorityQueue',
    'QueueMetrics',
    'SchedulingStrategy',
    # Workers
    'Worker',
    'WorkerPool',
    'WorkerState',
    'ResourceLimits',
    'WorkerStats',
    # Processor
    'BatchProcessor',
    'ProcessorConfig',
]
