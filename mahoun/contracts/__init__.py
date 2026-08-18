"""
MAHOUN Governance Contract System
==================================

Classification: KERNEL / CONSTITUTIONAL / LAYERED ARCHITECTURE

This module provides formal verification contracts that work in conjunction
with Pydantic validation contracts (mahoun/schemas/contracts/).

Architecture Layers:
    Layer 3 (This Module): Governance Contracts DSL
        - Proactive validation (precondition/invariant/forbidden)
        - State-space verification
        - CI/CD gates
        - Determinism checking
        - Unbypassable enforcement via InvariantViolationError
    
    Layer 2 (mahoun/schemas/contracts/): Pydantic Validation
        - Runtime type safety
        - Field-level validation
        - Data integrity
    
    Layer 1: Python Type System

Key Exports:
    - GovernanceContract: Base class for all governance contracts
    - ContractState: State representation for contract evaluation
    - ContractEngine: Executes and validates contracts
    - InvariantViolationError: Unbypassable contract violation exception
    - VerdictExecutionResult: Immutable contract for verdict artifacts
    - compile_tests_to_contracts: AST-based test → contract compiler
    - run_determinism_check: Determinism verification (CRITICAL for Legal AI)

Usage Example:
    >>> from mahoun.contracts import GovernanceContract, ContractEngine, ContractState
    >>> 
    >>> class MyContract(GovernanceContract):
    ...     @property
    ...     def name(self) -> str:
    ...         return "MyContract"
    ...     
    ...     @property
    ...     def domain(self) -> str:
    ...         return "LEDGER"
    ...     
    ...     def precondition(self, state: ContractState, input_data) -> bool:
    ...         return "ledger_initialized" in state.context
    ...     
    ...     def invariant(self, state: ContractState) -> bool:
    ...         return len(state.history) > 0
    ...     
    ...     def forbidden(self, state: ContractState, input_data) -> bool:
    ...         return input_data is None
    >>> 
    >>> engine = ContractEngine()
    >>> engine.register_contract(MyContract())
    >>> state = ContractState(context={"ledger_initialized": True}, data=None, history=[])
    >>> violations = engine.run_validation(state, {"test": "data"})
    >>> assert len(violations) == 0

Integration with Pydantic Contracts:
    >>> from mahoun.schemas.contracts.ledger_contracts import LedgerEntryContract
    >>> from mahoun.contracts import GovernanceContract, ContractState
    >>> 
    >>> class LedgerIntegrityContract(GovernanceContract):
    ...     def forbidden(self, state: ContractState, input_data) -> bool:
    ...         try:
    ...             # Use Pydantic for validation
    ...             entry = LedgerEntryContract(**input_data)
    ...             return False  # Valid
    ...         except ValueError:
    ...             return True  # FORBIDDEN

For detailed architecture and usage, see:
    - docs/architecture/CONTRACT_SYSTEM.md
    - mahoun/contracts/base.py (GovernanceContract ABC)
    - mahoun/contracts/verdict_execution.py (InvariantViolationError framework)

Author: MAHOUN Constitutional Governance Council
Version: 1.0.0
"""

# ============================================================================
# Core Contract DSL
# ============================================================================

from mahoun.contracts.base import (
    GovernanceContract,
    ContractState,
)

# ============================================================================
# Contract Execution Engine
# ============================================================================

from mahoun.contracts.engine import (
    ContractEngine,
)

# ============================================================================
# Runtime Invariant Enforcement (HIGH-002)
# ============================================================================

from mahoun.contracts.verdict_execution import (
    # Core Exceptions
    InvariantViolationError,
    ContractValidationError,
    
    # Execution Contracts
    VerdictExecutionResult,
    PendingLedgerCommit,
    ExecutionContext,
    
    # Continuous Invariant Checking
    InvariantChecker,
    register_invariant_check,
    enforce_invariants,
)

# ============================================================================
# Contract Compilation & Analysis
# ============================================================================

from mahoun.contracts.compiler import (
    compile_tests_to_contracts,
    TestVisitor,
)

# ============================================================================
# Determinism Checking (CRITICAL for Legal AI)
# ============================================================================

from mahoun.contracts.determinism_test import (
    run_determinism_check,
)

# ============================================================================
# Dependency & Infrastructure Validation
# ============================================================================

from mahoun.contracts.dependency_audit import (
    audit_dependencies,
    CRITICAL_DEPENDENCIES,
)

# ============================================================================
# CI/CD Gates
# ============================================================================

# Note: gate.py, coverage.py, schema_validator.py are CLI tools
# Import them explicitly if needed:
#   from mahoun.contracts.gate import evaluate_gate
#   from mahoun.contracts.coverage import generate_coverage
#   from mahoun.contracts.schema_validator import validate_schema


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Core DSL
    "GovernanceContract",
    "ContractState",
    
    # Engine
    "ContractEngine",
    
    # Runtime Enforcement
    "InvariantViolationError",
    "ContractValidationError",
    "VerdictExecutionResult",
    "PendingLedgerCommit",
    "ExecutionContext",
    "InvariantChecker",
    "register_invariant_check",
    "enforce_invariants",
    
    # Compilation
    "compile_tests_to_contracts",
    "TestVisitor",
    
    # Determinism
    "run_determinism_check",
    
    # Infrastructure
    "audit_dependencies",
    "CRITICAL_DEPENDENCIES",
]


# ============================================================================
# Version Information
# ============================================================================

__version__ = "1.0.0"
__author__ = "MAHOUN Constitutional Governance Council"
__classification__ = "KERNEL / CONSTITUTIONAL / LAYERED ARCHITECTURE"
