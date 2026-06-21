"""
Contract Schemas
================
Explicit contracts for core module interfaces.

This package defines formal contracts that core modules must adhere to,
replacing implicit assumptions with explicit, testable specifications.
"""

from .reasoning_contracts import (
    # EvidenceLinkedVerdictEngine
    EvidenceReferenceContract,
    VerdictStepContract,
    GenerateVerdictInput,
    GenerateVerdictOutput,
    GenerateVerdictError,
    # ChainOfThoughtReasoner
    ReasonInput,
    ReasoningStepContract,
    ReasonOutput,
    ReasonError,
    # DeepLegalReasoningEngine
    DeepReasonInput,
    CausalRelationContract,
    DeepReasonOutput,
    DeepReasonError,
)

from .graph_contracts import (
    # Entity and Relationship
    EntityContract,
    RelationshipContract,
    # Build Graph
    BuildGraphInput,
    GraphMetricsContract,
    GraphNodeContract,
    GraphEdgeContract,
    BuildGraphOutput,
    BuildGraphError,
    # Query Operations
    QueryNeighborsInput,
    QueryNeighborsOutput,
    FindPathInput,
    FindPathOutput,
    GetSubgraphInput,
    GetSubgraphOutput,
    GraphQueryError,
)

from .ledger_contracts import (
    # Ledger Entry
    LedgerEntryContract,
    # Write Operations
    WriteLedgerInput,
    WriteLedgerOutput,
    WriteLedgerError,
    # Verification
    VerifyIntegrityInput,
    VerifyIntegrityOutput,
    VerifyIntegrityError,
    # Invariants
    InvariantSpecContract,
    GetInvariantsOutput,
    # Configuration
    LedgerBackendConfig,
)

from .invariants_contracts import (
    # Invariant Specification
    InvariantSpecContract as InvariantSpec,
    GetInvariantByIdInput,
    GetInvariantByIdOutput,
    GetInvariantByIdError,
    GetAllInvariantsOutput,
    # Version Management
    InvariantVersionContract,
    GetCurrentVersionOutput,
    GetVersionHistoryOutput,
    # Validation
    ValidateInvariantInput,
    ValidateInvariantOutput,
    ValidateInvariantError,
    # Registry
    RegisterInvariantInput,
    RegisterInvariantOutput,
    RegisterInvariantError,
    # Statistics
    InvariantStatisticsContract,
    GetInvariantStatisticsOutput,
)

__all__ = [
    # EvidenceLinkedVerdictEngine
    "EvidenceReferenceContract",
    "VerdictStepContract",
    "GenerateVerdictInput",
    "GenerateVerdictOutput",
    "GenerateVerdictError",
    # ChainOfThoughtReasoner
    "ReasonInput",
    "ReasoningStepContract",
    "ReasonOutput",
    "ReasonError",
    # DeepLegalReasoningEngine
    "DeepReasonInput",
    "CausalRelationContract",
    "DeepReasonOutput",
    "DeepReasonError",
    # Entity and Relationship
    "EntityContract",
    "RelationshipContract",
    # Build Graph
    "BuildGraphInput",
    "GraphMetricsContract",
    "GraphNodeContract",
    "GraphEdgeContract",
    "BuildGraphOutput",
    "BuildGraphError",
    # Query Operations
    "QueryNeighborsInput",
    "QueryNeighborsOutput",
    "FindPathInput",
    "FindPathOutput",
    "GetSubgraphInput",
    "GetSubgraphOutput",
    "GraphQueryError",
    # Ledger Entry
    "LedgerEntryContract",
    # Write Operations
    "WriteLedgerInput",
    "WriteLedgerOutput",
    "WriteLedgerError",
    # Verification
    "VerifyIntegrityInput",
    "VerifyIntegrityOutput",
    "VerifyIntegrityError",
    # Invariants
    "InvariantSpecContract",
    "GetInvariantsOutput",
    # Configuration
    "LedgerBackendConfig",
    # Invariant Specification
    "InvariantSpec",
    "GetInvariantByIdInput",
    "GetInvariantByIdOutput",
    "GetInvariantByIdError",
    "GetAllInvariantsOutput",
    # Version Management
    "InvariantVersionContract",
    "GetCurrentVersionOutput",
    "GetVersionHistoryOutput",
    # Validation
    "ValidateInvariantInput",
    "ValidateInvariantOutput",
    "ValidateInvariantError",
    # Registry
    "RegisterInvariantInput",
    "RegisterInvariantOutput",
    "RegisterInvariantError",
    # Statistics
    "InvariantStatisticsContract",
    "GetInvariantStatisticsOutput",
]

__version__ = "1.0.0"
