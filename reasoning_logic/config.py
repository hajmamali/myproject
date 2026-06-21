"""
MAHOUN Reasoning Engine Configuration
======================================

Dual-mode architecture support for DESKTOP_MINIMAL and ENTERPRISE_FULL modes.

This module enforces resource constraints and semantic invariance across
execution modes as mandated by the MAHOUN architecture guidelines.

Author: MAHOUN Team
"""

from enum import Enum
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """
    Execution mode for MAHOUN reasoning engine
    
    DESKTOP_MINIMAL: Resource-constrained mode for laptops (8GB RAM, CPU-bound)
    ENTERPRISE_FULL: Full-featured mode for servers (unlimited resources)
    """
    DESKTOP_MINIMAL = "minimal"
    ENTERPRISE_FULL = "full"


class ResourceLimitError(Exception):
    """Raised when operation exceeds resource limits for current mode"""
    pass


def get_execution_mode() -> ExecutionMode:
    """
    Get current execution mode from environment
    
    Returns:
        ExecutionMode enum value
        
    Environment Variables:
        MAHOUN_EXECUTION_MODE: "minimal" or "full" (default: "minimal")
    """
    mode_str = os.getenv("MAHOUN_EXECUTION_MODE", "minimal").lower()
    
    if mode_str == "full":
        return ExecutionMode.ENTERPRISE_FULL
    else:
        return ExecutionMode.DESKTOP_MINIMAL


def enforce_resource_limit(operation: str, mode: Optional[ExecutionMode] = None):
    """
    Enforce resource limits based on execution mode
    
    Args:
        operation: Operation identifier to check
        mode: Execution mode (defaults to current mode from environment)
        
    Raises:
        ResourceLimitError: If operation is prohibited in current mode
        
    Prohibited Operations in DESKTOP_MINIMAL:
        - full_graph_build: Full Neo4j graph construction
        - heavy_neo4j: Heavy Neo4j queries
        - stress_test: Stress tests with 10,000+ facts
        - embedding_pipeline: Embedding-intensive operations
        - concurrent_graph: High-throughput concurrent graph operations
    """
    if mode is None:
        mode = get_execution_mode()
    
    if mode == ExecutionMode.DESKTOP_MINIMAL:
        prohibited_operations = {
            "full_graph_build": "Full graph construction requires ENTERPRISE_FULL mode",
            "heavy_neo4j": "Heavy Neo4j operations require ENTERPRISE_FULL mode",
            "stress_test": "Stress tests require ENTERPRISE_FULL mode",
            "embedding_pipeline": "Embedding pipelines require ENTERPRISE_FULL mode",
            "concurrent_graph": "Concurrent graph operations require ENTERPRISE_FULL mode",
        }
        
        if operation in prohibited_operations:
            error_msg = (
                f"Operation '{operation}' is prohibited in DESKTOP_MINIMAL mode. "
                f"{prohibited_operations[operation]}. "
                f"Set MAHOUN_EXECUTION_MODE=full to enable."
            )
            logger.error(error_msg)
            raise ResourceLimitError(error_msg)
    
    # ENTERPRISE_FULL mode: all operations allowed
    logger.debug(f"Operation '{operation}' allowed in {mode.value} mode")


def get_resource_limits(mode: Optional[ExecutionMode] = None) -> dict:
    """
    Get resource limits for current execution mode
    
    Args:
        mode: Execution mode (defaults to current mode from environment)
        
    Returns:
        Dictionary with resource limits
    """
    if mode is None:
        mode = get_execution_mode()
    
    if mode == ExecutionMode.DESKTOP_MINIMAL:
        return {
            "max_facts": 10000,
            "max_rules": 1000,
            "max_iterations": 1000,
            "max_depth": 50,
            "max_memory_mb": 500,
            "timeout_seconds": 30,
            "enable_graph": False,
            "enable_embeddings": False,
        }
    else:  # ENTERPRISE_FULL
        return {
            "max_facts": 1000000,
            "max_rules": 100000,
            "max_iterations": 100000,
            "max_depth": 1000,
            "max_memory_mb": 16000,
            "timeout_seconds": 300,
            "enable_graph": True,
            "enable_embeddings": True,
        }


def validate_mode_invariance(operation: str, result_minimal: any, result_full: any) -> bool:
    """
    Validate that operation produces semantically equivalent results across modes
    
    This is a critical invariant: DESKTOP_MINIMAL and ENTERPRISE_FULL must
    produce the same logical results, even if performance differs.
    
    Args:
        operation: Operation name
        result_minimal: Result from DESKTOP_MINIMAL mode
        result_full: Result from ENTERPRISE_FULL mode
        
    Returns:
        True if results are semantically equivalent
        
    Raises:
        AssertionError: If semantic divergence detected
    """
    # TODO: Implement semantic equivalence checking
    # For now, just log
    logger.info(f"Mode invariance check for '{operation}': Not yet implemented")
    return True


# Module-level configuration
CURRENT_MODE = get_execution_mode()
RESOURCE_LIMITS = get_resource_limits(CURRENT_MODE)

logger.info(f"MAHOUN Reasoning Engine initialized in {CURRENT_MODE.value} mode")
logger.debug(f"Resource limits: {RESOURCE_LIMITS}")
