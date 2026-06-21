"""
MAHOUN Reasoning Logic Engine - Enterprise Grade
=================================================

A production-ready First-Order Logic (FOL) reasoning engine designed for
high-stakes legal AI applications.

Modules:
- core: Core data structures (Term, Atom, Fact, Rule)
- unification: Robinson's unification algorithm
- knowledge_base: Indexed knowledge base
- forward_chaining: Data-driven inference
- backward_chaining: Goal-driven proof search
- parser: FOL expression parser
- tms: Truth Maintenance System
- explanation: Explanation generation
- profiler: Performance profiling

Author: MAHOUN Team
License: Proprietary
Version: 1.0.0
"""

from reasoning_logic.core import (
    Term,
    TermType,
    Atom,
    Fact,
    Rule,
    Expression,
)

from reasoning_logic.unification import UnificationEngine

from reasoning_logic.knowledge_base import KnowledgeBase

from reasoning_logic.forward_chaining import (
    ForwardChaining,
    ForwardChainingStats,
)

from reasoning_logic.backward_chaining import (
    BackwardChaining,
    BackwardChainingResult,
    ProofNode,
    ProofStatus,
)

from reasoning_logic.parser import (
    FOLConverter,
    FOLPrinter,
    ParseError,
)

from reasoning_logic.tms import (
    TruthMaintenanceSystem,
    Justification,
    JustificationType,
    Contradiction,
)

from reasoning_logic.explanation import (
    ExplanationGenerator,
    ExplanationStyle,
    ExplanationLanguage,
    ExplanationConfig,
)

from reasoning_logic.profiler import (
    ReasoningProfiler,
    PerformanceMetrics,
    RuleProfile,
)


__all__ = [
    # Core types
    'Term',
    'TermType',
    'Atom',
    'Fact',
    'Rule',
    'Expression',
    
    # Engines
    'KnowledgeBase',
    'ForwardChaining',
    'ForwardChainingStats',
    'BackwardChaining',
    'BackwardChainingResult',
    'UnificationEngine',
    
    # Parser
    'FOLConverter',
    'FOLPrinter',
    'ParseError',
    
    # Proof tree
    'ProofNode',
    'ProofStatus',
    
    # Truth Maintenance
    'TruthMaintenanceSystem',
    'Justification',
    'JustificationType',
    'Contradiction',
    
    # Explanation
    'ExplanationGenerator',
    'ExplanationStyle',
    'ExplanationLanguage',
    'ExplanationConfig',
    
    # Profiling
    'ReasoningProfiler',
    'PerformanceMetrics',
    'RuleProfile',
]

__version__ = "1.0.0"
__author__ = "MAHOUN Team"
