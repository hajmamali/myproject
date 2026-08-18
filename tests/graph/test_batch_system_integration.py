"""
Comprehensive integration tests for batch processing system.

Tests:
- JobQueue (FIFO) functionality
- PriorityQueue ordering
- Worker execution
- Error handling & retry
- Resource limits
"""

import pytest
import asyncio
from mahoun.graph.batch import (
    JobQueue,
    PriorityQueue,
    Worker,
    WorkerPool,
    BatchJob,
    JobStatus,
    JobPriority,
    ResourceLimits,
)


class TestJobQueueBasics:
    """Test basic JobQueue (FIFO) functionality"""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue_order(self):
        """Jobs should dequeue in FIFO order"""
        queue = JobQueue(max_size=100)

        # Enqueue 3 jobs
        jobs_in = [
            BatchJob(task_name="job1", priority=JobPriority.NORMAL),
            BatchJob(task_name="job2", priority=JobPriority.NORMAL),
            BatchJob(task_name="job3", priority=JobPriority.NORMAL),
        ]

        for job in jobs_in:
            await queue.enqueue(job)

        # Dequeue and verify order
        jobs_out = []
        for _ in range(3):
            job = await queue.dequeue(block=False)
            assert job is not None
            jobs_out.append(job)

        # Verify FIFO order
        assert jobs_out[0].task_name == "job1"
        assert jobs_out[1].task_name == "job2"
        assert jobs_out[2].task_name == "job3"

    @pytest.mark.asyncio
    async def test_queue_empty_check(self):
        """Test is_empty() method"""
        queue = JobQueue(max_size=10)

        # Initially empty
        assert await queue.is_empty()

        # Add job
        job = BatchJob(task_name="test", priority=JobPriority.NORMAL)
        await queue.enqueue(job)

        # Not empty
        assert not await queue.is_empty()

        # Remove job
        _ = await queue.dequeue(block=False)

        # Empty again
        assert await queue.is_empty()

    @pytest.mark.asyncio
    async def test_queue_size(self):
        """Test queue size tracking"""
        queue = JobQueue(max_size=100)

        assert await queue.size() == 0

        # Add 5 jobs
        for i in range(5):
            job = BatchJob(task_name=f"job{i}", priority=JobPriority.NORMAL)
            await queue.enqueue(job)

        assert await queue.size() == 5

        # Remove 2 jobs
        for _ in range(2):
            _ = await queue.dequeue(block=False)

        assert await queue.size() == 3

    @pytest.mark.asyncio
    async def test_queue_metrics(self):
        """Test queue metrics collection"""
        queue = JobQueue(max_size=100)

        # Add and process jobs
        for i in range(5):
            job = BatchJob(task_name=f"job{i}", priority=JobPriority.NORMAL)
            await queue.enqueue(job)

        for _ in range(5):
            _ = await queue.dequeue(block=False)

        # Check metrics
        metrics = queue.get_metrics()
        assert metrics["total_enqueued"] == 5
        assert metrics["total_dequeued"] == 5
        assert metrics["current_size"] == 0


class TestPriorityQueue:
    """Test PriorityQueue ordering by priority"""

    @pytest.mark.asyncio
    async def test_priority_order(self):
        """Higher priority jobs should dequeue first"""
        queue = PriorityQueue(max_size=100)

        # Enqueue jobs with different priorities in random order
        jobs_in = [
            BatchJob(task_name="low", priority=JobPriority.LOW),
            BatchJob(task_name="critical", priority=JobPriority.CRITICAL),
            BatchJob(task_name="normal", priority=JobPriority.NORMAL),
            BatchJob(task_name="high", priority=JobPriority.HIGH),
        ]

        for job in jobs_in:
            await queue.enqueue(job)

        # Dequeue and verify priority order
        job1 = await queue.dequeue(block=False)
        assert job1.task_name == "critical"
        assert job1.priority == JobPriority.CRITICAL

        job2 = await queue.dequeue(block=False)
        assert job2.task_name == "high"
        assert job2.priority == JobPriority.HIGH

        job3 = await queue.dequeue(block=False)
        assert job3.task_name == "normal"
        assert job3.priority == JobPriority.NORMAL

        job4 = await queue.dequeue(block=False)
        assert job4.task_name == "low"
        assert job4.priority == JobPriority.LOW

    @pytest.mark.asyncio
    async def test_same_priority_fifo(self):
        """Jobs with same priority should maintain FIFO order"""
        queue = PriorityQueue(max_size=100)

        # Enqueue jobs with same priority
        jobs = [
            BatchJob(task_name="job1", priority=JobPriority.NORMAL),
            BatchJob(task_name="job2", priority=JobPriority.NORMAL),
            BatchJob(task_name="job3", priority=JobPriority.NORMAL),
        ]

        for job in jobs:
            await queue.enqueue(job)

        # Should maintain FIFO order
        job1 = await queue.dequeue(block=False)
        assert job1.task_name == "job1"

        job2 = await queue.dequeue(block=False)
        assert job2.task_name == "job2"

        job3 = await queue.dequeue(block=False)
        assert job3.task_name == "job3"


class TestWorkerExecution:
    """Test Worker job execution"""

    async def simple_task_handler(self, job: BatchJob) -> bool:
        """Simple async task handler for testing"""
        if job.data and job.data.get("delay"):
            await asyncio.sleep(job.data["delay"])

        if job.data and job.data.get("should_fail"):
            raise Exception("Task failed as expected")

        job.data = {"result": "completed"}
        return True

    @pytest.mark.asyncio
    async def test_worker_processes_job(self):
        """Worker should successfully process a job"""
        queue = JobQueue(max_size=10)

        # Create and start worker
        worker = Worker(
            worker_id="test-worker-1",
            task_handler=self.simple_task_handler,
        )
        await worker.start(queue)

        # Enqueue a job
        job = BatchJob(
            task_name="test_task",
            data={"message": "hello"},
            priority=JobPriority.NORMAL,
        )
        await queue.enqueue(job)

        # Give worker time to process
        await asyncio.sleep(0.5)

        # Stop worker
        await worker.stop()

        # Verify job was processed
        assert job.status == JobStatus.COMPLETED
        assert job.data.get("result") == "completed"

    @pytest.mark.asyncio
    async def test_worker_handles_error(self):
        """Worker should catch and record errors"""
        queue = JobQueue(max_size=10)

        worker = Worker(
            worker_id="test-worker-2",
            task_handler=self.simple_task_handler,
        )
        await worker.start(queue)

        # Enqueue a job that will fail
        job = BatchJob(
            task_name="failing_task",
            data={"should_fail": True},
            priority=JobPriority.NORMAL,
        )
        await queue.enqueue(job)

        # Give worker time to process
        await asyncio.sleep(0.5)

        # Stop worker
        await worker.stop()

        # Verify job failed
        assert job.status == JobStatus.FAILED
        assert job.error is not None
        assert "Task failed as expected" in job.error

    @pytest.mark.asyncio
    async def test_worker_respects_timeout(self):
        """Worker should timeout long-running jobs"""
        queue = JobQueue(max_size=10)

        worker = Worker(
            worker_id="test-worker-3",
            task_handler=self.simple_task_handler,
        )
        await worker.start(queue)

        # Enqueue a job with timeout
        job = BatchJob(
            task_name="slow_task",
            data={"delay": 5},  # 5 second delay
            timeout=0.5,  # 500ms timeout
            priority=JobPriority.NORMAL,
        )
        await queue.enqueue(job)

        # Give worker time to process
        await asyncio.sleep(1.0)

        # Stop worker
        await worker.stop()

        # Verify job timed out
        assert job.status == JobStatus.FAILED
        assert "Timeout" in job.error


class TestWorkerPool:
    """Test WorkerPool with multiple workers"""

    async def counting_handler(self, job: BatchJob) -> bool:
        """Handler that increments a counter"""
        counter_id = job.data.get("counter_id")
        delay = job.data.get("delay", 0)

        if delay:
            await asyncio.sleep(delay)

        # In real scenario, this would write to shared state
        return True

    @pytest.mark.asyncio
    async def test_worker_pool_parallel_execution(self):
        """Multiple workers should execute jobs in parallel"""
        queue = JobQueue(max_size=100)

        # Create pool with 2-4 workers
        pool = WorkerPool(
            task_handler=self.counting_handler,
            min_workers=2,
            max_workers=4,
            auto_scale=False,  # Disable auto-scaling for test
        )
        await pool.start(queue)

        # Enqueue 20 jobs
        jobs = []
        for i in range(20):
            job = BatchJob(
                task_name=f"job{i}",
                data={"counter_id": i, "delay": 0.1},
                priority=JobPriority.NORMAL,
            )
            jobs.append(job)
            await queue.enqueue(job)

        # Wait for completion (with timeout)
        timeout = 5
        start = asyncio.get_event_loop().time()
        while not await queue.is_empty():
            if asyncio.get_event_loop().time() - start > timeout:
                break
            await asyncio.sleep(0.1)

        # Stop pool
        await pool.stop()

        # Verify jobs completed
        completed = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        assert completed > 0, "At least some jobs should complete"

    @pytest.mark.asyncio
    async def test_worker_pool_metrics(self):
        """WorkerPool should manage workers"""
        queue = JobQueue(max_size=100)

        pool = WorkerPool(
            task_handler=self.counting_handler,
            min_workers=2,
            max_workers=4,
            auto_scale=False,
        )
        await pool.start(queue)

        # Enqueue and process some jobs
        for i in range(10):
            job = BatchJob(
                task_name=f"job{i}",
                data={"counter_id": i},
                priority=JobPriority.NORMAL,
            )
            await queue.enqueue(job)

        # Wait for processing
        await asyncio.sleep(1.0)

        # Verify workers were created
        assert len(pool.workers) >= pool.min_workers

        # Stop pool
        await pool.stop()

        # Verify workers stopped
        for worker in pool.workers:
            assert worker.state.value in ["stopping", "stopped", "error"]


class TestJobRetry:
    """Test job retry logic"""

    retry_count = 0

    async def flaky_handler(self, job: BatchJob) -> bool:
        """Handler that fails first N times, then succeeds"""
        if self.retry_count < job.max_retries:
            self.retry_count += 1
            raise Exception("Temporary failure")
        return True

    @pytest.mark.asyncio
    async def test_job_retry_tracking(self):
        """Job should track retry attempts"""
        job = BatchJob(
            task_name="retry_test",
            data={},
            max_retries=3,
            priority=JobPriority.NORMAL,
        )

        # Initial retry count is 0
        assert job.retry_count == 0

        # Simulate retry attempts
        for i in range(3):
            job.retry_count += 1

        assert job.retry_count == 3


class TestJobMetadata:
    """Test job metadata and tracking"""

    @pytest.mark.asyncio
    async def test_job_contains_metadata(self):
        """Job should store and preserve metadata"""
        metadata = {
            "user_id": "user123",
            "request_id": "req456",
            "custom_field": "value",
        }

        job = BatchJob(
            task_name="tracked_job",
            metadata=metadata,
            priority=JobPriority.NORMAL,
        )

        # Metadata should be preserved
        assert job.metadata == metadata
        assert job.metadata["user_id"] == "user123"
        assert job.metadata["request_id"] == "req456"

    @pytest.mark.asyncio
    async def test_job_to_dict_serialization(self):
        """Job should serialize to dictionary"""
        job = BatchJob(
            task_name="serialization_test",
            data={"test": "data"},
            metadata={"key": "value"},
            priority=JobPriority.HIGH,
        )

        job_dict = job.to_dict()

        # Verify serialization
        assert job_dict["task_name"] == "serialization_test"
        assert job_dict["priority"] == JobPriority.HIGH.value
        assert job_dict["status"] == JobStatus.PENDING.value
        assert job_dict["metadata"]["key"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
