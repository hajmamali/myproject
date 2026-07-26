"""
MAHOUN Governance Context
==========================

Classification: CRITICAL / RUNTIME GOVERNANCE / NON-BYPASSABLE
Purpose: Execution context that enforces governance scope for all reasoning operations

This module implements a governance context that MUST be active before ANY
reasoning operation can execute. It provides:

1. Execution context creation
2. Correlation lineage tracking
3. Proof tracking activation
4. Governance scope injection
5. Runtime attestation
6. Contradiction hooks activation
7. **CRITICAL**: Graph mutation enforcement - NO graph writes without active context

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from mahoun.core.fortress_validator import get_logger
from mahoun.core.governance.protocols import MetricsCollectorProtocol
from mahoun.core.governance.deterministic_resolver import DeterministicResolver
from mahoun.core.governance.ontology_enforcer import OntologyEnforcer
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata, ProvenanceTracker
from mahoun.core.governance.validator_pipeline import ValidatorPipeline
from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)

log = get_logger(__name__)


# ============================================================================
# GOVERNANCE CONTEXT
# ============================================================================


@dataclass
class GovernanceContext:
    """
    Execution context that enforces governance scope for all reasoning operations.

    CRITICAL INVARIANT: NO reasoning operation can execute without an active
    GovernanceContext. This is enforced by the GovernanceContextManager.

    Features:
    - Execution context creation with correlation lineage
    - Proof tracking activation
    - Governance scope injection
    - Runtime attestation
    - Contradiction hooks activation

    Usage:
        async with GovernanceContextManager.create_context() as ctx:
            # All reasoning operations in this scope are governed
            result = await reasoning_service.reason(request)
    """

    # Core context
    context_id: str
    correlation_id: str
    timestamp: str
    execution_mode: str

    # Governance components
    provenance_tracker: ProvenanceTracker
    validator_pipeline: ValidatorPipeline
    deterministic_resolver: DeterministicResolver
    ontology_enforcer: OntologyEnforcer

    # Optional actor identity for audit trail compatibility
    actor_id: str | None = None

    # Runtime state
    proof_tracking_active: bool = True
    contradiction_hooks_active: bool = True
    governance_scope_injected: bool = True

    # Attestation
    runtime_attestation: dict[str, Any] = field(default_factory=dict)

    # Lineage tracking
    correlation_lineage: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize runtime attestation and correlation lineage."""
        self.runtime_attestation = {
            "context_id": self.context_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "execution_mode": self.execution_mode,
            "actor_id": self.actor_id,
            "governance_components": {
                "provenance_tracker": True,
                "validator_pipeline": True,
                "deterministic_resolver": True,
                "ontology_enforcer": True,
            },
            "proof_tracking_active": self.proof_tracking_active,
            "contradiction_hooks_active": self.contradiction_hooks_active,
            "governance_scope_injected": self.governance_scope_injected,
        }

        # CRITICAL: Only initialize lineage if empty (preserve parent lineage)
        # If lineage was passed from parent, keep it. Otherwise, start new lineage.
        if not self.correlation_lineage:
            self.correlation_lineage = [self.correlation_id]

    def require_active_context(self) -> None:
        """
        CRITICAL: Require active governance context for graph operations.

        This is the FINAL gate before any graph mutation.
        If governance context is not active, raise GovernanceViolationError.

        Usage:
            ctx = GovernanceContextManager.require_context()
            ctx.require_active_context()  # Fail-closed if not active
        """
        if not self.governance_scope_injected:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.GOVERNANCE_BYPASS,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        "GRAPH MUTATION BLOCKED: Governance scope not active. "
                        "All graph writes require active governance context. "
                        "Use GovernanceContextManager.active_context() to establish scope."
                    ),
                    details={
                        "context_id": self.context_id,
                        "correlation_id": self.correlation_id,
                        "governance_scope_injected": self.governance_scope_injected,
                    },
                    source="GovernanceContext",
                    correlation_id=self.correlation_id,
                )
            )

    def create_child_context(self, child_correlation_id: str | None = None) -> GovernanceContext:
        """
        Create a child context with inherited governance scope.

        Args:
            child_correlation_id: Optional child correlation ID

        Returns:
            New GovernanceContext with parent lineage
        """
        child_id = child_correlation_id or f"{self.correlation_id}-{uuid.uuid4().hex[:8]}"

        return GovernanceContext(
            context_id=f"{self.context_id}-child-{uuid.uuid4().hex[:8]}",
            correlation_id=child_id,
            timestamp=datetime.now(UTC).isoformat(),
            execution_mode=self.execution_mode,
            actor_id=self.actor_id,
            provenance_tracker=self.provenance_tracker,
            validator_pipeline=self.validator_pipeline,
            deterministic_resolver=self.deterministic_resolver,
            ontology_enforcer=self.ontology_enforcer,
            proof_tracking_active=self.proof_tracking_active,
            contradiction_hooks_active=self.contradiction_hooks_active,
            governance_scope_injected=self.governance_scope_injected,
            runtime_attestation=self.runtime_attestation.copy(),
            correlation_lineage=self.correlation_lineage + [child_id],
        )

    def get_attestation(self) -> dict[str, Any]:
        """Get runtime attestation for audit trail."""
        return {
            **self.runtime_attestation,
            "correlation_lineage": self.correlation_lineage,
            "attestation_timestamp": datetime.now(UTC).isoformat(),
        }

    def validate_governance_scope(self) -> bool:
        """
        Validate that governance scope is active.

        Returns:
            True if governance scope is active

        Raises:
            GovernanceViolationError: If governance scope is not active
        """
        if not self.governance_scope_injected:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.GOVERNANCE_BYPASS,
                    severity=ViolationSeverity.CRITICAL,
                    message="Governance scope not active - reasoning operations blocked",
                    details={
                        "context_id": self.context_id,
                        "correlation_id": self.correlation_id,
                        "governance_scope_injected": self.governance_scope_injected,
                    },
                    source="GovernanceContext",
                    correlation_id=self.correlation_id,
                )
            )

        return True


# ============================================================================
# GOVERNANCE CONTEXT MANAGER
# ============================================================================


class GovernanceContextManager:
    """
    Manager for governance context lifecycle.

    CRITICAL: This manager enforces that ALL reasoning operations
    execute within an active governance context.

    Usage:
        # Create a context
        ctx = GovernanceContextManager.create_context(
            correlation_id="req-123",
            execution_mode="STRICT"
        )

        # Use in reasoning operations
        async with ctx:
            result = await reasoning_service.reason(request)
    """

    # Replaced with contextvars for async-safe isolation (P0 GOVERNANCE CONTEXT ISOLATION)
    # We store a per-context list and replace it on push to keep tests/backward compatibility.
    _governance_stack: ContextVar[list[GovernanceContext] | None] = ContextVar(
        "mahoun_governance_stack", default=None
    )

    _default_instance: Optional['GovernanceContextManager'] = None

    @classmethod
    def configure(cls, metrics_collector: 'Optional[MetricsCollectorProtocol]') -> None:
        """
        Configure the global governance context manager instance.
        """
        cls._default_instance = cls(metrics_collector=metrics_collector)

    @classmethod
    def _get_instance(cls) -> 'GovernanceContextManager':
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    def __init__(self, metrics_collector: 'Optional[MetricsCollectorProtocol]' = None) -> None:
        """
        Initialize GovernanceContextManager.
        
        Args:
            metrics_collector: Injected metrics collector. Defaults to NoOpMetricsCollector.
        """
        from mahoun.core.governance.protocols import NoOpMetricsCollector
        self._metrics_collector = metrics_collector or NoOpMetricsCollector()

    @classmethod
    def _get_stack(cls) -> list[GovernanceContext]:
        """Return a mutable stack for the current async context."""
        stack = cls._governance_stack.get()
        if stack is None:
            stack = []
            cls._governance_stack.set(stack)
        return stack

    @classmethod
    def _reset_for_test(cls) -> None:
        """
        Test-only helper to reset governance context for the current async task.
        """
        cls._governance_stack.set(None)

    @classmethod
    def create_context(
        cls,
        correlation_id: str | None = None,
        execution_mode: str = "STRICT",
        actor_id: str | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> GovernanceContext:
        """
        Create a new governance context.

        Args:
            correlation_id: Optional correlation ID
            execution_mode: Execution mode (STRICT, AUDIT, etc.)
            actor_id: Optional actor identity for audit trail compatibility
            request_id: Optional request ID alias
            user_id: Optional user ID alias

        Returns:
            GovernanceContext instance
        """
        return cls._get_instance()._create_context(
            correlation_id=correlation_id or request_id,
            execution_mode=execution_mode,
            actor_id=actor_id or user_id,
            request_id=request_id,
            user_id=user_id,
            **kwargs,
        )

    def _create_context(
        self,
        correlation_id: str | None = None,
        execution_mode: str = "STRICT",
        actor_id: str | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> GovernanceContext:
        ctx_id = f"ctx-{uuid.uuid4().hex[:16]}"
        corr_id = correlation_id or f"req-{uuid.uuid4().hex[:16]}"

        # Initialize governance components
        provenance_tracker = ProvenanceTracker()
        validator_pipeline = ValidatorPipeline()
        deterministic_resolver = DeterministicResolver()
        ontology_enforcer = OntologyEnforcer()

        return GovernanceContext(
            context_id=ctx_id,
            correlation_id=corr_id,
            timestamp=datetime.now(UTC).isoformat(),
            execution_mode=execution_mode,
            actor_id=actor_id,
            provenance_tracker=provenance_tracker,
            validator_pipeline=validator_pipeline,
            deterministic_resolver=deterministic_resolver,
            ontology_enforcer=ontology_enforcer,
        )

    @classmethod
    @asynccontextmanager
    async def active_context(
        cls,
        correlation_id: str | None = None,
        execution_mode: str = "STRICT",
        actor_id: str | None = None,
    ) -> AsyncIterator[GovernanceContext]:
        """
        Async context manager for active governance context.

        This is the PRIMARY way to ensure governance context is active.

        Args:
            correlation_id: Optional correlation ID
            execution_mode: Execution mode
            actor_id: Optional actor identity for audit trail compatibility

        Yields:
            GovernanceContext instance

        Raises:
            GovernanceViolationError: If context cannot be established
        """
        async with cls._get_instance()._active_context(
            correlation_id=correlation_id,
            execution_mode=execution_mode,
            actor_id=actor_id,
        ) as ctx:
            yield ctx

    @asynccontextmanager
    async def _active_context(
        self,
        correlation_id: str | None = None,
        execution_mode: str = "STRICT",
        actor_id: str | None = None,
    ) -> AsyncIterator[GovernanceContext]:
        ctx = self._create_context(
            correlation_id=correlation_id,
            execution_mode=execution_mode,
            actor_id=actor_id,
        )

        try:
            # Validate governance scope
            ctx.validate_governance_scope()

            # Push to isolated context stack (mutable list for current async context)
            stack = self._get_stack()
            token = self._governance_stack.set([*stack, ctx])

            log.info(
                "GovernanceContext activated",
                extra={
                    "context_id": ctx.context_id,
                    "correlation_id": ctx.correlation_id,
                    "execution_mode": ctx.execution_mode,
                },
            )

            yield ctx

        finally:
            # Revert context using token (standard ContextVar practice)
            if 'token' in locals():
                self._governance_stack.reset(token)

            log.info(
                "GovernanceContext deactivated",
                extra={
                    "context_id": ctx.context_id,
                    "correlation_id": ctx.correlation_id,
                },
            )

    @classmethod
    def get_current_context(cls) -> GovernanceContext | None:
        """Get the current active governance context (isolated per async task)."""
        return cls._get_instance()._get_current_context()

    def _get_current_context(self) -> GovernanceContext | None:
        stack = self._get_stack()
        if stack:
            return stack[-1]
        return None

    @classmethod
    def require_context(cls) -> GovernanceContext:
        """
        Require an active governance context.

        Returns:
            Active GovernanceContext

        Raises:
            GovernanceViolationError: If no context is active
        """
        return cls._get_instance()._require_context()

    def _require_context(self) -> GovernanceContext:
        ctx = self._get_current_context()

        if ctx is None:
            try:
                self._metrics_collector.register_counter("mahoun_governance_missing_context_total").inc()
            except Exception:
                pass

            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.GOVERNANCE_BYPASS,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        "GRAPH MUTATION BLOCKED: No active governance context. "
                        "All graph writes require active governance context. "
                        "Use GovernanceContextManager.active_context() to establish scope."
                    ),
                    details={
                        "hint": "Use GovernanceContextManager.active_context()",
                    },
                    source="GovernanceContextManager",
                    correlation_id="unknown",
                )
            )

        # CRITICAL: Verify governance scope is active
        ctx.require_active_context()

        return ctx

    @classmethod
    def require_provenance(cls, source: str, author: str) -> ProvenanceMetadata:
        """
        Require provenance metadata for a graph operation.

        Args:
            source: Origin of the data
            author: Actor identifier

        Returns:
            ProvenanceMetadata instance with full governance attestation
        """
        return cls._get_instance()._require_provenance(source, author)

    def _require_provenance(self, source: str, author: str) -> ProvenanceMetadata:
        ctx = self._require_context()

        # CRITICAL: Extract governance scope and runtime attestation from active context
        # These are mandatory for cryptographic provenance integrity
        governance_scope_id = ctx.context_id  # Use context_id as governance scope
        runtime_attestation_id = ctx.runtime_attestation.get("context_id", ctx.context_id)

        return ProvenanceMetadata.create(
            source=source,
            correlation_id=ctx.correlation_id,
            author=author,
            governance_scope_id=governance_scope_id,
            runtime_attestation_id=runtime_attestation_id,
        )


# ============================================================================
# GOVERNANCE SCOPE ENFORCER
# ============================================================================


class GovernanceScopeEnforcer:
    """
    Enforces that all reasoning operations execute within governance scope.

    This is the FINAL gate before any reasoning operation executes.

    Usage:
        @GovernanceScopeEnforcer.enforce()
        async def my_reasoning_operation(request):
            # This will only execute if governance context is active
            ...
    """

    @staticmethod
    def enforce():
        """
        Decorator to enforce governance scope.

        Returns:
            Decorated function that requires governance context
        """

        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Require active governance context
                GovernanceContextManager.require_context()

                # Execute with governance scope
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def check_context():
        """
        Check if governance context is active.

        Returns:
            True if context is active

        Raises:
            GovernanceViolationError: If no context is active
        """
        return GovernanceContextManager.require_context()
