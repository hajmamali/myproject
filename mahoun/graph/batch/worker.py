"""
Advanced Worker Pool System
============================
Enterprise-grade worker management with auto-scaling and fault tolerance
"""

import asyncio
import psutil
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import uuid

from .models import BatchJob, JobStatus, WorkerStats
from .queue import JobQueue

logger = logging.getLogger(__name__)


class WorkerState(str, Enum):
    """Worker states"""
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ResourceLimits:
    """Resource limits for workers"""
    max_memory_mb: Optional[float] = None
    max_cpu_percent: Optional[float] = None
    max_gpu_memory_mb: Optional[float] = None
    
    def check_memory(self) -> bool:
        """Check if memory limit exceeded"""
        if self.max_memory_mb is None:
            return True
        
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        return memory_mb < self.max_memory_mb
    
    def check_cpu(self) -> bool:
        """Check if CPU limit exceeded"""
        if self.max_cpu_percent is None:
            return True
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        return cpu_percent < self.max_cpu_percent
    
    def check_all(self) -> tuple[bool, str]:
        """Check all resource limits"""
        if not self.check_memory():
            return False, "Memory limit exceeded"
        if not self.check_cpu():
            return False, "CPU limit exceeded"
        return True, "OK"


class Worker:
    """
    Advanced worker with fault tolerance and resource management
    
    Features:
    - Async job execution
    - Resource monitoring
    - Heartbeat mechanism
    - Graceful shutdown
    - Error recovery
    """
    
    def __init__(
        self,
        worker_id: str,
        task_handler: Callable,
        resource_limits: Optional[ResourceLimits] = None,
        heartbeat_interval: float = 5.0,
        max_consecutive_failures: int = 5
    ):
        """
        Initialize worker
        
        Args:
            worker_id: Unique worker ID
            task_handler: Async function to process jobs
            resource_limits: Resource limits
            heartbeat_interval: Heartbeat interval (seconds)
            max_consecutive_failures: Max failures before stopping
        """
        self.worker_id = worker_id
        self.task_handler = task_handler
        self.resource_limits = resource_limits or ResourceLimits()
        self.heartbeat_interval = heartbeat_interval
        self.max_consecutive_failures = max_consecutive_failures
        
        # State
        self.state = WorkerState.IDLE
        self.current_job: Optional[BatchJob] = None
        self.stats = WorkerStats(worker_id=worker_id)
        
        # Control
        self.should_stop = False
        self.consecutive_failures = 0
        
        # Tasks
        self.worker_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def start(self, job_queue: JobQueue):
        """Start worker"""
        logger.info(f"Worker {self.worker_id} starting...")
        
        self.worker_task = asyncio.create_task(self._work_loop(job_queue))
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"Worker {self.worker_id} started")
    
    async def _work_loop(self, job_queue: JobQueue):
        """Main work loop"""
        while not self.should_stop:
            try:
                # Check resource limits
                can_proceed, reason = self.resource_limits.check_all()
                if not can_proceed:
                    logger.warning(f"Worker {self.worker_id}: {reason}. Pausing...")
                    self.state = WorkerState.PAUSED
                    await asyncio.sleep(5)
                    continue
                
                # Get job from queue
                self.state = WorkerState.IDLE
                job = await job_queue.dequeue(block=True, timeout=1.0)
                
                if job is None:
                    continue
                
                # Process job
                await self._process_job(job)
                
            except asyncio.CancelledError:
                logger.info(f"Worker {self.worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                self.consecutive_failures += 1
                
                if self.consecutive_failures >= self.max_consecutive_failures:
                    logger.error(f"Worker {self.worker_id} exceeded max failures. Stopping.")
                    self.state = WorkerState.ERROR
                    break
                
                await asyncio.sleep(1)
        
        self.state = WorkerState.STOPPED
        logger.info(f"Worker {self.worker_id} stopped")
    
    async def _process_job(self, job: BatchJob):
        """Process a single job"""
        self.state = WorkerState.BUSY
        self.current_job = job
        self.stats.current_job = job.job_id
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        job.worker_id = self.worker_id
        
        start_time = time.time()
        
        try:
            # Execute task with timeout
            if job.timeout:
                result = await asyncio.wait_for(
                    self.task_handler(job),
                    timeout=job.timeout
                )
            else:
                result = await self.task_handler(job)
            
            # Success
            execution_time = time.time() - start_time
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.result = result
            job.execution_time = execution_time
            
            # Update stats
            self.stats.jobs_processed += 1
            self.stats.total_execution_time += execution_time
            self.stats.avg_job_time = self.stats.total_execution_time / self.stats.jobs_processed
            
            # Reset failure counter on success
            self.consecutive_failures = 0
            
            logger.debug(f"Worker {self.worker_id} completed job {job.job_id} in {execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            job.status = JobStatus.FAILED
            job.error = f"Timeout after {job.timeout}s"
            job.execution_time = execution_time
            
            self.stats.jobs_failed += 1
            self.consecutive_failures += 1
            
            logger.error(f"Worker {self.worker_id} job {job.job_id} timed out")
            
        except Exception as e:
            execution_time = time.time() - start_time
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.execution_time = execution_time
            
            self.stats.jobs_failed += 1
            self.consecutive_failures += 1
            
            logger.error(f"Worker {self.worker_id} job {job.job_id} failed: {e}")
        
        finally:
            self.current_job = None
            self.stats.current_job = None
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while not self.should_stop:
            try:
                self.stats.last_heartbeat = datetime.now()
                self.stats.status = self.state.value
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
    
    async def stop(self, graceful: bool = True, timeout: float = 30.0):
        """
        Stop worker
        
        Args:
            graceful: Wait for current job to complete
            timeout: Timeout for graceful shutdown
        """
        logger.info(f"Stopping worker {self.worker_id} (graceful={graceful})")
        
        self.should_stop = True
        self.state = WorkerState.STOPPING
        
        if graceful and self.current_job:
            # Wait for current job
            start = time.time()
            while self.current_job and (time.time() - start) < timeout:
                await asyncio.sleep(0.1)
        
        # Cancel tasks
        if self.worker_task:
            self.worker_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        self.state = WorkerState.STOPPED
        logger.info(f"Worker {self.worker_id} stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        return self.stats.to_dict()


class WorkerPool:
    """
    Advanced worker pool with auto-scaling and load balancing
    
    Features:
    - Dynamic worker scaling based on load
    - Health monitoring
    - Load balancing
    - Fault tolerance
    - Resource management
    """
    
    def __init__(
        self,
        task_handler: Callable,
        min_workers: int = 2,
        max_workers: int = 10,
        auto_scale: bool = True,
        scale_up_threshold: float = 0.8,  # Queue utilization
        scale_down_threshold: float = 0.2,
        resource_limits: Optional[ResourceLimits] = None
    ):
        """
        Initialize worker pool
        
        Args:
            task_handler: Function to process jobs
            min_workers: Minimum number of workers
            max_workers: Maximum number of workers
            auto_scale: Enable auto-scaling
            scale_up_threshold: Scale up when queue > threshold
            scale_down_threshold: Scale down when queue < threshold
            resource_limits: Resource limits per worker
        """
        self.task_handler = task_handler
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.auto_scale = auto_scale
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.resource_limits = resource_limits
        
        # Workers
        self.workers: List[Worker] = []
        self.worker_map: Dict[str, Worker] = {}
        
        # Monitoring
        self.scaling_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
    
    async def start(self, job_queue: JobQueue):
        """Start worker pool"""
        logger.info(f"Starting worker pool (min={self.min_workers}, max={self.max_workers})")
        
        # Start minimum workers
        for i in range(self.min_workers):
            await self._add_worker(job_queue)
        
        # Start auto-scaling
        if self.auto_scale:
            self.scaling_task = asyncio.create_task(self._auto_scale_loop(job_queue))
        
        # Start health checks
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Worker pool started with {len(self.workers)} workers")
    
    async def _add_worker(self, job_queue: JobQueue) -> Worker:
        """Add new worker to pool"""
        worker_id = f"worker-{len(self.workers)}"
        worker = Worker(
            worker_id=worker_id,
            task_handler=self.task_handler,
            resource_limits=self.resource_limits
        )
        
        await worker.start(job_queue)
        
        self.workers.append(worker)
        self.worker_map[worker_id] = worker
        
        logger.info(f"Added worker {worker_id} (total: {len(self.workers)})")
        return worker
    
    async def _remove_worker(self):
        """Remove worker from pool"""
        if len(self.workers) <= self.min_workers:
            return
        
        # Find idle worker
        for worker in self.workers:
            if worker.state == WorkerState.IDLE:
                await worker.stop(graceful=True)
                self.workers.remove(worker)
                del self.worker_map[worker.worker_id]
                logger.info(f"Removed worker {worker.worker_id} (total: {len(self.workers)})")
                return
    
    async def _auto_scale_loop(self, job_queue: JobQueue):
        """Auto-scaling loop"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                queue_size = await job_queue.size()
                queue_utilization = queue_size / job_queue.max_size
                
                # Scale up
                if queue_utilization > self.scale_up_threshold and len(self.workers) < self.max_workers:
                    logger.info(f"Scaling up: queue utilization {queue_utilization:.1%}")
                    await self._add_worker(job_queue)
                
                # Scale down
                elif queue_utilization < self.scale_down_threshold and len(self.workers) > self.min_workers:
                    logger.info(f"Scaling down: queue utilization {queue_utilization:.1%}")
                    await self._remove_worker()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-scaling error: {e}")
    
    async def _health_check_loop(self):
        """Health check loop"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                for worker in self.workers:
                    # Check heartbeat
                    if worker.stats.last_heartbeat:
                        elapsed = (datetime.now() - worker.stats.last_heartbeat).total_seconds()
                        if elapsed > 60:  # No heartbeat for 1 minute
                            logger.warning(f"Worker {worker.worker_id} heartbeat timeout. Restarting...")
                            # TODO: Restart worker
                    
                    # Check if stuck
                    if worker.state == WorkerState.BUSY and worker.current_job:
                        job_duration = (datetime.now() - worker.current_job.started_at).total_seconds()
                        if worker.current_job.timeout and job_duration > worker.current_job.timeout * 1.5:
                            logger.warning(f"Worker {worker.worker_id} appears stuck. Restarting...")
                            # TODO: Restart worker
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def stop(self, graceful: bool = True, timeout: float = 60.0):
        """Stop all workers"""
        logger.info(f"Stopping worker pool (graceful={graceful})")
        
        # Cancel monitoring tasks
        if self.scaling_task:
            self.scaling_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        
        # Stop all workers
        stop_tasks = [worker.stop(graceful, timeout) for worker in self.workers]
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        logger.info("Worker pool stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        total_processed = sum(w.stats.jobs_processed for w in self.workers)
        total_failed = sum(w.stats.jobs_failed for w in self.workers)
        
        worker_states = {}
        for state in WorkerState:
            worker_states[state.value] = sum(1 for w in self.workers if w.state == state)
        
        return {
            'total_workers': len(self.workers),
            'worker_states': worker_states,
            'total_jobs_processed': total_processed,
            'total_jobs_failed': total_failed,
            'success_rate': total_processed / (total_processed + total_failed) if (total_processed + total_failed) > 0 else 0,
            'workers': [w.get_stats() for w in self.workers]
        }
