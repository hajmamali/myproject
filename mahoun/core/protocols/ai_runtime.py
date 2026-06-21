#!/usr/bin/env python3
"""
AI Runtime Protocol - G-0 FREEZE CANDIDATE

This module defines the core AI Runtime Protocol that must remain stable
across all future model implementations to prevent kernel modifications.

CRITICAL: This interface MUST be frozen before first GGUF integration
to ensure that future model additions (Qwen, Llama, Mistral, Phi, Gemma) 
do not require changes to the governance kernel or core architecture.

Contract Guarantees:
- All implementations must support local-only operation
- All responses must be auditable and traceable
- Resource constraints must be respected
- Governance context must be propagated

Version: 1.0.0-rc1 (Release Candidate - Pre-G-0)
Freeze Status: PENDING (Must freeze before Task A.2 implementation)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List
import time
from pathlib import Path


class ModelStatus(Enum):
    """Model loading and health status enumeration"""
    NOT_LOADED = "not_loaded"
    LOADING = "loading" 
    READY = "ready"
    ERROR = "error"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    INTEGRITY_FAILED = "integrity_failed"


@dataclass(frozen=True)
class ModelMetadata:
    """
    Immutable model metadata for audit and governance
    
    G-0 FREEZE CANDIDATE: This structure must remain stable
    """
    model_id: str
    model_path: str
    model_format: str  # "GGUF", "SAFETENSORS", etc.
    file_size_bytes: int
    checksum_sha256: str
    parameters_count: Optional[int]  # Model parameters (1B, 3B, 7B, etc.)
    quantization: Optional[str]  # Q4_K_M, Q8_0, etc.
    context_window: int
    deployment_profile: str  # "desktop_minimal" | "enterprise_full"
    load_timestamp: float
    
    def __post_init__(self):
        """Validation for model metadata"""
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not Path(self.model_path).exists():
            raise ValueError(f"Model path does not exist: {self.model_path}")
        if self.file_size_bytes <= 0:
            raise ValueError("file_size_bytes must be positive")
        if len(self.checksum_sha256) != 64:  # SHA-256 hex length
            raise ValueError("checksum_sha256 must be valid SHA-256 hash")
        if self.context_window <= 0:
            raise ValueError("context_window must be positive")


@dataclass(frozen=True)
class HealthStatus:
    """
    AI Runtime health status information
    
    G-0 FREEZE CANDIDATE: This structure must remain stable
    """
    status: ModelStatus
    model_loaded: bool
    memory_usage_mb: float
    last_inference_time: Optional[float]
    error_message: Optional[str]
    uptime_seconds: float
    total_requests: int
    failed_requests: int
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for monitoring"""
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.failed_requests) / self.total_requests


class AIRuntimeProtocol(ABC):
    """
    Core AI Runtime Protocol - G-0 FREEZE CANDIDATE
    
    This abstract protocol defines the contract that all AI runtime 
    implementations must follow. This interface MUST remain stable
    to prevent future model integrations from requiring kernel changes.
    
    Design Principles:
    1. Local-First: All operations must work without network access
    2. Governance-Aware: All operations must support audit trails
    3. Resource-Constrained: Must respect deployment profile limits
    4. Error-Safe: Must fail gracefully and provide clear error messages
    
    Implementation Requirements:
    - MUST support GGUF format (minimum requirement)
    - MUST validate model integrity via SHA-256 checksums
    - MUST enforce resource constraints based on deployment profile
    - MUST generate audit events for all operations
    - MUST support graceful degradation and error recovery
    
    Future Compatibility:
    This interface is designed to support:
    - Multiple model formats (GGUF, SafeTensors, etc.)
    - Various model sizes (1B to 70B+ parameters)  
    - Different quantization levels (Q4_K_M, Q8_0, F16, etc.)
    - Multiple deployment profiles (desktop, server, cloud)
    """
    
    @abstractmethod
    def load_model(
        self,
        model_path: str,
        *,
        max_memory_mb: Optional[int] = None,
        context_window: int = 4096,
        quantization: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Load AI model from local path with resource validation
        
        Args:
            model_path: Local filesystem path to model file
            max_memory_mb: Maximum memory usage allowed (None = use profile limit)
            context_window: Token context window size
            quantization: Quantization format preference (Q4_K_M, Q8_0, etc.)
            **kwargs: Additional model-specific parameters
            
        Returns:
            True if model loaded successfully, False otherwise
            
        Raises:
            ModelNotFoundError: Model file does not exist
            ModelIntegrityError: Model checksum validation failed
            ResourceConstraintError: Model exceeds memory limits
            GovernanceViolationError: Operation violates governance rules
            
        Contract Guarantees:
        - MUST validate model file exists locally
        - MUST verify model integrity via SHA-256 checksum
        - MUST check resource constraints against deployment profile
        - MUST generate audit event for load operation
        - MUST be idempotent (safe to call multiple times)
        - MUST NOT make any network calls
        """
        pass
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> 'AIResponse':
        """
        Generate response from loaded model with governance context
        
        Args:
            prompt: Input text prompt for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            context: Governance and evidence context for audit trail
            correlation_id: Request correlation ID for tracing
            **kwargs: Additional generation parameters
            
        Returns:
            AIResponse object with generated text and metadata
            
        Raises:
            ModelNotLoadedError: No model is currently loaded
            GenerationError: Model generation failed
            GovernanceViolationError: Response violates governance rules
            ResourceExhaustedError: Insufficient resources for generation
            
        Contract Guarantees:
        - MUST require a model to be loaded first
        - MUST include governance context in response metadata
        - MUST generate audit event with correlation_id
        - MUST validate input prompt for safety and compliance
        - MUST enforce token limits based on deployment profile
        - MUST be thread-safe for concurrent requests
        """
        pass
    
    @abstractmethod
    def health_check(self) -> HealthStatus:
        """
        Check current health and status of AI runtime
        
        Returns:
            HealthStatus object with current runtime information
            
        Contract Guarantees:
        - MUST return current model loading status
        - MUST include memory usage information
        - MUST provide error details if runtime is unhealthy
        - MUST be fast (< 100ms response time)
        - MUST be safe to call frequently for monitoring
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> bool:
        """
        Unload current model to free resources
        
        Returns:
            True if model was unloaded successfully, False if no model loaded
            
        Contract Guarantees:
        - MUST free all model-related memory and resources
        - MUST be safe to call when no model is loaded
        - MUST generate audit event for unload operation
        - MUST clean up any temporary files or caches
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Optional[ModelMetadata]:
        """
        Get metadata about currently loaded model
        
        Returns:
            ModelMetadata object if model is loaded, None otherwise
            
        Contract Guarantees:
        - MUST return None if no model is currently loaded
        - MUST include complete model information for audit trails
        - MUST provide accurate resource usage information
        - MUST be fast (< 50ms response time)
        """
        pass
    
    # Optional methods for advanced implementations
    
    def validate_model_integrity(self, model_path: str, expected_checksum: str) -> bool:
        """
        Validate model file integrity against expected checksum
        
        Default implementation provided for consistency.
        Implementations MAY override for optimization.
        """
        import hashlib
        
        try:
            with open(model_path, 'rb') as f:
                file_hash = hashlib.sha256()
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(65536), b""):
                    file_hash.update(chunk)
            
            return file_hash.hexdigest() == expected_checksum.lower()
        except Exception:
            return False
    
    def estimate_memory_usage(self, model_path: str) -> int:
        """
        Estimate memory usage for model loading
        
        Default implementation based on file size.
        Implementations SHOULD override with more accurate estimates.
        
        Returns:
            Estimated memory usage in megabytes
        """
        try:
            file_size = Path(model_path).stat().st_size
            # Conservative estimate: file size + 20% overhead
            return int((file_size * 1.2) / (1024 * 1024))
        except Exception:
            return 0


# Custom exceptions for AI Runtime operations
class AIRuntimeError(Exception):
    """Base exception for all AI Runtime errors"""
    pass


class ModelNotFoundError(AIRuntimeError):
    """Raised when requested model file does not exist"""
    pass


class ModelIntegrityError(AIRuntimeError):
    """Raised when model fails integrity validation"""
    pass


class ModelNotLoadedError(AIRuntimeError):
    """Raised when operation requires loaded model but none is loaded"""
    pass


class ResourceConstraintError(AIRuntimeError):
    """Raised when operation would exceed resource constraints"""
    pass


class GenerationError(AIRuntimeError):
    """Raised when model generation fails"""
    pass


class GovernanceViolationError(AIRuntimeError):
    """Raised when operation violates governance rules"""
    pass


class ResourceExhaustedError(AIRuntimeError):
    """Raised when system resources are exhausted"""
    pass