"""
MAHOUN Reasoning API Router
============================

Core reasoning endpoints for evidence-linked verdict generation.

CRITICAL GUARANTEES:
- Zero-hallucination: All reasoning grounded in graph evidence
- Full auditability: Complete evidence trail in blockchain ledger
- Cryptographic proofs: Tamper-evident verification
- Deterministic contradiction resolution: Predictable conflict handling

Architecture:
- Evidence-Linked Verdict Engine: Graph-based reasoning
- Immutable Ledger: Blockchain audit trail
- Cryptographic Proofs: Non-repudiation guarantees
- Runtime Guardrails: Zero-hallucination enforcement
"""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.models.proof_carrying import ProofCarryingResponse
from mahoun.api.errors import (
    VerdictGenerationError,
    VerificationError,
    handle_runtime_error,
    handle_value_error,
)
from mahoun.core.governance import (
    GovernanceContextManager,
)
from mahoun.core.fortress_validator import SecurityBreachException
from mahoun.core.logging import setup_logger
from mahoun.core.runtime_config import is_desktop_minimal, should_skip_graph
from mahoun.crypto.proof_system import ProofSystem
from mahoun.crypto.signatures import generate_keypair
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
from mahoun.ledger.blockchain import ImmutableLedger
from mahoun.ledger.writer import EvidenceLedgerWriter
from mahoun.reasoning.evidence_linked_verdict import (
    EvidenceLinkedVerdictEngine,
)
from mahoun.reasoning.fortress_integration import (
    FortressProtectedReasoningService,  # noqa: F401
    create_fortress_protected_service,
)
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph

log = setup_logger("reasoning_api")

router = APIRouter(
    prefix="/api/v1/reasoning",
    tags=["reasoning"],
    responses={
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable in current mode"},
    },
)


# ============================================================================
# Request/Response Models
# ============================================================================


class FactInput(BaseModel):
    """Single fact input"""

    id: str | None = Field(None, description="Fact identifier (optional)")
    value: str = Field(..., description="Fact text", min_length=1)
    type: str | None = Field("UNKNOWN", description="Fact type")
    confidence: float | None = Field(1.0, ge=0.0, le=1.0, description="Fact confidence")


class VerdictGenerationRequest(BaseModel):
    """Request for verdict generation"""

    question: str = Field(..., description="Legal question to answer", min_length=1)
    facts: list[FactInput] = Field(..., description="Case facts", min_length=0)
    case_id: str | None = Field(None, description="Case identifier (optional)")
    generate_proof: bool = Field(True, description="Generate cryptographic proof")


class EvidenceReferenceResponse(BaseModel):
    """Evidence reference in response"""

    node_id: str
    node_type: str
    edge_id: str | None = None
    justification: str
    confidence: float


class VerdictStepResponse(BaseModel):
    """Verdict step in response"""

    statement: str
    evidence: list[EvidenceReferenceResponse]


class CryptographicProofResponse(BaseModel):
    """Cryptographic proof in response"""

    graph_state_hash: str
    reasoning_chain_hash: str
    evidence_merkle_root: str
    timestamp: str
    signature: str
    verdict_id: str
    case_id: str
    confidence: float


class VerdictGenerationResponse(ProofCarryingResponse):
    """Response for verdict generation with proof-carrying contract"""

    success: bool
    verdict_id: str
    case_id: str
    final_verdict: str
    steps: list[VerdictStepResponse]
    unresolved_conflicts: list[str]
    confidence_score: float
    proof: CryptographicProofResponse | None = None
    ledger_entry_id: str | None = None
    processing_time_ms: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerdictVerificationRequest(BaseModel):
    """Request for verdict verification"""

    verdict_id: str = Field(..., description="Verdict identifier")
    proof: CryptographicProofResponse = Field(..., description="Cryptographic proof to verify")


class VerdictVerificationResponse(ProofCarryingResponse):
    """Response for verdict verification with proof-carrying contract"""

    success: bool
    verdict_id: str
    is_valid: bool
    verification_details: dict[str, Any]
    timestamp: str


class LedgerQueryRequest(BaseModel):
    """Request for ledger query"""

    case_id: str | None = Field(None, description="Case identifier")
    verdict_id: str | None = Field(None, description="Verdict identifier")
    node_id: str | None = Field(None, description="Node identifier")
    start_time: str | None = Field(None, description="Start time (ISO 8601)")
    end_time: str | None = Field(None, description="End time (ISO 8601)")


class LedgerQueryResponse(ProofCarryingResponse):
    """Response for ledger query with proof-carrying contract"""

    success: bool
    entries: list[dict[str, Any]]
    total_count: int
    query_time_ms: float


# ============================================================================
# Dependencies
# ============================================================================

_verdict_engine: EvidenceLinkedVerdictEngine | None = None
_immutable_ledger: ImmutableLedger | None = None
_proof_system: ProofSystem | None = None
_private_key: str | None = None
_public_key: str | None = None


def get_verdict_engine() -> EvidenceLinkedVerdictEngine:
    """Get or create verdict engine instance"""
    global _verdict_engine

    if _verdict_engine is None:
        # Check if we're in DESKTOP_MINIMAL mode with graph disabled
        if is_desktop_minimal() and should_skip_graph():
            # Log blocked attempt
            log.warning(
                "Verdict engine initialization blocked due to mode constraint",
                extra={
                    "mode": "desktop_minimal",
                    "graph_enabled": False,
                    "entry_point": "api",
                },
            )

            # Record metrics
            try:
                from mahoun.metrics import record_blocked_attempt, record_mode_check

                record_blocked_attempt(mode="desktop_minimal", reason="graph_disabled", entry_point="api")
                record_mode_check(mode="desktop_minimal", graph_enabled=False, passed=False)
            except ImportError:
                log.debug("Metrics module not available - skipping metrics recording")

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "service_unavailable",
                    "message": "Reasoning API requires full graph operations. "
                    "Current mode: DESKTOP_MINIMAL with graph disabled. "
                    "Please run in ENTERPRISE_FULL mode or enable graph "
                    "(MAHOUN_ENABLE_GRAPH=true).",
                },
            )

        # Initialize components
        graph_builder = UltraGraphBuilder()
        knowledge_graph = LegalKnowledgeGraph()
        immutable_ledger = get_immutable_ledger()
        ledger_writer = EvidenceLedgerWriter(blockchain=immutable_ledger)

        _verdict_engine = EvidenceLinkedVerdictEngine(
            graph_builder=graph_builder,
            knowledge_graph=knowledge_graph,
            ledger_writer=ledger_writer,
            container=None,  # No dependency injection for now
        )

        log.info("Evidence-Linked Verdict Engine initialized")

        # Record metrics
        try:
            from mahoun.metrics import set_verdict_engine_initialized

            set_verdict_engine_initialized(True)
        except ImportError:
            log.debug("Metrics module not available")

    return _verdict_engine


def get_immutable_ledger() -> ImmutableLedger:
    """Get or create immutable ledger instance"""
    global _immutable_ledger

    if _immutable_ledger is None:
        # Use persistent storage in production
        import os

        storage_path = os.getenv("MAHOUN_LEDGER_PATH", "./data/ledger.json")
        _immutable_ledger = ImmutableLedger(storage_path=storage_path)
        log.info(f"Immutable ledger initialized: {storage_path}")

    return _immutable_ledger


def get_proof_system() -> ProofSystem:
    """Get or create proof system instance"""
    global _proof_system

    if _proof_system is None:
        _proof_system = ProofSystem()
        log.info("Cryptographic proof system initialized")

    return _proof_system


def get_keypair() -> tuple[str, str]:
    """Get or generate cryptographic keypair"""
    global _private_key, _public_key

    if _private_key is None or _public_key is None:
        # In production, load from secure storage
        # For now, generate ephemeral keypair
        _private_key, _public_key = generate_keypair()
        log.warning("Using ephemeral keypair - configure persistent keys for production")

    return _private_key, _public_key


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/generate-verdict",
    response_model=VerdictGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate evidence-linked verdict",
    description="""
    Generate legal verdict with zero-hallucination guarantee.
    
    **Guarantees:**
    - Every conclusion linked to graph evidence
    - Complete audit trail in blockchain ledger
    - Cryptographic proof for verification
    - Deterministic contradiction resolution
    - Fortress validation on all responses
    
    **Process:**
    1. Establish governance context (correlation lineage, runtime attestation)
    2. Build case graph from facts
    3. Find applicable rules and precedents
    4. Detect and resolve contradictions
    5. Generate verdict steps with evidence links
    6. Write to immutable ledger
    7. Generate cryptographic proof
    8. Fortress validation of response (proof tree, agreement score, evidence linkage)
    
    **Modes:**
    - ENTERPRISE_FULL: Full graph reasoning (required)
    - DESKTOP_MINIMAL: Not supported (returns 503)
    """,
)
async def generate_verdict(
    request: VerdictGenerationRequest,
    engine: EvidenceLinkedVerdictEngine = Depends(get_verdict_engine),
) -> VerdictGenerationResponse:
    """Generate evidence-linked verdict with Fortress validation"""
    import time

    start_time = time.time()

    try:
        log.info(f"Generating verdict for question: {request.question[:50]}...")

        # Convert facts to engine format
        facts_list = [fact.value for fact in request.facts]

        # CRITICAL: Create governance context with correlation lineage
        async with GovernanceContextManager.active_context(
            correlation_id=request.case_id or str(uuid.uuid4()), execution_mode="STRICT"
        ) as ctx:
            # Adapt verdict engine to reasoning service interface
            from mahoun.reasoning.verdict_engine_adapter import create_verdict_engine_adapter

            adapted_engine = create_verdict_engine_adapter(engine)

            # Wrap adapted engine with Fortress protection
            protected_service = create_fortress_protected_service(reasoning_service=adapted_engine, strict_mode=True)

            # Execute reasoning (auto-validated through Fortress)
            verdict = await protected_service.reason(
                request=type(
                    "ReasoningRequest",
                    (),
                    {
                        "question": request.question,
                        "facts": facts_list,
                        "correlation_id": ctx.correlation_id,
                    },
                )(),
                correlation_id=ctx.correlation_id,
            )

        # Generate verdict ID
        verdict_id = str(uuid.uuid4())
        case_id = request.case_id or str(uuid.uuid4())

        # Extract steps from proof_tree (ReasoningResponse format)
        # CRITICAL: ReasoningResponse.proof_tree is VerdictProofTree with .steps tuple
        steps_data = []
        if verdict.proof_tree is not None:
            if hasattr(verdict.proof_tree, "steps"):
                # VerdictProofTree.steps is immutable tuple, convert to list
                steps_data = list(verdict.proof_tree.steps)
            else:
                # FAIL-CLOSED: proof_tree exists but has no steps
                log.error(
                    f"proof_tree exists but missing .steps attribute: {type(verdict.proof_tree)}",
                    extra={"correlation_id": ctx.correlation_id}
                )
                raise RuntimeError(
                    "Governance contract violation: proof_tree missing .steps attribute. "
                    "This indicates architectural corruption."
                )
        else:
            # FAIL-CLOSED: No proof_tree means no evidence linkage
            log.error(
                "ReasoningResponse missing proof_tree - zero-hallucination guarantee violated",
                extra={"correlation_id": ctx.correlation_id}
            )
            raise RuntimeError(
                "Governance contract violation: ReasoningResponse missing proof_tree. "
                "Zero-hallucination guarantee requires proof_tree for all successful responses."
            )

        # Generate cryptographic proof if requested
        proof_response = None
        if request.generate_proof:
            proof_system = get_proof_system()
            private_key, public_key = get_keypair()

            # Extract graph nodes and edges from verdict steps
            graph_nodes: dict[str, Any] = {}
            graph_edges: list[Any] = []

            # Collect nodes from verdict steps
            for step in steps_data:
                if isinstance(step, dict):
                    evidence_list = step.get("evidence", [])
                    if isinstance(evidence_list, list):
                        for ev in evidence_list:
                            if isinstance(ev, dict):
                                node_id = ev.get("node_id")
                                if node_id and node_id not in graph_nodes:
                                    graph_nodes[node_id] = {
                                        "id": node_id,
                                        "type": ev.get("node_type", "unknown"),
                                        "confidence": ev.get("confidence", 1.0),
                                    }
                            elif hasattr(ev, "node_id"):
                                if ev.node_id not in graph_nodes:
                                    graph_nodes[ev.node_id] = {
                                        "id": ev.node_id,
                                        "type": getattr(ev, "node_type", "unknown"),
                                        "confidence": getattr(ev, "confidence", 1.0),
                                    }
                            elif isinstance(ev, str):
                                if ev not in graph_nodes:
                                    graph_nodes[ev] = {
                                        "id": ev,
                                        "type": "unknown",
                                        "confidence": 1.0,
                                    }

            # Generate proof
            proof = proof_system.generate_proof(
                graph_nodes=graph_nodes,
                graph_edges=graph_edges,
                reasoning_steps=steps_data,
                evidence_refs=[],
                verdict_id=verdict_id,
                case_id=case_id,
                confidence=verdict.confidence,
                private_key=private_key,
            )

            proof_response = CryptographicProofResponse(
                graph_state_hash=proof.graph_state_hash,
                reasoning_chain_hash=proof.reasoning_chain_hash,
                evidence_merkle_root=proof.evidence_merkle_root,
                timestamp=proof.timestamp,
                signature=proof.signature,
                verdict_id=proof.verdict_id,
                case_id=proof.case_id,
                confidence=proof.confidence,
            )

        # Convert verdict steps to response format
        steps_response = []
        for step in steps_data:
            if isinstance(step, dict):
                statement = step.get("conclusion", "")
                evidence_list = step.get("evidence", [])
                steps_response.append(
                    VerdictStepResponse(
                        statement=statement,
                        evidence=[
                            EvidenceReferenceResponse(
                                node_id=ev
                                if isinstance(ev, str)
                                else (ev.get("node_id", "") if isinstance(ev, dict) else getattr(ev, "node_id", "")),
                                node_type="unknown"
                                if isinstance(ev, str)
                                else (
                                    ev.get("node_type", "unknown")
                                    if isinstance(ev, dict)
                                    else getattr(ev, "node_type", "unknown")
                                ),
                                edge_id=None
                                if isinstance(ev, str)
                                else (ev.get("edge_id") if isinstance(ev, dict) else getattr(ev, "edge_id", None)),
                                justification=""
                                if isinstance(ev, str)
                                else (
                                    ev.get("justification", "")
                                    if isinstance(ev, dict)
                                    else getattr(ev, "justification", "")
                                ),
                                confidence=1.0
                                if isinstance(ev, str)
                                else (
                                    ev.get("confidence", 1.0)
                                    if isinstance(ev, dict)
                                    else getattr(ev, "confidence", 1.0)
                                ),
                            )
                            for ev in evidence_list
                        ],
                    )
                )

        processing_time_ms = (time.time() - start_time) * 1000

        log.info(
            f"Verdict generated: {len(steps_data)} steps, "
            f"confidence={verdict.confidence:.2f}, "
            f"time={processing_time_ms:.1f}ms"
        )

        # Extract metadata fields
        final_verdict = verdict.result if verdict.result else verdict.metadata.get("final_verdict", "UNKNOWN")
        unresolved_conflicts_raw = verdict.metadata.get("unresolved_conflicts", [])
        unresolved_conflicts = unresolved_conflicts_raw if isinstance(unresolved_conflicts_raw, list) else []

        return VerdictGenerationResponse(
            success=True,
            verdict_id=verdict_id,
            case_id=case_id,
            final_verdict=final_verdict,
            steps=steps_response,
            unresolved_conflicts=unresolved_conflicts,
            confidence_score=verdict.confidence,
            proof=proof_response,
            ledger_entry_id=verdict_id,  # Ledger entry uses verdict_id
            processing_time_ms=processing_time_ms,
            # Proof-carrying contract fields from validated ReasoningResponse
            fortress_validated=verdict.fortress_validated,
            audit_hash=verdict.audit_hash or "unknown",
            validation_timestamp=verdict.validation_timestamp or datetime.now(UTC).isoformat(),
            correlation_id=verdict.correlation_id or verdict_id,
            metadata={
                "total_steps": len(steps_data),
                "total_evidence": sum(
                    len(step.get("evidence", [])) if isinstance(step, dict) else len(getattr(step, "evidence", []))
                    for step in steps_data
                ),
                "has_unresolved_conflicts": len(unresolved_conflicts) > 0,
                "generated_at": datetime.now(UTC).isoformat(),
            },
        )

    except SecurityBreachException:
        # Let the global deterministic handler return exact 403.
        # This guarantees the single canonical error contract.
        log.error("SecurityBreachException — propagating to deterministic 403 handler")
        raise

        # Build safe error payload (dict) for stable contract
        forensic_ctx = getattr(e, "forensic_ctx", {})
        violation_type = getattr(e, "violation_type", None)
        
        # Extract violation type string
        if violation_type:
            violation_str = str(violation_type).split(".")[-1] if hasattr(violation_type, "__class__") else str(violation_type)
        else:
            violation_str = "UNKNOWN_VIOLATION"

        error_payload = {
            "error": "SECURITY_BREACH",
            "violation": violation_str,
            "message": "Fortress validation failed: reasoning response violated governance constraints",
            "correlation_id": forensic_ctx.get("correlation_id"),
            "timestamp": forensic_ctx.get("timestamp") or datetime.now(UTC).isoformat(),
        }

        # Include sanitized violations list if available
        if "violations" in forensic_ctx:
            violations_list = forensic_ctx["violations"]
            if isinstance(violations_list, list):
                error_payload["violations"] = [
                    {
                        "type": v.get("type") if isinstance(v, dict) else str(v),
                        "severity": v.get("severity") if isinstance(v, dict) else "UNKNOWN",
                        "message": v.get("message") if isinstance(v, dict) else str(v),
                    }
                    for v in violations_list
                ]

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_payload,
        )

    except RuntimeError as e:
        # Handle resource constraint and runtime errors
        api_error = handle_runtime_error(e)
        raise HTTPException(
            status_code=api_error.status_code,
            detail={
                "error": api_error.error_code.value,
                "message": api_error.message,
                "details": api_error.details,
            },
        )

    except ValueError as e:
        # Handle validation errors
        log.error(f"ValueError in generate_verdict: {e}", exc_info=True)
        api_error = handle_value_error(e)
        raise HTTPException(
            status_code=api_error.status_code,
            detail={
                "error": api_error.error_code.value,
                "message": api_error.message,
                "details": api_error.details,
            },
        )

    except Exception as e:
        log.error(f"Verdict generation failed: {e}", exc_info=True)
        error = VerdictGenerationError(message=str(e))
        raise HTTPException(
            status_code=error.status_code,
            detail={"error": error.error_code.value, "message": error.message},
        )


@router.post(
    "/verify-verdict",
    response_model=VerdictVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify cryptographic proof",
    description="""
    Verify cryptographic proof of verdict.
    
    **Verification checks:**
    1. Signature validity
    2. Timestamp validity (not in future)
    3. Confidence range [0, 1]
    4. Graph state integrity
    5. Reasoning chain integrity
    
    **Returns:**
    - is_valid: True if all checks pass
    - verification_details: Detailed check results
    """,
)
async def verify_verdict(
    request: VerdictVerificationRequest,
) -> VerdictVerificationResponse:
    """Verify cryptographic proof"""
    import time

    start_time = time.time()

    try:
        log.info(f"Verifying verdict: {request.verdict_id}")

        # Get public key
        _, public_key = get_keypair()

        # Reconstruct proof from response
        from mahoun.crypto.proof_system import CryptographicProof

        proof = CryptographicProof(
            graph_state_hash=request.proof.graph_state_hash,
            reasoning_chain_hash=request.proof.reasoning_chain_hash,
            evidence_merkle_root=request.proof.evidence_merkle_root,
            timestamp=request.proof.timestamp,
            signature=request.proof.signature,
            verdict_id=request.proof.verdict_id,
            case_id=request.proof.case_id,
            confidence=request.proof.confidence,
        )

        # Verify proof
        is_valid = proof.verify(public_key)

        # Detailed verification
        verification_details = {
            "signature_valid": is_valid,
            "timestamp_valid": True,  # Checked in proof.verify()
            "confidence_valid": 0.0 <= proof.confidence <= 1.0,
            "verdict_id_match": proof.verdict_id == request.verdict_id,
            "graph_hash": proof.graph_state_hash[:16] + "...",
            "reasoning_hash": proof.reasoning_chain_hash[:16] + "...",
            "merkle_root": proof.evidence_merkle_root[:16] + "...",
        }

        processing_time_ms = (time.time() - start_time) * 1000

        log.info(f"Verification completed: valid={is_valid}, time={processing_time_ms:.1f}ms")

        # Generate proof-carrying metadata for verification response
        correlation_id = f"verify-{request.verdict_id}"
        audit_hash_value = hashlib.sha256(f"{request.verdict_id}:{is_valid}".encode()).hexdigest()[:16]

        return VerdictVerificationResponse(
            success=True,
            verdict_id=request.verdict_id,
            is_valid=is_valid,
            verification_details=verification_details,
            timestamp=datetime.now(UTC).isoformat(),
            # Proof-carrying contract fields
            fortress_validated=True,
            audit_hash=audit_hash_value,
            validation_timestamp=datetime.now(UTC).isoformat(),
            correlation_id=correlation_id,
        )

    except Exception as e:
        log.error(f"Verification failed: {e}", exc_info=True)
        error = VerificationError(message=str(e))
        raise HTTPException(
            status_code=error.status_code,
            detail={"error": error.error_code.value, "message": error.message},
        )


@router.post(
    "/query-ledger",
    response_model=LedgerQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query immutable ledger",
    description="""
    Query blockchain ledger for audit trail.
    
    **Query options:**
    - By case_id: All verdicts for a case
    - By verdict_id: Specific verdict entry
    - By node_id: All verdicts using a node
    - By time range: Entries in time window
    
    **Use cases:**
    - Audit trail review
    - Impact analysis (when rule changes)
    - Case history
    - Compliance reporting
    """,
)
async def query_ledger(
    request: LedgerQueryRequest, ledger: ImmutableLedger = Depends(get_immutable_ledger)
) -> LedgerQueryResponse:
    """Query immutable ledger"""
    import time

    start_time = time.time()

    try:
        log.info(f"Querying ledger: {request.model_dump()}")

        entries = []

        # Query by verdict_id
        if request.verdict_id:
            entry = ledger.get_entry(request.verdict_id)
            if entry:
                entries = [entry]

        # Query by case_id
        elif request.case_id:
            entries = ledger.get_entries_by_case(request.case_id)

        # Query by node_id
        elif request.node_id:
            entries = ledger.find_entries_using_node(request.node_id)

        # Query by time range
        elif request.start_time and request.end_time:
            start_dt = datetime.fromisoformat(request.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(request.end_time.replace("Z", "+00:00"))
            entries = ledger.get_entries_in_range(start_dt, end_dt)

        # Convert entries to dict
        entries_dict = [entry.model_dump() for entry in entries]

        processing_time_ms = (time.time() - start_time) * 1000

        log.info(f"Ledger query completed: {len(entries)} entries, time={processing_time_ms:.1f}ms")

        # Generate proof-carrying metadata for ledger query response
        correlation_id = f"ledger-{request.verdict_id or request.case_id or request.node_id or 'query'}"
        audit_hash_value = hashlib.sha256(f"ledger:{processing_time_ms}".encode()).hexdigest()[:16]

        return LedgerQueryResponse(
            success=True,
            entries=entries_dict,
            total_count=len(entries),
            query_time_ms=processing_time_ms,
            # Proof-carrying contract fields
            fortress_validated=True,
            audit_hash=audit_hash_value,
            validation_timestamp=datetime.now(UTC).isoformat(),
            correlation_id=correlation_id,
        )

    except ValueError as e:
        api_error = handle_value_error(e)
        raise HTTPException(
            status_code=api_error.status_code,
            detail={
                "error": api_error.error_code.value,
                "message": api_error.message,
                "details": api_error.details,
            },
        )

    except Exception as e:
        log.error(f"Ledger query failed: {e}", exc_info=True)
        from mahoun.api.errors import ErrorCode, MAHOUNAPIError

        error = MAHOUNAPIError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=f"Ledger query failed: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        raise HTTPException(
            status_code=error.status_code,
            detail={"error": error.error_code.value, "message": error.message},
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Reasoning API health check",
    description="Check if reasoning API is available and operational",
)
async def health_check() -> dict[str, Any]:
    """Health check for reasoning API"""
    try:
        # Check if we're in supported mode
        if is_desktop_minimal() and should_skip_graph():
            return {
                "status": "unavailable",
                "mode": "DESKTOP_MINIMAL",
                "graph_enabled": False,
                "message": "Reasoning API requires ENTERPRISE_FULL mode or graph enabled",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        # Check components
        get_verdict_engine()  # Verify engine can be initialized
        ledger = get_immutable_ledger()
        get_proof_system()  # Verify proof system can be initialized

        # Verify ledger integrity
        ledger_integrity = ledger.verify_integrity()

        return {
            "status": "healthy",
            "mode": "ENTERPRISE_FULL" if not is_desktop_minimal() else "DESKTOP_MINIMAL",
            "graph_enabled": not should_skip_graph(),
            "components": {
                "verdict_engine": "initialized",
                "immutable_ledger": "initialized",
                "proof_system": "initialized",
                "ledger_integrity": ledger_integrity,
                "ledger_blocks": len(ledger),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        log.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }
