# Batch Processing System Guide

## Overview

The MahouN batch processing system (`mahoun/graph/batch/`) provides production-grade job queue and worker pool implementations for parallel processing of large-scale data operations. It is specifically designed to support:

- **Knowledge Graph Data Loading**: Load 4000+ legal entities, rules, and precedents in 7-10 minutes (3-4x speedup vs sequential loading)
- **Document Ingestion**: Process large document batches with OCR and NER
- **Graph Analytics**: Parallel execution of graph queries and transformations
- **Ledger Operations**: Atomic, governance-aware batch writes with auditability

## Architecture

### Core Components

```
mahoun/graph/batch/
├── models.py       # Job definitions (BatchJob, JobStatus, BatchConfig)
├── queue.py        # Queue implementations (JobQueue, PriorityQueue)
├── worker.py       # Worker and WorkerPool implementations
└── __init__.py     # Public API exports
```

### Key Classes

#### BatchJob
Represents a single job to be processed.

```python
BatchJob(
    task_name: str,           # Unique identifier for the task type
    data: dict,               # Payload (arbitrary dict)
    priority: JobPriority,    # LOW, NORMAL, HIGH, CRITICAL
    max_retries: int = 3,     # Automatic retry count
    timeout: float = 300.0,   # Job timeout in seconds
    metadata: dict = None,    # Optional metadata
)
```

**Status Enum**: `PENDING`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `RETRYING`

#### JobQueue (FIFO)
First-in-first-out async queue with metrics tracking.

```python
queue = JobQueue(max_size=1000)
await queue.enqueue(job, block=True, timeout=5.0)
job = await queue.dequeue(block=True, timeout=5.0)
size = await queue.size()
metrics = queue.get_metrics()
```

#### PriorityQueue
Priority-based queue using max-heap (higher priority → dequeue first). Same-priority jobs maintain FIFO order via internal counter.

```python
queue = PriorityQueue(max_size=1000)
# Jobs with CRITICAL priority dequeue before HIGH, which dequeue before NORMAL, etc.
```

#### Worker
Single async worker that processes jobs from a queue.

```python
handler = async def my_handler(job: BatchJob) -> Any:
    # Process job.data
    return result

resource_limits = ResourceLimits(
    max_memory_mb=1024,
    max_cpu_percent=50.0,
    max_gpu_memory_mb=2048,
)

worker = Worker(
    task_handler=handler,
    resource_limits=resource_limits,
    heartbeat_interval=10.0,
    max_consecutive_failures=5,
)

await worker.start(queue)
# ... process jobs ...
await worker.stop(graceful=True, timeout=30)
```

#### WorkerPool
Manages multiple workers with auto-scaling and load balancing.

```python
pool = WorkerPool(
    task_handler=handler,
    min_workers=2,
    max_workers=10,
    auto_scale=True,
    scale_up_threshold=0.8,      # Scale up when queue > 80% full
    scale_down_threshold=0.2,    # Scale down when queue < 20% full
    resource_limits=resource_limits,
)

await pool.start(queue)
# ... submit jobs ...
await pool.stop(graceful=True, timeout=30)
```

## Usage Patterns

### Pattern 1: Simple FIFO Processing

```python
from mahoun.graph.batch import JobQueue, Worker, BatchJob, JobPriority

async def process_document(job: BatchJob):
    """Process a single document"""
    doc_id = job.data['doc_id']
    text = job.data['text']
    
    # Process...
    return {'doc_id': doc_id, 'entities': []}

# Setup
queue = JobQueue(max_size=1000)
handler = process_document
resource_limits = ResourceLimits(max_memory_mb=2048)

# Create worker
worker = Worker(
    task_handler=handler,
    resource_limits=resource_limits,
)

# Submit jobs
for doc_id in range(100):
    job = BatchJob(
        task_name="process_doc",
        data={'doc_id': doc_id, 'text': 'Lorem ipsum...'},
        priority=JobPriority.NORMAL,
        timeout=60.0,
    )
    await queue.enqueue(job)

# Process
await worker.start(queue)
await asyncio.sleep(30)  # Let worker process
await worker.stop()
```

### Pattern 2: Priority-Based Processing

For scenarios where certain jobs need higher priority (e.g., statutes before precedents).

```python
from mahoun.graph.batch import PriorityQueue, WorkerPool, BatchJob, JobPriority

async def load_legal_data(job: BatchJob):
    """Load legal entities, statutes, or precedents"""
    data_type = job.data['type']  # 'statute', 'precedent', 'entity'
    
    if data_type == 'statute':
        # Load statute from database
        pass
    elif data_type == 'precedent':
        # Load precedent
        pass
    # ...
    
    return {'loaded': True, 'type': data_type}

# Setup priority queue
queue = PriorityQueue(max_size=5000)

# Enqueue with priorities
# Statutes: HIGH priority (most important)
for statute_id in range(1600):
    job = BatchJob(
        task_name="load_legal",
        data={'type': 'statute', 'id': statute_id},
        priority=JobPriority.HIGH,  # High priority
    )
    await queue.enqueue(job)

# Precedents: NORMAL priority
for precedent_id in range(2300):
    job = BatchJob(
        task_name="load_legal",
        data={'type': 'precedent', 'id': precedent_id},
        priority=JobPriority.NORMAL,  # Normal priority
    )
    await queue.enqueue(job)

# Entities: LOW priority
for entity_id in range(1000):
    job = BatchJob(
        task_name="load_legal",
        data={'type': 'entity', 'id': entity_id},
        priority=JobPriority.LOW,  # Low priority
    )
    await queue.enqueue(job)

# Create pool with multiple workers
pool = WorkerPool(
    task_handler=load_legal_data,
    min_workers=4,
    max_workers=8,
    auto_scale=True,
)

await pool.start(queue)

# Monitor progress
while not await queue.is_empty():
    metrics = queue.get_metrics()
    print(f"Queue size: {metrics.current_size}, Processed: {metrics.total_dequeued}")
    await asyncio.sleep(5)

await pool.stop()
```

### Pattern 3: Distributed Job Handler

For complex operations where job handling depends on job type:

```python
async def unified_handler(job: BatchJob) -> dict:
    """Route jobs to specialized handlers"""
    task_name = job.task_name
    
    if task_name == 'ingest_document':
        return await handle_ingest(job)
    elif task_name == 'extract_entities':
        return await handle_extraction(job)
    elif task_name == 'build_graph':
        return await handle_graph(job)
    else:
        raise ValueError(f"Unknown task: {task_name}")

async def handle_ingest(job):
    """Ingest and OCR document"""
    # Implementation
    return {}

async def handle_extraction(job):
    """Extract legal entities"""
    # Implementation
    return {}

async def handle_graph(job):
    """Build graph structure"""
    # Implementation
    return {}
```

## Advanced Configuration

### Resource Limits

Control per-worker resource consumption:

```python
from mahoun.graph.batch import ResourceLimits

limits = ResourceLimits(
    max_memory_mb=4096,      # Max 4GB memory per worker
    max_cpu_percent=80.0,    # Max 80% CPU
    max_gpu_memory_mb=8192,  # Max 8GB GPU memory (if available)
)

# ResourceLimits provides resource checking methods
if limits.check_memory():
    print("Memory available")
if limits.check_cpu():
    print("CPU available")
```

### Auto-Scaling Configuration

WorkerPool auto-scaling adjusts worker count based on queue utilization:

```python
pool = WorkerPool(
    task_handler=handler,
    min_workers=2,           # Always maintain at least 2 workers
    max_workers=16,          # Never exceed 16 workers
    auto_scale=True,         # Enable auto-scaling
    scale_up_threshold=0.8,  # Scale up when queue > 80% full
    scale_down_threshold=0.2,  # Scale down when queue < 20% full
)
```

### Job Retry Configuration

Jobs automatically retry on failure:

```python
job = BatchJob(
    task_name="risky_task",
    data={'url': 'https://...'},
    max_retries=5,  # Retry up to 5 times
    timeout=30.0,   # Each attempt has 30 second timeout
)
```

## Monitoring and Metrics

### Queue Metrics

```python
metrics = queue.get_metrics()

print(f"Total enqueued: {metrics.total_enqueued}")
print(f"Total dequeued: {metrics.total_dequeued}")
print(f"Current size: {metrics.current_size}")
print(f"Max size reached: {metrics.max_size_reached}")
print(f"Avg wait time: {metrics.avg_wait_time:.2f}s")
print(f"Priority distribution: {metrics.priority_counts}")
```

### Job Status Tracking

```python
job = await queue.dequeue()

print(f"Job ID: {job.job_id}")
print(f"Status: {job.status}")
print(f"Retry count: {job.retry_count}")
print(f"Execution time: {job.execution_time:.2f}s")
print(f"Assigned to: {job.worker_id}")

if job.status == JobStatus.FAILED:
    print(f"Error: {job.error}")
```

## Performance Characteristics

### Throughput

Based on benchmark tests with typical workloads:

| Workload | Workers | Queue Type | Throughput |
|----------|---------|-----------|-----------|
| Document ingestion (120s/doc) | 8 | FIFO | ~7 docs/min |
| Entity extraction (5s/entity) | 4 | Priority | ~48 entities/min |
| Graph building (2s/rule) | 4 | FIFO | ~120 rules/min |
| Knowledge Graph load (mixed) | 10 | Priority | 4000+ facts / 7-10 min |

### Latency

- Job enqueue: < 1ms
- Job dequeue: < 1ms (FIFO), < 5ms (Priority)
- Job dispatch to worker: < 10ms

### Resource Usage

- Per worker memory: ~50-100MB base
- Queue overhead: ~10KB per 1000 jobs
- Metrics tracking: < 1% CPU overhead

## Common Patterns

### Pattern: Knowledge Graph Loader (Reference Implementation)

See [KNOWLEDGE_GRAPH_LOADER_GUIDE.md](./KNOWLEDGE_GRAPH_LOADER_GUIDE.md) for complete implementation.

```python
# Use PriorityQueue for statutes > precedents > entities
# Use WorkerPool with 4 workers for statutes, 4 for precedents, 2 for entities
# Target: 4000+ facts in 7-10 minutes

# Expected speedup: 3-4x faster than sequential loading (30 min → 7-10 min)
```

### Pattern: Fault-Tolerant Batch Processing

```python
async def resilient_handler(job: BatchJob):
    """Handler with automatic retry logic"""
    try:
        return await do_work(job)
    except TransientError:
        raise  # Will trigger automatic retry
    except PermanentError as e:
        return {'error': str(e), 'fatal': True}
```

### Pattern: Graceful Shutdown

```python
async def shutdown_gracefully(pool, queue, timeout=30):
    """Shutdown pool, allowing in-progress jobs to complete"""
    
    # Signal stop
    await pool.stop(graceful=True, timeout=timeout)
    
    # Check for orphaned jobs
    size = await queue.size()
    if size > 0:
        print(f"Warning: {size} jobs still in queue")
```

## Troubleshooting

### High Queue Depth

**Problem**: Queue size keeps growing, workers falling behind.

**Solutions**:
1. Increase worker count (increase `max_workers` in WorkerPool)
2. Reduce per-job processing time (optimize handler)
3. Enable auto-scaling: `auto_scale=True`
4. Check resource limits (may be throttling workers)

### High Error Rate

**Problem**: Jobs failing frequently.

**Solutions**:
1. Increase `max_retries` on job
2. Increase `timeout` (may be too aggressive)
3. Check resource limits
4. Add error handling/logging to handler
5. Review error messages in failed job logs

### Memory Growth

**Problem**: Memory usage growing over time.

**Solutions**:
1. Reduce worker count (fewer concurrent jobs)
2. Add resource limits: `ResourceLimits(max_memory_mb=...)`
3. Check for memory leaks in job handler
4. Reduce queue `max_size`

### Uneven Load Distribution

**Problem**: Some workers busy, others idle (even with auto-scaling).

**Solutions**:
1. Check if certain jobs are much slower than others
2. Use PriorityQueue to prioritize faster jobs
3. Adjust `scale_up_threshold` to be more aggressive
4. Check for slow external dependencies (database, network)

## Best Practices

1. **Always use graceful shutdown**: `await pool.stop(graceful=True, timeout=30)`
2. **Set appropriate timeouts**: Not too short (false failures), not too long (blocking)
3. **Monitor metrics**: Track queue size and error rates
4. **Use priorities wisely**: High priority for critical/fast jobs, low for background
5. **Resource limits matter**: Prevent resource exhaustion on shared systems
6. **Test handlers thoroughly**: Batch systems amplify buggy handlers
7. **Plan capacity**: Start conservative, scale up incrementally
8. **Log generously**: Include job ID in logs for tracking

## Integration with MahouN

### Governance Integration

Jobs inherit governance context automatically:

```python
async def governed_job_handler(job: BatchJob):
    """Handler with automatic governance context"""
    # Access current governance context via ContextVar
    from mahoun.core.governance import get_governance_context
    
    ctx = get_governance_context()
    # All Neo4j writes automatically routed through mutation boundary
```

### Ledger Integration

Batch writes can integrate with ledger for auditability:

```python
from mahoun.ledger.writer import EvidenceLedgerWriter

writer = EvidenceLedgerWriter()

async def logged_handler(job: BatchJob):
    """Handler with ledger logging"""
    result = await do_work(job)
    await writer.commit_batch(
        job_id=job.job_id,
        data=result,
        metadata={'source': 'batch_system'}
    )
    return result
```

## Testing

Run the comprehensive test suite:

```bash
cd /home/haji/Desktop/KingMahouN
source venv/bin/activate
pytest tests/graph/test_batch_system_integration.py -v
```

Expected output: **14 passed**

Tests verify:
- FIFO queue ordering
- Priority queue max-heap ordering
- Worker job execution and error handling
- Job timeout enforcement
- Job retry tracking
- Metadata preservation
- Queue metrics collection
- Worker pool parallel execution
- Worker pool lifecycle

## Example: Complete End-to-End Usage

```python
import asyncio
from mahoun.graph.batch import (
    BatchJob, BatchConfig, JobPriority, JobStatus,
    PriorityQueue, WorkerPool, ResourceLimits
)

async def example():
    """Complete batch processing example"""
    
    # 1. Define handler
    async def process_item(job: BatchJob):
        item = job.data
        print(f"Processing {item['id']}")
        
        # Simulate work
        await asyncio.sleep(0.1)
        
        return {'result': item['id'] * 2}
    
    # 2. Create queue with priority
    queue = PriorityQueue(max_size=1000)
    
    # 3. Create resource limits
    limits = ResourceLimits(max_memory_mb=2048)
    
    # 4. Create worker pool
    pool = WorkerPool(
        task_handler=process_item,
        min_workers=2,
        max_workers=4,
        auto_scale=True,
        resource_limits=limits,
    )
    
    # 5. Submit jobs
    for i in range(100):
        job = BatchJob(
            task_name="process",
            data={'id': i},
            priority=JobPriority.HIGH if i % 10 == 0 else JobPriority.NORMAL,
            timeout=30.0,
        )
        await queue.enqueue(job)
    
    # 6. Start processing
    await pool.start(queue)
    
    # 7. Wait for completion
    while not await queue.is_empty():
        metrics = queue.get_metrics()
        print(f"Progress: {metrics.total_dequeued}/{metrics.total_enqueued}")
        await asyncio.sleep(1)
    
    # 8. Graceful shutdown
    await pool.stop(graceful=True)
    
    print("Done!")

if __name__ == '__main__':
    asyncio.run(example())
```

## References

- Implementation: `mahoun/graph/batch/`
- Integration Tests: `tests/graph/test_batch_system_integration.py`
- Neo4j Connection: `mahoun/graph/neo4j/connection.py`
- Governance: `mahoun/core/governance/`
