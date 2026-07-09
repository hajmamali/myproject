"""
🧠 MAHOUN Reasoning Module - Smart Imports
==========================================

Multi-stage reasoning and knowledge graph integration for MAHOUN.

Main Classes:
    from mahoun.reasoning import ReasoningMode, UnifiedReasoningService
    from mahoun.reasoning import ChainOfThoughtReasoner

CANONICAL LOCATION GUIDE:
- ReasoningMode → USE unified_reasoning_service.py (60+ usage)
- ChainOfThoughtReasoner → USE chain_of_thought.py  
- ReasoningResult → Import from mahoun.core instead!

🚨 DEPRECATED/DUPLICATE LOCATIONS (DO NOT USE):
❌ from mahoun.reasoning.reasoning_recorder import ReasoningResult  
❌ from mahoun.reasoning.reasoning_chain import ReasoningMode
❌ from mahoun.reasoning.symbolic_reasoner import ReasoningMode

Version 2.1.0: Added Unified Reasoning Service combining symbolic FOL and neural reasoning.
"""
# 🎯 Canonical reasoning components (Developer Daily Use)
from .unified_reasoning_service import (
    UnifiedReasoningService,
    ReasoningMode,  # ✅ CANONICAL - 60+ files use this
    ReasoningTask,
    ReasoningRequest,
    ReasoningResponse,
)

# 🧠 Core reasoning engines
from .chain_of_thought import ChainOfThoughtReasoner  
from .evidence_linked_verdict import EvidenceLinkedVerdictEngine

# 🚨 IMPORT FROM MAHOUN.CORE INSTEAD:
# Use: from mahoun.core import ReasoningResult, ReasoningStep

__version__ = "2.1.0"

__all__ = [
    # Core reasoning service
    "UnifiedReasoningService",
    "ReasoningMode",  # ✅ CANONICAL
    "ReasoningTask",
    "ReasoningRequest", 
    "ReasoningResponse",
    # Reasoning engines
    "ChainOfThoughtReasoner",
    "EvidenceLinkedVerdictEngine",
]
