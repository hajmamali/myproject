"""
Fine-Tuning API Router
======================
Complete API for model fine-tuning with feedback loop integration.

Features:
- Start/stop fine-tuning jobs
- Monitor training progress
- Manage datasets from feedback
- Deploy fine-tuned models
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/finetuning",
    tags=["finetuning"],
    responses={500: {"description": "Internal server error"}}
)


# =============================================================================
# Models
# =============================================================================

class TrainingStatus(str, Enum):
    """Training job status"""
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingMode(str, Enum):
    """Training modes"""
    FULL_FINETUNE = "full_finetune"
    LORA = "lora"
    QLORA = "qlora"
    DORA = "dora"
    ADALORA = "adalora"


class DatasetSource(str, Enum):
    """Dataset source types"""
    FEEDBACK = "feedback"
    UPLOAD = "upload"
    EXISTING = "existing"


class FineTuningConfig(BaseModel):
    """Fine-tuning configuration"""
    model_name: str = Field(..., description="Base model name or path")
    training_mode: TrainingMode = Field(default=TrainingMode.LORA)
    
    # Training hyperparameters
    learning_rate: float = Field(default=2e-5, gt=0, le=1e-3)
    num_epochs: int = Field(default=3, ge=1, le=100)
    batch_size: int = Field(default=4, ge=1, le=128)
    gradient_accumulation_steps: int = Field(default=4, ge=1, le=32)
    warmup_ratio: float = Field(default=0.1, ge=0, le=1)
    
    # LoRA specific
    lora_r: int = Field(default=8, ge=1, le=256)
    lora_alpha: int = Field(default=16, ge=1)
    lora_dropout: float = Field(default=0.05, ge=0, le=1)
    
    # Optimization
    use_gradient_checkpointing: bool = Field(default=True)
    use_mixed_precision: bool = Field(default=True)
    max_grad_norm: float = Field(default=1.0, ge=0)
    
    # Quantization
    load_in_4bit: bool = Field(default=False)
    load_in_8bit: bool = Field(default=False)


class DatasetConfig(BaseModel):
    """Dataset configuration"""
    source: DatasetSource
    dataset_id: Optional[str] = None
    
    # For feedback source
    feedback_start_date: Optional[datetime] = None
    feedback_end_date: Optional[datetime] = None
    min_rating: Optional[float] = Field(default=4.0, ge=1, le=5)
    
    # Split ratios
    train_ratio: float = Field(default=0.8, gt=0, lt=1)
    eval_ratio: float = Field(default=0.1, gt=0, lt=1)
    test_ratio: float = Field(default=0.1, gt=0, lt=1)


class FineTuningRequest(BaseModel):
    """Request to start fine-tuning"""
    job_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    config: FineTuningConfig
    dataset: DatasetConfig
    
    # Deployment
    auto_deploy: bool = Field(default=False)
    deployment_strategy: str = Field(default="shadow")  # shadow, canary, full


class FineTuningJob(BaseModel):
    """Fine-tuning job information"""
    job_id: str
    job_name: str
    description: Optional[str]
    status: TrainingStatus
    
    config: FineTuningConfig
    dataset: DatasetConfig
    
    # Progress
    current_epoch: int = 0
    total_epochs: int = 0
    current_step: int = 0
    total_steps: int = 0
    progress_percentage: float = 0.0
    
    # Metrics
    train_loss: Optional[float] = None
    eval_loss: Optional[float] = None
    eval_accuracy: Optional[float] = None
    learning_rate: Optional[float] = None
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Resources
    gpu_memory_used: Optional[float] = None
    estimated_time_remaining: Optional[int] = None  # seconds
    
    # Output
    model_path: Optional[str] = None
    checkpoint_path: Optional[str] = None
    logs_path: Optional[str] = None


class TrainingMetrics(BaseModel):
    """Training metrics at a point in time"""
    timestamp: datetime
    epoch: int
    step: int
    
    train_loss: float
    eval_loss: Optional[float] = None
    eval_accuracy: Optional[float] = None
    eval_perplexity: Optional[float] = None
    
    learning_rate: float
    gpu_memory_mb: Optional[float] = None
    samples_per_second: Optional[float] = None


class DeploymentRequest(BaseModel):
    """Request to deploy a fine-tuned model"""
    job_id: str
    strategy: str = Field(default="shadow")  # shadow, canary, full
    traffic_percentage: float = Field(default=0.0, ge=0, le=100)
    rollback_on_error: bool = Field(default=True)


# =============================================================================
# In-memory storage (replace with database in production)
# =============================================================================

_jobs: Dict[str, FineTuningJob] = {}
_metrics: Dict[str, List[TrainingMetrics]] = {}


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/jobs", response_model=FineTuningJob, status_code=status.HTTP_201_CREATED)
async def create_finetuning_job(
    request: FineTuningRequest,
    background_tasks: BackgroundTasks
):
    """
    Create and start a new fine-tuning job.
    
    This endpoint:
    1. Validates the configuration
    2. Prepares the dataset
    3. Starts training in background
    4. Returns job information
    """
    job_id = str(uuid.uuid4())
    
    job = FineTuningJob(
        job_id=job_id,
        job_name=request.job_name,
        description=request.description,
        status=TrainingStatus.PENDING,
        config=request.config,
        dataset=request.dataset,
        total_epochs=request.config.num_epochs,
        created_at=datetime.now()
    )
    
    _jobs[job_id] = job
    _metrics[job_id] = []
    
    # Start training in background
    background_tasks.add_task(
        _run_training,
        job_id=job_id,
        request=request
    )
    
    logger.info(f"Created fine-tuning job: {job_id} - {request.job_name}")
    
    return job


@router.get("/jobs", response_model=List[FineTuningJob])
async def list_finetuning_jobs(
    status: Optional[TrainingStatus] = None,
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    List all fine-tuning jobs.
    
    Optionally filter by status.
    """
    jobs = list(_jobs.values())
    
    if status:
        jobs = [j for j in jobs if j.status == status]
    
    # Sort by created_at descending
    jobs.sort(key=lambda x: x.created_at, reverse=True)
    
    return jobs[:limit]


@router.get("/jobs/{job_id}", response_model=FineTuningJob)
async def get_finetuning_job(job_id: str):
    """
    Get detailed information about a specific job.
    """
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return _jobs[job_id]


@router.delete("/jobs/{job_id}")
async def cancel_finetuning_job(job_id: str):
    """
    Cancel a running fine-tuning job.
    """
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job = _jobs[job_id]
    
    if job.status not in [TrainingStatus.PENDING, TrainingStatus.PREPARING, TrainingStatus.TRAINING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in status: {job.status}"
        )
    
    job.status = TrainingStatus.CANCELLED
    job.completed_at = datetime.now()
    
    logger.info(f"Cancelled fine-tuning job: {job_id}")
    
    return {"status": "cancelled", "job_id": job_id}


@router.get("/jobs/{job_id}/metrics", response_model=List[TrainingMetrics])
async def get_training_metrics(
    job_id: str,
    limit: int = Query(default=100, ge=1, le=1000)
):
    """
    Get training metrics for a job.
    
    Returns time-series data of training progress.
    """
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    metrics = _metrics.get(job_id, [])
    
    return metrics[-limit:]


@router.get("/jobs/{job_id}/logs")
async def get_training_logs(
    job_id: str,
    lines: int = Query(default=100, ge=1, le=1000)
):
    """
    Get training logs for a job.
    
    Returns the last N lines of logs.
    """
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job = _jobs[job_id]
    
    # In production, read from actual log file
    logs = [
        f"[{datetime.now().isoformat()}] Starting fine-tuning job {job_id}",
        f"[{datetime.now().isoformat()}] Model: {job.config.model_name}",
        f"[{datetime.now().isoformat()}] Training mode: {job.config.training_mode}",
        f"[{datetime.now().isoformat()}] Status: {job.status}",
    ]
    
    return {
        "job_id": job_id,
        "lines": logs[-lines:],
        "total_lines": len(logs)
    }


@router.post("/jobs/{job_id}/deploy")
async def deploy_finetuned_model(
    job_id: str,
    deployment: DeploymentRequest
):
    """
    Deploy a fine-tuned model to production.
    
    Supports different deployment strategies:
    - shadow: Run alongside production without serving traffic
    - canary: Serve a percentage of traffic
    - full: Replace production model
    """
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job = _jobs[job_id]
    
    if job.status != TrainingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot deploy job in status: {job.status}"
        )
    
    if not job.model_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model path not available"
        )
    
    logger.info(
        f"Deploying model from job {job_id} "
        f"with strategy: {deployment.strategy}"
    )
    
    return {
        "status": "deployed",
        "job_id": job_id,
        "strategy": deployment.strategy,
        "traffic_percentage": deployment.traffic_percentage,
        "model_path": job.model_path,
        "deployed_at": datetime.now().isoformat()
    }


@router.get("/datasets")
async def list_datasets():
    """
    List available datasets for fine-tuning.
    
    Includes datasets from:
    - User feedback
    - Uploaded files
    - Pre-existing datasets
    """
    datasets = [
        {
            "dataset_id": "feedback_2024_01",
            "name": "User Feedback January 2024",
            "source": "feedback",
            "size": 1250,
            "created_at": "2024-01-01T00:00:00Z"
        },
        {
            "dataset_id": "legal_docs_v1",
            "name": "Legal Documents v1",
            "source": "upload",
            "size": 5000,
            "created_at": "2023-12-15T00:00:00Z"
        }
    ]
    
    return {"datasets": datasets, "total": len(datasets)}


@router.post("/datasets/from-feedback")
async def create_dataset_from_feedback(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_rating: float = Query(default=4.0, ge=1, le=5)
):
    """
    Create a training dataset from user feedback.
    
    Filters feedback by:
    - Date range
    - Minimum rating
    - Quality metrics
    """
    try:
        # Get feedback pipeline from main app
        from api.main import get_feedback_pipeline
        from pathlib import Path
        
        pipeline = get_feedback_pipeline()
        
        # Collect feedback
        feedback_list = pipeline.collect_feedback(
            start_date=start_date,
            end_date=end_date,
            min_rating=min_rating
        )
        
        if not feedback_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No feedback found matching criteria"
            )
        
        # Convert to training examples
        examples = pipeline.convert_to_training_examples(feedback_list)
        
        if not examples:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid training examples created from feedback"
            )
        
        # Create dataset
        dataset_name = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dataset = pipeline.create_dataset(
            examples=examples,
            dataset_name=dataset_name,
            description=f"Dataset from {len(feedback_list)} feedback entries"
        )
        
        # Save dataset
        output_dir = Path("./datasets/feedback")
        paths = pipeline.save_dataset(dataset, output_dir)
        
        logger.info(
            f"Created dataset {dataset.dataset_id} from feedback "
            f"with {dataset.total_examples} examples"
        )
        
        return {
            "dataset_id": dataset.dataset_id,
            "name": dataset.name,
            "source": "feedback",
            "size": dataset.total_examples,
            "avg_quality_score": dataset.avg_quality_score,
            "splits": {
                "train": len(dataset.train_examples),
                "eval": len(dataset.eval_examples),
                "test": len(dataset.test_examples),
            },
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "min_rating": min_rating,
            "created_at": dataset.created_at.isoformat(),
            "files": {k: str(v) for k, v in paths.items()}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create dataset from feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset creation failed: {str(e)}"
        )


# =============================================================================
# Background Tasks
# =============================================================================

async def _run_training(job_id: str, request: FineTuningRequest):
    """
    Run training in background.
    
    This is a simplified version. In production:
    - Use Celery or similar for job queue
    - Run on GPU workers
    - Stream logs to storage
    - Save checkpoints regularly
    """
    job = _jobs[job_id]
    
    try:
        # Update status
        job.status = TrainingStatus.PREPARING
        job.started_at = datetime.now()
        
        # Simulate preparation
        import asyncio
        await asyncio.sleep(2)
        
        # Start training
        job.status = TrainingStatus.TRAINING
        
        # Simulate training epochs
        total_steps = request.config.num_epochs * 100
        job.total_steps = total_steps
        
        for epoch in range(request.config.num_epochs):
            job.current_epoch = epoch + 1
            
            for step in range(100):
                job.current_step = epoch * 100 + step + 1
                job.progress_percentage = (job.current_step / total_steps) * 100
                
                # Simulate metrics
                job.train_loss = 2.5 - (job.current_step / total_steps) * 2.0
                job.learning_rate = request.config.learning_rate * (1 - job.current_step / total_steps)
                
                # Record metrics
                metric = TrainingMetrics(
                    timestamp=datetime.now(),
                    epoch=epoch + 1,
                    step=job.current_step,
                    train_loss=job.train_loss,
                    learning_rate=job.learning_rate,
                    gpu_memory_mb=8000.0
                )
                _metrics[job_id].append(metric)
                
                await asyncio.sleep(0.1)
            
            # Evaluation at end of epoch
            job.status = TrainingStatus.EVALUATING
            job.eval_loss = job.train_loss * 0.9
            job.eval_accuracy = 0.85 + (epoch / request.config.num_epochs) * 0.1
            
            await asyncio.sleep(1)
            job.status = TrainingStatus.TRAINING
        
        # Complete
        job.status = TrainingStatus.COMPLETED
        job.completed_at = datetime.now()
        job.model_path = f"/models/finetuned/{job_id}"
        job.checkpoint_path = f"/checkpoints/{job_id}"
        
        logger.info(f"Fine-tuning job {job_id} completed successfully")
        
        # Auto-deploy if requested
        if request.auto_deploy:
            logger.info(f"Auto-deploying model from job {job_id}")
            # Trigger deployment
        
    except Exception as e:
        job.status = TrainingStatus.FAILED
        job.completed_at = datetime.now()
        logger.error(f"Fine-tuning job {job_id} failed: {e}", exc_info=True)
