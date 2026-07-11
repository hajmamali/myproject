"""
Core Protocol Definitions for MAHOUN

This module contains the fundamental protocol definitions that form
the contract boundaries for MAHOUN's architecture.

G-0 FREEZE STATUS: These protocols are candidates for G-0 freeze
and should not be modified without architecture review.
"""

from .ai_runtime import AIRuntimeProtocol, HealthStatus, ModelMetadata

__all__ = [
    "AIRuntimeProtocol", 
    "HealthStatus", 
    "ModelMetadata"
]