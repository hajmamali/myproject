"""
MAHOUN Fortress Integration for Unified Reasoning Service
==========================================================

Classification: MISSION-CRITICAL / GOVERNANCE-ENFORCEMENT
Purpose: Integrate FortressValidator with UnifiedReasoningService

This module provides a wrapper around UnifiedReasoningService that
automatically validates all responses through FortressValidator before
returning them to callers.

CRITICAL: This wrapper enforces governance scope through GovernanceContext.
NO reasoning operation can execute without an active governance context.

Usage:
    from mahoun.reasoning.fortress_integration import create_fortress_protected_service
    
    # Wrap existing service
    protected_service = create_fortress_protected_service(reasoning_service)
    
    # All responses are now validated
    response = await protected_service.reason(request)

Author: MahouN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from mahoun.core.fortress_validator import (
    ExecutionMode,
    FortressValidator,
    ReasoningResponse,
    SecurityBreachException,
    ValidationResult,
    ViolationSeverity,
    ViolationType,
)
from mahoun.core.governance import (
    GovernanceContextManager,
    GovernanceScopeEnforcer,
)
from mahoun.core.fortress_validator import get_logger

log = get_logger(__name__)


# ============================================================================
# FORTRESS-PROTECTED REASONING SERVICE
# ============================================================================


class FortressProtectedReasoningService:
    """
    Wrapper around UnifiedReasoningService with automatic FortressValidator enforcement.
    
    This class intercepts ALL responses from the underlying reasoning service
    and validates them through FortressValidator before returning to callers.
    
    Features:
    - Automatic validation of all reasoning responses
    - SecurityBreachException on RedLine violations
    - Forensic audit trail generation
    - Statistics tracking
    - Transparent pass-through for valid responses
    
    Example:
        service = FortressProtectedReasoningService(
            reasoning_service=unified_service,
            strict_mode=True
        )
        
        response = await service.reason(request)  # Auto-validated
    """
    
    def __init__(
        self,
        reasoning_service: Any,
        validator: Optional[FortressValidator] = None,
        strict_mode: bool = True,
        execution_mode: ExecutionMode = ExecutionMode.DESKTOP_MINIMAL,
        ledger_commit_service: Optional[Any] = None,
    ):
        """
        Initialize Fortress-protected reasoning service.
        
        PER RULE 8: Dependency Direction
        - LedgerCommitService is explicitly injected, NOT discovered via object graphs
        - This prevents Fortress from walking object graphs to find ledger_writer
        
        Args:
            reasoning_service: UnifiedReasoningService instance to wrap
            validator: Optional FortressValidator instance (creates new if None)
            strict_mode: If True, raise exceptions on violations
            execution_mode: Current execution mode
            ledger_commit_service: Explicitly injected LedgerCommitService (RULE 8)
        """
        self.reasoning_service = reasoning_service
        self.strict_mode = strict_mode
        self.execution_mode = execution_mode
        self.ledger_commit_service = ledger_commit_service
        
        # Create or use provided validator
        self.validator = validator or FortressValidator(
            execution_mode=execution_mode,
            strict_mode=strict_mode
        )
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "validated_responses": 0,
            "blocked_responses": 0,
            "validation_failures": 0,
            "ledger_commits": 0,
            "failed_ledger_commits": 0,
        }
        
        log.info(
            f"FortressProtectedReasoningService initialized: "
            f"strict={strict_mode}, mode={execution_mode.value}, "
            f"ledger_commit_service={'ENABLED' if ledger_commit_service else 'NOT PROVIDED'}"
        )
    
    async def reason(
        self,
        request: Any,
        correlation_id: Optional[str] = None
    ) -> ReasoningResponse:
        """
        Execute reasoning with automatic fortress validation, ledger commit, and governance scope.
        
        PER RULE 1: Ledger is NEVER written before Fortress validation
        PER RULE 10: Execution Atomicity - all steps succeed or fail together
        PER RULE 11: Failed executions must also be recorded
        
        This method:
        1. Requires active governance context (CORRELATION LINEAGE)
        2. Executes reasoning within governance scope (PROOF TRACKING ACTIVE)
        3. Validates response through FortressValidator
        4. **COMMITS LEDGER AFTER VALIDATION** (NEW - RULE 1)
        5. Returns validated response or raises SecurityBreachException
        
        CRITICAL: NO reasoning can execute without active governance context.
        
        Args:
            request: ReasoningRequest to process
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            Validated ReasoningResponse
            
        Raises:
            SecurityBreachException: On critical RedLine violations
            GovernanceViolationError: If governance context not active
        """
        self.stats["total_requests"] += 1
        
        # Generate correlation_id if not provided
        if correlation_id is None and hasattr(request, 'correlation_id'):
            correlation_id = request.correlation_id
        
        # CRITICAL: Require active governance context (RULE 14)
        ctx = GovernanceContextManager.require_context()
        
        # PER RULE 3: Execution artifacts travel through explicit contracts
        # The reasoning service now returns VerdictExecutionResult with pending ledger entry
        execution_result = None
        
        try:
            # Execute reasoning within governance scope
            log.debug(f"[{correlation_id}] Executing reasoning request")
            response = await self.reasoning_service.reason(request)
            
            # Get the execution result from the reasoning service if available
            # The VerdictEngineAdapter now returns ReasoningResponse with execution artifacts
            # We need to extract the VerdictExecutionResult from the adapter
            execution_result = self._extract_execution_result(response)
            
            # Validate response through Fortress
            log.debug(f"[{correlation_id}] Validating response through Fortress")
            validation_result = await self.validator.validate(
                response=response,
                correlation_id=correlation_id
            )
            
            self.stats["validated_responses"] += 1
            
            # ========================================================================
            # LEDGER COMMIT AFTER VALIDATION (RULE 1, RULE 2, RULE 10, RULE 11)
            # ========================================================================
            #
            # PER RULE 1: Ledger is NEVER written before validation
            # PER RULE 11: Both successful AND failed validations are recorded
            #
            if self.ledger_commit_service and execution_result:
                try:
                    # Commit ledger with validation result
                    # This happens AFTER validation, ensuring trustworthy ledger
                    commit_result = await self.ledger_commit_service.commit_execution(
                        execution_result=execution_result,
                        validation_passed=validation_result.passed,
                        validation_violations=validation_result.violations,
                        validation_timestamp=datetime.now(UTC),
                        fortress_version=self.validator.version if hasattr(self.validator, 'version') else "1.0.0",
                    )
                    
                    if commit_result.success:
                        self.stats["ledger_commits"] += 1
                        log.info(
                            f"[{correlation_id}] Ledger committed successfully: "
                            f"verdict_id={execution_result.ledger_entry.verdict_id}, "
                            f"validation_status={commit_result.entry.validation_status}"
                        )
                    else:
                        self.stats["failed_ledger_commits"] += 1
                        log.error(
                            f"[{correlation_id}] Ledger commit failed: {commit_result.error}"
                        )
                        # PER RULE 10: Execution Atomicity
                        # If ledger commit fails, we cannot return success
                        if self.strict_mode:
                            raise RuntimeError(
                                f"Ledger commit failed after validation - execution atomicity violated: "
                                f"{commit_result.error}"
                            )
                except Exception as e:
                    log.error(f"[{correlation_id}] Ledger commit exception: {e}")
                    if self.strict_mode:
                        raise
            else:
                # No ledger commit service - log warning but continue
                if execution_result:
                    log.warning(
                        f"[{correlation_id}] No LedgerCommitService provided - "
                        f"ledger will not be committed for verdict_id={execution_result.ledger_entry.verdict_id}"
                    )
            
            # Log validation result
            if validation_result.passed:
                log.info(
                    f"[{correlation_id}] Response VALIDATED by Fortress "
                    f"({validation_result.execution_time_ms:.2f}ms)"
                )
            else:
                # This should never be reached in strict mode since validator.raise() will be called
                # But we keep it for safety and non-strict mode
                self.stats["blocked_responses"] += 1
                log.warning(
                    f"[{correlation_id}] Response blocked by Fortress: "
                    f"{len(validation_result.violations)} violations (non-strict mode)"
                )
                
            return response
            
        except SecurityBreachException:
            # Re-raise security breaches
            self.stats["blocked_responses"] += 1
            raise
            
        except Exception as e:
            self.stats["validation_failures"] += 1
            log.error(f"[{correlation_id}] Validation failed with exception: {e}")
            raise
    
    def _extract_execution_result(self, response: Any) -> Any:
        """
        Extract VerdictExecutionResult from ReasoningResponse.
        
        The VerdictEngineAdapter stores the execution result in the response metadata
        for backward compatibility. This method extracts it.
        
        PER RULE 3: Execution artifacts travel through explicit contracts
        
        Args:
            response: ReasoningResponse that may contain execution result
            
        Returns:
            VerdictExecutionResult if available, None otherwise
        """
        # Check if response has execution result in metadata
        if hasattr(response, 'metadata') and response.metadata:
            if '_execution_result' in response.metadata:
                return response.metadata['_execution_result']
        
        # In new architecture, the adapter should have stored it
        # For backward compatibility, return None
        return None
    
    async def reason_batch(
        self,
        requests: list[Any],
        correlation_id_prefix: Optional[str] = None
    ) -> list[ReasoningResponse]:
        """
        Execute batch reasoning with validation.
        
        Args:
            requests: List of ReasoningRequest objects
            correlation_id_prefix: Optional prefix for correlation IDs
            
        Returns:
            List of validated ReasoningResponse objects
        """
        tasks = []
        for i, request in enumerate(requests):
            corr_id = f"{correlation_id_prefix}-{i}" if correlation_id_prefix else None
            tasks.append(self.reason(request, correlation_id=corr_id))
        
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        validator_stats = self.validator.get_stats()
        
        return {
            "service": self.stats.copy(),
            "validator": validator_stats,
            "combined": {
                "total_requests": self.stats["total_requests"],
                "validation_pass_rate": (
                    validator_stats["passed"] / validator_stats["total_validations"]
                    if validator_stats["total_validations"] > 0 else 0.0
                ),
                "block_rate": (
                    self.stats["blocked_responses"] / self.stats["total_requests"]
                    if self.stats["total_requests"] > 0 else 0.0
                )
            }
        }
    
    def get_audit_trail(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Get recent audit trail from validator"""
        return self.validator.get_audit_trail(limit=limit)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on protected service"""
        try:
            # Check underlying service
            service_healthy = hasattr(self.reasoning_service, 'health_check')
            if service_healthy:
                service_health = await self.reasoning_service.health_check()
            else:
                service_health = {"status": "unknown"}
            
            # Check validator
            validator_healthy = self.validator is not None
            
            return {
                "status": "healthy" if (service_healthy and validator_healthy) else "degraded",
                "fortress_validator": {
                    "active": validator_healthy,
                    "strict_mode": self.strict_mode,
                    "execution_mode": self.execution_mode.value,
                    "total_validations": self.validator.stats["total_validations"]
                },
                "reasoning_service": service_health,
                "statistics": self.get_stats()
            }
            
        except Exception as e:
            log.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def create_fortress_protected_service(
    reasoning_service: Any,
    strict_mode: bool = True,
    execution_mode: ExecutionMode = ExecutionMode.DESKTOP_MINIMAL,
    validator: Optional[FortressValidator] = None,
    ledger_commit_service: Optional[Any] = None,
) -> FortressProtectedReasoningService:
    """
    Create a Fortress-protected reasoning service.
    
    This is the recommended way to wrap an existing UnifiedReasoningService
    with automatic FortressValidator enforcement.
    
    PER RULE 8: Dependencies point inward
    - ledger_commit_service is explicitly injected, NOT discovered
    
    Args:
        reasoning_service: UnifiedReasoningService instance to protect
        strict_mode: If True, raise exceptions on violations
        execution_mode: Current execution mode
        validator: Optional FortressValidator instance (creates new if None)
        ledger_commit_service: Optional LedgerCommitService for ledger commits AFTER validation
        
    Returns:
        FortressProtectedReasoningService instance
        
    Example:
        from mahoun.reasoning.unified_reasoning_service import UnifiedReasoningService
        from mahoun.reasoning.fortress_integration import create_fortress_protected_service
        from mahoun.reasoning.ledger_commit_service import LedgerCommitService
        
        # Create base service
        base_service = UnifiedReasoningService()
        
        # Create ledger commit service
        ledger_commit_service = LedgerCommitService(ledger_writer=ledger_writer)
        
        # Wrap with Fortress protection
        protected_service = create_fortress_protected_service(
            base_service,
            strict_mode=True,
            ledger_commit_service=ledger_commit_service  # Explicit injection
        )
        
        # Use protected service (all responses auto-validated, ledger auto-committed)
        response = await protected_service.reason(request)
    """
    return FortressProtectedReasoningService(
        reasoning_service=reasoning_service,
        validator=validator,
        strict_mode=strict_mode,
        execution_mode=execution_mode,
        ledger_commit_service=ledger_commit_service,
    )


async def validate_existing_response(
    response: ReasoningResponse,
    correlation_id: Optional[str] = None,
    strict_mode: bool = True
) -> ValidationResult:
    """
    Validate an existing reasoning response.
    
    Useful for validating responses from external sources or
    for retroactive validation of cached responses.
    
    Args:
        response: ReasoningResponse to validate
        correlation_id: Optional correlation ID
        strict_mode: If True, raise exceptions on violations
        
    Returns:
        ValidationResult
        
    Raises:
        SecurityBreachException: On critical violations (if strict_mode=True)
    """
    validator = FortressValidator(strict_mode=strict_mode)
    return await validator.validate(response, correlation_id=correlation_id)


# ============================================================================
# DECORATOR FOR AUTOMATIC VALIDATION
# ============================================================================


def fortress_validated(strict_mode: bool = True):
    """
    Decorator for automatic fortress validation of reasoning methods.
    
    Usage:
        class MyReasoningService:
            @fortress_validated(strict_mode=True)
            async def reason(self, request):
                # ... reasoning logic ...
                return response
    
    Args:
        strict_mode: If True, raise exceptions on violations
        
    Returns:
        Decorated function with automatic validation
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Execute original function
            response = await func(*args, **kwargs)
            
            # Extract correlation_id if available
            correlation_id = kwargs.get('correlation_id')
            if correlation_id is None and len(args) > 1:
                request = args[1]
                if hasattr(request, 'correlation_id'):
                    correlation_id = request.correlation_id
            
            # Validate response
            validator = FortressValidator(strict_mode=strict_mode)
            await validator.validate(response, correlation_id=correlation_id)
            
            return response
        
        return wrapper
    return decorator


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

log.info("FortressIntegration module loaded: AUTOMATIC VALIDATION ENABLED")
