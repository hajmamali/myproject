"""
Guardrails Adapter for Reasoning Module
========================================

This adapter module provides runtime access to guardrails functionality
without creating compile-time dependencies.

ARCHITECTURE NOTE:
- This is a NON-CORE adapter module
- It bridges reasoning (core) with guardrails (non-core)
- Uses runtime imports to avoid circular dependencies
- Provides graceful degradation when guardrails unavailable
"""

import logging
from typing import Optional, Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from mahoun.core.protocols import ContradictionDetectorProtocol

logger = logging.getLogger(__name__)


def create_contradiction_detector() -> Optional['ContradictionDetectorProtocol']:
    """
    Create ContradictionDetector instance with runtime import.
    
    Returns:
        ContradictionDetectorProtocol implementation or None if unavailable
        
    Note:
        This function uses runtime import to avoid compile-time dependency
        from reasoning (core) to guardrails (non-core).
    """
    try:
        from mahoun.guardrails.ultra_nli_verifier import ContradictionDetector
        detector = ContradictionDetector()
        logger.info("ContradictionDetector created successfully")
        return detector
    except ImportError as e:
        logger.info(f"ContradictionDetector not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"ContradictionDetector creation failed: {e}")
        return None
