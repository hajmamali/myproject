"""
Batch Processor Wrapper
=======================

High-level wrapper for the batch processing system providing easy-to-use
ProcessorConfig and BatchProcessor classes.
"""

from typing import List, Dict, Any, Optional, Callable
from .models import BatchJob, JobStatus
from .queue import JobQueue, PriorityQueue
from .worker import Worker, ResourceLimits
import asyncio

class ProcessorConfig:
    """
    Configuration for batch processor
    
    Configures the processor itself (number of workers, queue size, etc.)
    """
    def __init__(
        self,
        num_workers: int = 4,
        queue_size: int = 10000,
        use_priority: bool = False,
        resource_limits: Optional[ResourceLimits] = None
    ):
        self.num_workers = num_workers
        self.queue_size = queue_size
        self.use_priority = use_priority
        self.resource_limits = resource_limits or ResourceLimits()

class BatchProcessor:
    """
    High-level batch job processor
    
    Provides a simple interface for submitting and managing batch jobs
    using the underlying batch system components.
    """
    
    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.queue = (
            PriorityQueue(max_size=config.queue_size)
            if config.use_priority
            else JobQueue(max_size=config.queue_size)
        )
        self.workers = []
        self.task_handler: Optional[Callable] = None
        self._started = False
    
    def set_task_handler(self, handler: Callable):
        """Set the async handler for all jobs"""
        self.task_handler = handler
    
    async def start(self):
        """Start worker pool"""
        if not self.task_handler:
            raise ValueError("Task handler not set")
        
        if self._started:
            return  # Already started
            
        for i in range(self.config.num_workers):
            worker = Worker(
                worker_id=f"worker-{i}",
                task_handler=self.task_handler,
                resource_limits=self.config.resource_limits
            )
            await worker.start(self.queue)
            self.workers.append(worker)
        
        self._started = True
    
    async def submit_job(self, job: BatchJob) -> bool:
        """Submit a job to the queue"""
        if not self._started:
            await self.start()
        return await self.queue.enqueue(job)
    
    async def submit_jobs(self, jobs: List[BatchJob]) -> List[bool]:
        """Submit multiple jobs to the queue"""
        if not self._started:
            await self.start()
        results = []
        for job in jobs:
            result = await self.queue.enqueue(job)
            results.append(result)
        return results
    
    async def wait_completion(self, timeout: Optional[float] = None):
        """Wait for all queued jobs to complete"""
        if not self._started:
            return
            
        start = asyncio.get_event_loop().time()
        while not await self.queue.is_empty():
            if timeout and asyncio.get_event_loop().time() - start > timeout:
                raise TimeoutError("Batch processing timed out")
            await asyncio.sleep(0.1)
    
    async def stop(self, graceful: bool = True):
        """Stop all workers"""
        if not self._started:
            return
            
        for worker in self.workers:
            await worker.stop(graceful=graceful)
        self.workers.clear()
        self._started = False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue and worker metrics"""
        if not self._started:
            return {
                "queue_metrics": {"total_enqueued": 0, "total_dequeued": 0, "current_size": 0},
                "worker_stats": [],
                "num_workers": 0
            }
            
        return {
            "queue_metrics": self.queue.get_metrics(),
            "worker_stats": [w.__dict__ for w in self.workers],
            "num_workers": len(self.workers),
            "queue_type": "priority" if self.config.use_priority else "fifo"
        }

# For backward compatibility and convenience
__all__ = ['BatchProcessor', 'ProcessorConfig']
