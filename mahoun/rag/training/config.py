from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# ENUMS & TYPES
# ============================================================================

class TrainingMode(str, Enum):
    """Training modes"""
    FULL_FINETUNE = "full_finetune"
    LORA = "lora"
    QLORA = "qlora"
    DORA = "dora"  # Weight-Decomposed Low-Rank Adaptation
    ADALORA = "adalora"  # Adaptive LoRA
    IA3 = "ia3"  # Infused Adapter by Inhibiting and Amplifying
    PREFIX_TUNING = "prefix_tuning"
    PROMPT_TUNING = "prompt_tuning"
    P_TUNING = "p_tuning"
    ADAPTER = "adapter"


class QuantizationMode(str, Enum):
    """Quantization modes"""
    NONE = "none"
    INT8 = "int8"
    INT4 = "int4"
    FP8 = "fp8"
    GPTQ = "gptq"
    AWQ = "awq"
    GGUF = "gguf"


class DistributedBackend(str, Enum):
    """Distributed training backends"""
    NONE = "none"
    DDP = "ddp"  # DistributedDataParallel
    FSDP = "fsdp"  # Fully Sharded Data Parallel
    DEEPSPEED = "deepspeed"
    HOROVOD = "horovod"
    COLOSSALAI = "colossalai"


class OptimizationStrategy(str, Enum):
    """Optimization strategies"""
    STANDARD = "standard"
    GRADIENT_ACCUMULATION = "gradient_accumulation"
    GRADIENT_CHECKPOINTING = "gradient_checkpointing"
    MIXED_PRECISION = "mixed_precision"
    ZERO_OPTIMIZATION = "zero"  # ZeRO optimizer
    OFFLOAD_OPTIMIZER = "offload_optimizer"
    OFFLOAD_PARAMS = "offload_params"


# ============================================================================
# CONFIGURATION MODELS
# ============================================================================

class LoRAConfig(BaseModel):
    """LoRA configuration"""
    r: int = Field(default=8, ge=1, le=256, description="LoRA rank")
    lora_alpha: int = Field(default=16, ge=1, description="LoRA alpha")
    lora_dropout: float = Field(default=0.05, ge=0.0, le=1.0)
    target_modules: List[str] = Field(
        default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    bias: str = Field(default="none", pattern="^(none|all|lora_only)$")
    task_type: str = Field(default="CAUSAL_LM")
    
    # Advanced LoRA features
    use_rslora: bool = False  # Rank-Stabilized LoRA
    use_dora: bool = False  # Weight-Decomposed LoRA
    init_lora_weights: str = "gaussian"  # gaussian, kaiming, xavier
    
    # AdaLoRA specific
    adaptive: bool = False
    target_r: Optional[int] = None
    init_r: int = 12
    tinit: int = 0
    tfinal: int = 0
    deltaT: int = 1


class QuantizationConfig(BaseModel):
    """Quantization configuration"""
    mode: QuantizationMode = QuantizationMode.NONE
    load_in_4bit: bool = False
    load_in_8bit: bool = False
    
    # 4-bit config
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_quant_type: str = "nf4"  # nf4, fp4
    bnb_4bit_use_double_quant: bool = True
    
    # GPTQ config
    gptq_bits: int = 4
    gptq_group_size: int = 128
    gptq_desc_act: bool = False
    
    # AWQ config
    awq_bits: int = 4
    awq_group_size: int = 128


class TrainingConfig(BaseModel):
    """Ultra-advanced training configuration"""
    
    model_config = ConfigDict(
        use_enum_values=True,
        protected_namespaces=()   # Allow model_ prefix without warnings
    )
    
    # === BASIC SETTINGS ===
    output_dir: str = "./outputs"
    run_name: Optional[str] = None
    seed: int = 42
    
    # === MODEL SETTINGS ===
    model_name_or_path: str
    training_mode: TrainingMode = TrainingMode.LORA
    quantization: QuantizationConfig = Field(default_factory=QuantizationConfig)
    lora_config: Optional[LoRAConfig] = None
    
    # === TRAINING HYPERPARAMETERS ===
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 8
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.03
    max_grad_norm: float = 1.0
    
    # === OPTIMIZATION ===
    optimizer: str = "adamw_torch"  # adamw_torch, adamw_8bit, adafactor, lion
    lr_scheduler_type: str = "cosine"  # linear, cosine, polynomial, constant
    optimization_strategies: List[OptimizationStrategy] = Field(
        default_factory=lambda: [OptimizationStrategy.GRADIENT_ACCUMULATION]
    )
    
    # === MIXED PRECISION ===
    fp16: bool = False
    bf16: bool = True
    fp8: bool = False
    tf32: bool = True
    
    # === DISTRIBUTED TRAINING ===
    distributed_backend: DistributedBackend = DistributedBackend.NONE
    local_rank: int = -1
    world_size: int = 1
    
    # DeepSpeed config
    deepspeed_config: Optional[Dict[str, Any]] = None
    zero_stage: int = 2  # 0, 1, 2, 3
    
    # === GRADIENT CHECKPOINTING ===
    gradient_checkpointing: bool = True
    gradient_checkpointing_kwargs: Dict[str, Any] = Field(
        default_factory=lambda: {"use_reentrant": False}
    )
    
    # === LOGGING & MONITORING ===
    logging_steps: int = 10
    eval_steps: int = 100
    save_steps: int = 500
    save_total_limit: int = 3
    
    # Experiment tracking
    report_to: List[str] = Field(default_factory=lambda: ["tensorboard", "wandb"])
    wandb_project: Optional[str] = None
    wandb_entity: Optional[str] = None
    
    # === EVALUATION ===
    evaluation_strategy: str = "steps"  # no, steps, epoch
    metric_for_best_model: str = "eval_loss"
    greater_is_better: bool = False
    load_best_model_at_end: bool = True
    
    # === ADVANCED FEATURES ===
    
    # Curriculum learning
    curriculum_learning: bool = False
    curriculum_strategy: str = "difficulty"  # difficulty, length, diversity
    
    # Active learning
    active_learning: bool = False
    active_learning_strategy: str = "uncertainty"  # uncertainty, diversity, hybrid
    active_learning_budget: int = 1000
    
    # Multi-task learning
    multi_task: bool = False
    task_weights: Optional[Dict[str, float]] = None
    
    # Knowledge distillation
    distillation: bool = False
    teacher_model: Optional[str] = None
    distillation_alpha: float = 0.5
    distillation_temperature: float = 2.0
    
    # Model compression
    pruning: bool = False
    pruning_ratio: float = 0.3
    pruning_schedule: str = "gradual"  # oneshot, gradual, iterative
    
    # Continual learning
    continual_learning: bool = False
    replay_buffer_size: int = 10000
    ewc_lambda: float = 0.4  # Elastic Weight Consolidation
    
    # RLHF
    rlhf: bool = False
    reward_model: Optional[str] = None
    ppo_epochs: int = 4
    
    # === DATA SETTINGS ===
    max_seq_length: int = 2048
    packing: bool = False  # Pack multiple samples into one sequence
    dataset_text_field: str = "text"
    
    # Data augmentation
    data_augmentation: bool = False
    augmentation_strategies: List[str] = Field(
        default_factory=lambda: ["synonym_replacement", "back_translation"]
    )
    
    # === SAFETY & ROBUSTNESS ===
    early_stopping_patience: int = 3
    early_stopping_threshold: float = 0.0
    
    # Anomaly detection
    detect_anomaly: bool = False
    
    # Gradient clipping
    max_grad_norm: float = 1.0
    
    # === RESOURCE MANAGEMENT ===
    max_memory_MB: Optional[int] = None
    cpu_offload: bool = False
    pin_memory: bool = True
    dataloader_num_workers: int = 4
    
    # === CHECKPOINTING ===
    resume_from_checkpoint: Optional[str] = None
    save_safetensors: bool = True
