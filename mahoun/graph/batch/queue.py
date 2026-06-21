"""
Advanced Job Queue System
==========================
Enterprise-grade queue with multiple scheduling strategies
"""

import asyncio
import heapq
from typing import List, Optional, Dict, Any, Callable
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .models import BatchJob, JobStatus, JobPriority

logger = logging.getLogger(__name__)


class SchedulingStrategy(str, Enum):
    """Job scheduling strategies"""
    FIFO = "fifo"  # First In First Out
    LIFO = "lifo"  # Last In First Out
    PRIORITY = "priority"  # Priority-based
    FAIR_SHARE = "fair_share"  # Fair share across users/tenants
    SHORTEST_JOB_FIRST = "sjf"  # Shortest job first
    DEADLINE = "deadline"  # Deadline-based


@dataclass
class QueueMetrics:
    """Queue performance metrics"""
    total_enqueued: int = 0
    total_dequeued: int = 0
    current_size: int = 0
    max_size_reached: int = 0
    avg_wait_time: float = 0.0
    total_wait_time: float = 0.0
    
    # Per-priority metrics
    priority_counts: Dict[JobPriority, int] = field(default_factory=lambda: defaultdict(int))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_enqueued': self.total_enqueued,
            'total_dequeued': self.total_dequeued,
            'current_size': self.current_size,
            'max_size_reached': self.max_size_reached,
            'avg_wait_time': self.avg_wait_time,
            'priority_distribution': {
                k.name: v for k, v in self.priority_counts.items()
            }
        }


class JobQueue:
    """
    Base job queue with FIFO scheduling
    
    Thread-safe queue for batch jobs
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize job queue
        
        Args:
            max_size: Maximum queue size
        """
        self.max_size = max_size
        self.queue: deque = deque()
        self.lock = asyncio.Lock()
        self.not_empty = asyncio.Condition(self.lock)
        self.not_full = asyncio.Condition(self.lock)
        self.metrics = QueueMetrics()
        
        # Job tracking
        self.job_map: Dict[str, BatchJob] = {}
        self.enqueue_times: Dict[str, datetime] = {}
    
    async def enqueue(self, job: BatchJob, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Add job to queue
        
        Args:
            job: Job to enqueue
            block: Block if queue is full
            timeout: Timeout for blocking
            
        Returns:
            True if enqueued successfully
        """
        async with self.not_full:
            # Wait if full
            if len(self.queue) >= self.max_size:
                if not block:
                    return False
                
                if timeout:
                    try:
                        await asyncio.wait_for(
                            self.not_full.wait_for(lambda: len(self.queue) < self.max_size),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        return False
                else:
                    await self.not_full.wait_for(lambda: len(self.queue) < self.max_size)
            
            # Add to queue
            job.status = JobStatus.QUEUED
            self.queue.append(job)
            self.job_map[job.job_id] = job
            self.enqueue_times[job.job_id] = datetime.now()
            
            # Update metrics
            self.metrics.total_enqueued += 1
            self.metrics.current_size = len(self.queue)
            self.metrics.max_size_reached = max(self.metrics.max_size_reached, len(self.queue))
            self.metrics.priority_counts[job.priority] += 1
            
            # Notify waiting consumers
            self.not_empty.notify()
            
            logger.debug(f"Enqueued job {job.job_id} (queue size: {len(self.queue)})")
            return True
    
    async def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[BatchJob]:
        """
        Remove and return job from queue
        
        Args:
            block: Block if queue is empty
            timeout: Timeout for blocking
            
        Returns:
            Job or None if timeout
        """
        async with self.not_empty:
            # Wait if empty
            if not self.queue:
                if not block:
                    return None
                
                if timeout:
                    try:
                        await asyncio.wait_for(
                            self.not_empty.wait_for(lambda: len(self.queue) > 0),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        return None
                else:
                    await self.not_empty.wait_for(lambda: len(self.queue) > 0)
            
            # Get job
            job = self.queue.popleft()
            
            # Calculate wait time
            if job.job_id in self.enqueue_times:
                wait_time = (datetime.now() - self.enqueue_times[job.job_id]).total_seconds()
                self.metrics.total_wait_time += wait_time
                self.metrics.avg_wait_time = self.metrics.total_wait_time / (self.metrics.total_dequeued + 1)
                del self.enqueue_times[job.job_id]
            
            # Update metrics
            self.metrics.total_dequeued += 1
            self.metrics.current_size = len(self.queue)
            
            # Notify waiting producers
            self.not_full.notify()
            
            logger.debug(f"Dequeued job {job.job_id} (queue size: {len(self.queue)})")
            return job
    
    async def peek(self) -> Optional[BatchJob]:
        """Peek at next job without removing"""
        async with self.lock:
            return self.queue[0] if self.queue else None
    
    async def size(self) -> int:
        """Get current queue size"""
        async with self.lock:
            return len(self.queue)
    
    async def is_empty(self) -> bool:
        """Check if queue is empty"""
        async with self.lock:
            return len(self.queue) == 0
    
    async def is_full(self) -> bool:
        """Check if queue is full"""
        async with self.lock:
            return len(self.queue) >= self.max_size
    
    async def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID"""
        async with self.lock:
            return self.job_map.get(job_id)
    
    async def remove_job(self, job_id: str) -> bool:
        """Remove job from queue"""
        async with self.lock:
            if job_id in self.job_map:
                job = self.job_map[job_id]
                try:
                    self.queue.remove(job)
                    del self.job_map[job_id]
                    self.enqueue_times.pop(job_id, None)
                    self.metrics.current_size = len(self.queue)
                    return True
                except ValueError:
                    return False
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics"""
        return self.metrics.to_dict()


class PriorityQueue(JobQueue):
    """
    Priority-based job queue
    
    Jobs with higher priority are dequeued first
    Uses heap for efficient priority ordering
    """
    
    def __init__(self, max_size: int = 10000):
        """Initialize priority queue"""
        super().__init__(max_size)
        self.heap: List[tuple] = []  # (priority, counter, job)
        self.counter = 0  # For stable sorting
    
    async def enqueue(self, job: BatchJob, block: bool = True, timeout: Optional[float] = None) -> bool:
        """Add job with priority"""
        async with self.not_full:
            if len(self.heap) >= self.max_size:
                if not block:
                    return False
                
                if timeout:
                    try:
                        await asyncio.wait_for(
                            self.not_full.wait_for(lambda: len(self.heap) < self.max_size),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        return False
                else:
                    await self.not_full.wait_for(lambda: len(self.heap) < self.max_size)
            
            # Add to heap (negative priority for max-heap behavior)
            job.status = JobStatus.QUEUED
            heapq.heappush(self.heap, (-job.priority.value, self.counter, job))
            self.counter += 1
            
            self.job_map[job.job_id] = job
            self.enqueue_times[job.job_id] = datetime.now()
            
            # Update metrics
            self.metrics.total_enqueued += 1
            self.metrics.current_size = len(self.heap)
            self.metrics.max_size_reached = max(self.metrics.max_size_reached, len(self.heap))
            self.metrics.priority_counts[job.priority] += 1
            
            self.not_empty.notify()
            
            logger.debug(f"Enqueued job {job.job_id} with priority {job.priority.name}")
            return True
    
    async def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[BatchJob]:
        """Remove highest priority job"""
        async with self.not_empty:
            if not self.heap:
                if not block:
                    return None
                
                if timeout:
                    try:
                        await asyncio.wait_for(
                            self.not_empty.wait_for(lambda: len(self.heap) > 0),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        return None
                else:
                    await self.not_empty.wait_for(lambda: len(self.heap) > 0)
            
            # Get highest priority job
            _, _, job = heapq.heappop(self.heap)
            
            # Calculate wait time
            if job.job_id in self.enqueue_times:
                wait_time = (datetime.now() - self.enqueue_times[job.job_id]).total_seconds()
                self.metrics.total_wait_time += wait_time
                self.metrics.avg_wait_time = self.metrics.total_wait_time / (self.metrics.total_dequeued + 1)
                del self.enqueue_times[job.job_id]
            
            # Update metrics
            self.metrics.total_dequeued += 1
            self.metrics.current_size = len(self.heap)
            
            self.not_full.notify()
            
            logger.debug(f"Dequeued job {job.job_id} with priority {job.priority.name}")
            return job
    
    async def peek(self) -> Optional[BatchJob]:
        """Peek at highest priority job"""
        async with self.lock:
            if self.heap:
                return self.heap[0][2]
            return None
    
    async def size(self) -> int:
        """Get queue size"""
        async with self.lock:
            return len(self.heap)


class FairShareQueue(JobQueue):
    """
    Fair-share job queue
    
    Distributes resources fairly across users/tenants
    Prevents starvation by rotating between users
    """
    
    def __init__(self, max_size: int = 10000):
        """Initialize fair-share queue"""
        super().__init__(max_size)
        self.user_queues: Dict[str, deque] = defaultdict(deque)
        self.user_order: deque = deque()  # Round-robin order
        self.user_job_counts: Dict[str, int] = defaultdict(int)
    
    async def enqueue(self, job: BatchJob, block: bool = True, timeout: Optional[float] = None) -> bool:
        """Add job to user's queue"""
        user_id = job.metadata.get('user_id', 'default')
        
        async with self.not_full:
            total_jobs = sum(len(q) for q in self.user_queues.values())
            
            if total_jobs >= self.max_size:
                if not block:
                    return False
                
                if timeout:
                    try:
                        await asyncio.wait_for(
                            self.not_full.wait_for(lambda: sum(len(q) for q in self.user_queues.values()) < self.max_size),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        return False
                else:
                    await self.not_full.wait_for(lambda: sum(len(q) for q in self.user_queues.values()) < self.max_size)
            
            # Add to user's queue
            job.status = JobStatus.QUEUED
            if user_id not in self.user_queues or not self.user_queues[user_id]:
                self.user_order.append(user_id)
            
            self.user_queues[user_id].append(job)
            self.user_job_counts[user_id] += 1
            self.job_map[job.job_id] = job
            self.enqueue_times[job.job_id] = datetime.now()
            
            # Update metrics
            self.metrics.total_enqueued += 1
            self.metrics.current_size = sum(len(q) for q in self.user_queues.values())
            self.metrics.max_size_reached = max(self.metrics.max_size_reached, self.metrics.current_size)
            
            self.not_empty.notify()
            
            logger.debug(f"Enqueued job {job.job_id} for user {user_id}")
            return True
    
    async def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[BatchJob]:
        """Remove job using fair-share round-robin"""
        async with self.not_empty:
            if not self.user_order:
                if not block:
                    return None
                
                if timeout:
                    try:
                        await asyncio.wait_for(
                            self.not_empty.wait_for(lambda: len(self.user_order) > 0),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        return None
                else:
                    await self.not_empty.wait_for(lambda: len(self.user_order) > 0)
            
            # Round-robin: get next user
            user_id = self.user_order.popleft()
            user_queue = self.user_queues[user_id]
            
            # Get job from user's queue
            job = user_queue.popleft()
            
            # If user still has jobs, add back to rotation
            if user_queue:
                self.user_order.append(user_id)
            
            # Calculate wait time
            if job.job_id in self.enqueue_times:
                wait_time = (datetime.now() - self.enqueue_times[job.job_id]).total_seconds()
                self.metrics.total_wait_time += wait_time
                self.metrics.avg_wait_time = self.metrics.total_wait_time / (self.metrics.total_dequeued + 1)
                del self.enqueue_times[job.job_id]
            
            # Update metrics
            self.metrics.total_dequeued += 1
            self.metrics.current_size = sum(len(q) for q in self.user_queues.values())
            
            self.not_full.notify()
            
            logger.debug(f"Dequeued job {job.job_id} for user {user_id} (fair-share)")
            return job


class DeadLetterQueue(JobQueue):
    """
    Dead letter queue for failed jobs
    
    Stores jobs that failed after max retries
    """
    
    def __init__(self, max_size: int = 1000):
        """Initialize dead letter queue"""
        super().__init__(max_size)
        self.failure_reasons: Dict[str, str] = {}
    
    async def enqueue(self, job: BatchJob, reason: str = "", block: bool = False, timeout: Optional[float] = None) -> bool:
        """Add failed job with reason"""
        success = await super().enqueue(job, block, timeout)
        if success:
            self.failure_reasons[job.job_id] = reason
            logger.warning(f"Job {job.job_id} moved to dead letter queue: {reason}")
        return success
    
    async def get_failure_reason(self, job_id: str) -> Optional[str]:
        """Get failure reason for job"""
        async with self.lock:
            return self.failure_reasons.get(job_id)
