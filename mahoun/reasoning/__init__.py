"""
Reasoning Module
================

Multi-stage reasoning and knowledge graph integration for MAHOUN.

Version 2.1.0: Added Unified Reasoning Service combining symbolic FOL and neural reasoning.
"""
from typing import Any, List, Optional

__version__ = "2.1.0"

# Import unified reasoning service (always available)
try:
    from .unified_reasoning_service import (
        UnifiedReasoningService,
        ReasoningMode,
        ReasoningTask,
        ReasoningRequest,
        ReasoningResponse,
        forward_inference,
        prove_goal,
        answer_question,
    )
    UNIFIED_AVAILABLE = True
except ImportError:
    UNIFIED_AVAILABLE = False

# Conditional imports to avoid dependency issues
try:
    from .reasoning_engine import ReasoningEngine, ReasoningResult
except ImportError:
    ReasoningEngine: Optional[Any] = None
    ReasoningResult: Optional[Any] = None
try:
    from .policies import PolicyEngine, PolicyDecision
except ImportError:
    PolicyEngine: Optional[Any] = None
    PolicyDecision: Optional[Any] = None
try:
    from .chain_of_thought import ChainOfThoughtReasoner
except ImportError:
    ChainOfThoughtReasoner: Optional[Any] = None
try:
    from .causal_inference import CausalInferenceEngine
except ImportError:
    CausalInferenceEngine: Optional[Any] = None
try:
    from .knowledge_graph import LegalKnowledgeGraph
except ImportError:
    LegalKnowledgeGraph: Optional[Any] = None
try:
    from .ultra_reasoning_service import UltraReasoningService
except ImportError:
    UltraReasoningService: Optional[Any] = None
try:
    from .first_order_logic import FirstOrderLogicEngine, Term, Atom, Clause, Substitution
except ImportError:
    FirstOrderLogicEngine: Optional[Any] = None
    Term: Optional[Any] = None
    Atom: Optional[Any] = None
    Clause: Optional[Any] = None
    Substitution: Optional[Any] = None
try:
    from .forward_chaining import ForwardChainingEngine, ForwardChainingResult
except ImportError:
    ForwardChainingEngine: Optional[Any] = None
    ForwardChainingResult: Optional[Any] = None
try:
    from .backward_chaining import BackwardChainingEngine, BackwardChainingResult
except ImportError:
    BackwardChainingEngine: Optional[Any] = None
    BackwardChainingResult: Optional[Any] = None
try:
    from .symbolic_reasoner import SymbolicReasoningEngine, KnowledgeBase, ReasoningMode as SymbolicReasoningMode
except ImportError:
    SymbolicReasoningEngine: Optional[Any] = None
    KnowledgeBase: Optional[Any] = None
    SymbolicReasoningMode: Optional[Any] = None
# Always safe imports
try:
    from .reasoning_chain import ReasoningChain, ReasoningConfig, ReasoningMode, ReasoningResult
    __all__ = ["ReasoningChain", "ReasoningConfig", "ReasoningMode", "ReasoningResult"]
except ImportError:
    __all__: List[Any] = []
# Add optional exports
if ReasoningEngine:
    __all__.extend(["ReasoningEngine"])
if PolicyEngine:
    __all__.extend(["PolicyEngine", "PolicyDecision"])
if ChainOfThoughtReasoner:
    __all__.append("ChainOfThoughtReasoner")
if CausalInferenceEngine:
    __all__.append("CausalInferenceEngine")
if LegalKnowledgeGraph:
    __all__.append("LegalKnowledgeGraph")
if UltraReasoningService:
    __all__.append("UltraReasoningService")
if FirstOrderLogicEngine:
    __all__.extend(["FirstOrderLogicEngine", "Term", "Atom", "Clause", "Substitution"])
if ForwardChainingEngine:
    __all__.extend(["ForwardChainingEngine", "ForwardChainingResult"])
if BackwardChainingEngine:
    __all__.extend(["BackwardChainingEngine", "BackwardChainingResult"])
# Add unified reasoning exports
if UNIFIED_AVAILABLE:
    __all__.extend([
        "UnifiedReasoningService",
        "ReasoningMode", 
        "ReasoningTask",
        "ReasoningRequest",
        "ReasoningResponse",
        "forward_inference",
        "prove_goal", 
        "answer_question"
    ])
