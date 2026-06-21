"""
Batch Processing Data Models
=============================
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import uuid


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(int, Enum):
    """Job priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class BatchJob:
    """
    Batch job definition
    
    Represents a single unit of work to be processed
    """
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_name: str = ""
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    
    # Execution config
    max_retries: int = 3
    timeout: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    
    # Status tracking
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    execution_time: float = 0.0
    
    # Worker assignment
    worker_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'job_id': self.job_id,
            'task_name': self.task_name,
            'metadata': self.metadata,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'retry_count': self.retry_count,
            'execution_time': self.execution_time,
            'error': self.error,
            'worker_id': self.worker_id
        }


@dataclass
class BatchResult:
    """
    Batch processing result
    
    Aggregates results from multiple jobs
    """
    batch_id: str
    total_jobs: int
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    results: List[BatchJob] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    total_execution_time: float = 0.0
    avg_job_time: float = 0.0
    throughput: float = 0.0  # jobs per second
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_jobs == 0:
            return 0.0
        return self.completed / self.total_jobs
    
    @property
    def is_complete(self) -> bool:
        """Check if batch is complete"""
        return (self.completed + self.failed + self.cancelled) >= self.total_jobs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'batch_id': self.batch_id,
            'total_jobs': self.total_jobs,
            'completed': self.completed,
            'failed': self.failed,
            'cancelled': self.cancelled,
            'success_rate': self.success_rate,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_execution_time': self.total_execution_time,
            'avg_job_time': self.avg_job_time,
            'throughput': self.throughput,
            'errors': self.errors
        }


@dataclass
class BatchConfig:
    """
    Batch processor configuration
    """
    # Worker configuration
    num_workers: int = 4
    worker_timeout: float = 300.0  # 5 minutes
    
    # Queue configuration
    max_queue_size: int = 10000
    enable_priority_queue: bool = True
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    
    # Checkpoint configuration
    enable_checkpoints: bool = True
    checkpoint_interval: int = 100  # jobs
    checkpoint_dir: str = "./checkpoints"
    
    # Monitoring
    enable_metrics: bool = True
    enable_progress_bar: bool = True
    
    # Resource limits
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[float] = None


@dataclass
class WorkerStats:
    """Worker performance statistics"""
    worker_id: str
    jobs_processed: int = 0
    jobs_failed: int = 0
    total_execution_time: float = 0.0
    avg_job_time: float = 0.0
    current_job: Optional[str] = None
    status: str = "idle"  # idle, busy, error
    last_heartbeat: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'worker_id': self.worker_id,
            'jobs_processed': self.jobs_processed,
            'jobs_failed': self.jobs_failed,
            'total_execution_time': self.total_execution_time,
            'avg_job_time': self.avg_job_time,
            'current_job': self.current_job,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat.isoformat()
        }
