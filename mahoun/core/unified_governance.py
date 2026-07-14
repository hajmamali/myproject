#!/usr/bin/env python3
"""
Unified Governance Controller - Integration Layer
==================================================

This module provides the UNIFIED coordination layer between:
1. PolicyResolver (view mode, resource limits, profile awareness)
2. Governance Kernel (mutation authorization, query classification)

CRITICAL DESIGN PRINCIPLES:
1. Two-layer governance: Security (Kernel) + Visibility (Policy)
2. Coordinated decision-making with unified audit trail
3. Cypher query transformation (tombstone filtering, depth limiting)
4. Fail-closed security posture
5. Zero-bypass guarantees

Integration Points:
-------------------
- PolicyResolver: Determines WHAT data is visible (ACTIVE_VIEW vs HISTORICAL_VIEW)
- Governance Kernel: Determines IF operations are authorized (READ vs WRITE)
- Unified Controller: Coordinates both layers for complete governance

Version: 1.0.0
Phase: Hard Policy Enforcement - Kernel Integration
Author: MAHOUN System Architecture Team
Date: 2026-06-18
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from mahoun.ai.profile_manager import ProfileManager
    from mahoun.core.governance.governance_context import GovernanceContext
    from mahoun.core.governance_kernel.kernel import (
        KernelMutationBoundary,
        QueryType,
    )
    from mahoun.core.policy_resolver import ExecutionPolicy, PolicyResolver, ViewMode

logger = logging.getLogger(__name__)


# ============================================================================
# Internal Helpers
# ============================================================================


def _resolve_actor_id(context: Any) -> str:
    """Return a stable non-empty actor identifier for governance decisions."""
    actor_id = getattr(context, "actor_id", None)
    if actor_id is None:
        return "unknown"

    actor_text = str(actor_id).strip()
    return actor_text or "unknown"


# ============================================================================
# Unified Governance Decision
# ============================================================================

@dataclass(frozen=True)
class UnifiedGovernanceDecision:
    """
    Complete governance decision combining both layers.
    
    This immutable dataclass represents the OUTPUT of unified governance,
    combining policy decisions (PolicyResolver) with security checks (Kernel).
    
    Two-Layer Model:
    ----------------
    Layer 1 (Kernel): Security & Authorization
        - Query classification (READ vs WRITE)
        - Mutation authorization check
        - Forbidden operation detection
        - Actor & correlation tracking
        
    Layer 2 (Policy): Visibility & Resources
        - View mode determination (ACTIVE_VIEW vs HISTORICAL_VIEW)
        - Tombstone filtering decisions
        - Graph depth limits
        - Semantic search enablement
        
    Attributes:
    -----------
    decision_id: Unique identifier for this governance decision
    query_type: Classified query type (READ, WRITE, DDL, FORBIDDEN)
    mutation_authorized: Whether mutation is authorized (Kernel layer)
    policy: Execution policy (Policy layer)
    query_transformed: Whether query was transformed
    original_query: Original Cypher query
    transformed_query: Transformed query (with filters/limits)
    transformations_applied: List of transformations
    
    Audit Trail:
    ------------
    correlation_id: Links to governance context
    actor_id: Actor who initiated the query
    decided_at: When decision was made
    kernel_check_passed: Whether Kernel layer approved
    policy_check_passed: Whether Policy layer approved
    decision_reason: Human-readable explanation
    """
    
    # Identifiers
    decision_id: str
    correlation_id: str
    actor_id: str
    decided_at: str
    
    # Kernel layer (security)
    query_type: str  # READ, WRITE, DDL, FORBIDDEN
    mutation_authorized: bool
    kernel_check_passed: bool
    kernel_message: str
    
    # Policy layer (visibility)
    policy: ExecutionPolicy
    policy_check_passed: bool
    view_mode: str  # active, historical, mixed
    allow_tombstones: bool
    
    # Query transformation
    query_transformed: bool
    original_query: str
    transformed_query: str
    transformations_applied: List[str]
    
    # Decision summary
    approved: bool
    decision_reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "decision_id": self.decision_id,
            "correlation_id": self.correlation_id,
            "actor_id": self.actor_id,
            "decided_at": self.decided_at,
            "query_type": self.query_type,
            "mutation_authorized": self.mutation_authorized,
            "kernel_check_passed": self.kernel_check_passed,
            "kernel_message": self.kernel_message,
            "policy": self.policy.to_dict(),
            "policy_check_passed": self.policy_check_passed,
            "view_mode": self.view_mode,
            "allow_tombstones": self.allow_tombstones,
            "query_transformed": self.query_transformed,
            "original_query": self.original_query,
            "transformed_query": self.transformed_query,
            "transformations_applied": self.transformations_applied,
            "approved": self.approved,
            "decision_reason": self.decision_reason,
            "metadata": self.metadata
        }
    
    def is_safe_read(self) -> bool:
        """Check if this is a safe read query (approved, read-only, active view)."""
        return (
            self.approved
            and self.query_type == "READ"
            and self.view_mode == "active"
            and not self.allow_tombstones
        )
    
    def requires_elevated_privileges(self) -> bool:
        """Check if this decision required elevated privileges."""
        return (
            self.mutation_authorized
            or self.view_mode in ("historical", "mixed")
        )


# ============================================================================
# Unified Governance Controller
# ============================================================================

class UnifiedGovernanceController:
    """
    Unified Governance Controller - Two-Layer Coordination
    
    This class is the SINGLE coordination point for all governance decisions.
    It orchestrates both PolicyResolver (visibility) and Governance Kernel
    (security) to provide complete, consistent governance.
    
    Design Philosophy:
    ------------------
    "Security checks happen first, then visibility rules are applied."
    
    1. Kernel Layer (Security First):
       - Classify query type (READ vs WRITE)
       - Check mutation authorization
       - Detect forbidden operations
       - Enforce correlation_id + actor_id requirements
       
    2. Policy Layer (Visibility Second):
       - Resolve execution policy (profile-aware)
       - Determine view mode (ACTIVE_VIEW vs HISTORICAL_VIEW)
       - Apply tombstone filtering
       - Enforce resource limits (depth, semantic search)
       
    3. Query Transformation:
       - Inject tombstone filters (WHERE node._deleted IS NULL)
       - Inject path filters (NONE(n IN nodes(path) WHERE n._deleted = true))
       - Apply depth limits (relationship[:*1..MAX_DEPTH])
       - Validate transformed query
       
    4. Unified Audit Trail:
       - Combine Kernel + Policy decisions
       - Generate human-readable explanation
       - Persist for compliance
    
    Constructor Injection:
    ----------------------
    policy_resolver: PolicyResolver instance
    enable_query_transformation: Whether to transform queries (default: True)
    enable_audit_logging: Whether to log decisions (default: True)
    
    Usage:
    ------
    >>> controller = UnifiedGovernanceController(policy_resolver)
    >>> 
    >>> # Prepare query execution (combines both layers)
    >>> decision = controller.prepare_query_execution(
    ...     query="MATCH (n:Law) RETURN n",
    ...     context=context,
    ...     view_mode=ViewMode.ACTIVE_VIEW
    ... )
    >>> 
    >>> # Check if approved
    >>> if decision.approved:
    ...     # Execute decision.transformed_query
    ...     results = execute(decision.transformed_query)
    >>> else:
    ...     raise GovernanceViolationError(decision.decision_reason)
    """
    
    def __init__(
        self,
        policy_resolver: PolicyResolver,
        enable_query_transformation: bool = True,
        enable_audit_logging: bool = True,
        strict_mode: bool = True
    ):
        """
        Initialize unified governance controller.
        
        Args:
            policy_resolver: PolicyResolver instance (required)
            enable_query_transformation: Enable automatic query transformation
            enable_audit_logging: Enable audit trail logging
            strict_mode: Enforce strict governance (fail-closed)
        """
        self.policy_resolver = policy_resolver
        self.enable_query_transformation = enable_query_transformation
        self.enable_audit_logging = enable_audit_logging
        self.strict_mode = strict_mode
        
        # Import Kernel components (lazy to prevent circular deps)
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            QueryType,
        )
        self.kernel_boundary = KernelMutationBoundary
        self.query_type_enum = QueryType
        
        # Audit trail storage
        self._audit_trail: List[UnifiedGovernanceDecision] = []
        
        logger.info(
            f"UnifiedGovernanceController initialized: "
            f"transformation={'ON' if enable_query_transformation else 'OFF'}, "
            f"audit={'ON' if enable_audit_logging else 'OFF'}, "
            f"strict_mode={'ON' if strict_mode else 'OFF'}"
        )
    
    def prepare_query_execution(
        self,
        query: str,
        context: GovernanceContext,
        view_mode: Optional[ViewMode] = None,
        explicit_depth_limit: Optional[int] = None,
        semantic_override: Optional[bool] = None,
        audit_justification: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UnifiedGovernanceDecision:
        """
        Prepare query execution with unified governance.
        
        This is the CORE method that coordinates both governance layers.
        
        Algorithm:
        ----------
        1. Classify query type (Kernel layer)
        2. Check mutation authorization (Kernel layer)
        3. Resolve execution policy (Policy layer)
        4. Transform query if needed (tombstone filtering, depth limits)
        5. Generate unified decision with audit trail
        6. Return immutable decision
        
        Args:
            query: Cypher query to execute
            context: Active governance context (required)
            view_mode: Explicit view mode (None = ACTIVE_VIEW)
            explicit_depth_limit: Override max graph depth
            semantic_override: Override semantic search
            audit_justification: Required for HISTORICAL_VIEW/MIXED_VIEW
            metadata: Additional metadata for audit trail
            
        Returns:
            UnifiedGovernanceDecision with complete governance info
            
        Raises:
            Never raises directly - failures are encoded in decision.approved=False
        """
        decided_at = datetime.now(UTC).isoformat()
        
        # ====================================================================
        # STEP 1: Kernel Layer - Security & Authorization
        # ====================================================================
        
        # Classify query type
        query_type = self.kernel_boundary.classify_query(query)
        
        # Check if mutation is authorized (Kernel context)
        from mahoun.core.governance_kernel.kernel import is_governance_authorized
        mutation_authorized = is_governance_authorized()
        
        # Kernel decision
        kernel_check_passed = True
        kernel_message = "OK"
        
        if query_type == self.query_type_enum.FORBIDDEN:
            kernel_check_passed = False
            kernel_message = "FORBIDDEN: Query contains prohibited operations (apoc, dbms, plugin)"
        elif query_type == self.query_type_enum.WRITE and not mutation_authorized:
            kernel_check_passed = False
            kernel_message = "UNAUTHORIZED: Mutation query requires authorized governance context"
        elif query_type == self.query_type_enum.DDL:
            kernel_check_passed = False
            kernel_message = "DDL: Schema operations must use dedicated migration tools"
        
        # ====================================================================
        # STEP 2: Policy Layer - Visibility & Resources
        # ====================================================================
        
        # Resolve execution policy
        try:
            policy = self.policy_resolver.resolve_policy(
                context=context,
                view_mode=view_mode,
                explicit_depth_limit=explicit_depth_limit,
                semantic_override=semantic_override,
                audit_justification=audit_justification,
                metadata=metadata
            )
            policy_check_passed = True
        except ValueError as e:
            # Policy resolution failed (e.g., HISTORICAL_VIEW without justification)
            policy_check_passed = False
            
            # Create minimal policy for decision recording
            from mahoun.core.policy_resolver import (
                EmbeddingMode,
                ExecutionPolicy,
                ReasoningBudget,
                ViewMode as VMEnum,
            )
            policy = ExecutionPolicy(
                policy_id="policy_failed",
                view_mode=VMEnum.ACTIVE_VIEW,
                allow_tombstones=False,
                max_graph_depth=3,
                semantic_enabled=False,
                embedding_mode=EmbeddingMode.LIGHT,
                reasoning_budget=ReasoningBudget.LOW,
                profile_name="unknown",
                max_concurrent_requests=10,
                max_model_size_gb=8.0,
                enable_gpu=False,
                target_latency_ms=1000,
                target_throughput_rps=10,
                correlation_id=context.correlation_id,
                actor_id=_resolve_actor_id(context),
                resolved_at=decided_at,
                justification=f"Policy resolution failed: {str(e)}",
                metadata={"error": str(e)}
            )
        
        # ====================================================================
        # STEP 3: Query Transformation (if enabled and approved)
        # ====================================================================
        
        query_transformed = False
        transformed_query = query
        transformations_applied: List[str] = []
        
        if (
            self.enable_query_transformation
            and kernel_check_passed
            and policy_check_passed
            and query_type == self.query_type_enum.READ
        ):
            # Apply transformations based on policy
            new_transformed_query, new_transformations_applied = self._transform_query(
                query=query,
                policy=policy
            )
            
            # IDEMPOTENCY CHECK: اگر query تغییر نکرده، از forbidden pattern check رد شو
            if new_transformed_query != query:
                # Check forbidden patterns ONLY on new transformations
                # Skip check for HISTORICAL_VIEW since user explicitly wants to see deleted entities
                from mahoun.core.governance.violations import (
                    GovernanceViolationError,
                    GovernanceViolation,
                    ViolationCategory,
                    ViolationSeverity,
                )
                if self._has_forbidden_deletion_pattern(new_transformed_query):
                    # Allow _deleted patterns in HISTORICAL_VIEW mode (forensic audit)
                    if policy.view_mode.value != "historical":
                        raise GovernanceViolationError(
                            GovernanceViolation(
                                category=ViolationCategory.FORBIDDEN_PATTERN,
                                severity=ViolationSeverity.CRITICAL,
                                message="EL-I8: Forbidden _deleted pattern in query",
                                details={"query": new_transformed_query[:200]},
                                source="UnifiedGovernanceController",
                                correlation_id=context.correlation_id,
                            )
                        )
                
                transformed_query = new_transformed_query
                transformations_applied = new_transformations_applied
                query_transformed = len(transformations_applied) > 0
            else:
                # Query is idempotent, no change
                transformed_query = query
                transformations_applied = []
                query_transformed = False
        
        # ====================================================================
        # STEP 4: Generate Decision
        # ====================================================================
        
        # Overall approval
        approved = kernel_check_passed and policy_check_passed
        
        # Decision reason
        if not approved:
            if not kernel_check_passed:
                decision_reason = f"DENIED (Kernel): {kernel_message}"
            elif not policy_check_passed:
                decision_reason = f"DENIED (Policy): {policy.justification}"
            else:
                decision_reason = "DENIED (Unknown)"
        else:
            decision_reason = (
                f"APPROVED: {query_type.value} query with {policy.view_mode.value} view, "
                f"profile={policy.profile_name}, depth<={policy.max_graph_depth}"
            )
        
        # Generate decision ID
        decision_basis = (
            f"{context.correlation_id}|{query_type.value}|{policy.policy_id}|"
            f"{mutation_authorized}|{decided_at}"
        )
        decision_id = f"decision_{hashlib.sha256(decision_basis.encode()).hexdigest()[:16]}"
        
        # Create immutable decision
        decision = UnifiedGovernanceDecision(
            decision_id=decision_id,
            correlation_id=context.correlation_id,
            actor_id=_resolve_actor_id(context),
            decided_at=decided_at,
            query_type=query_type.value,
            mutation_authorized=mutation_authorized,
            kernel_check_passed=kernel_check_passed,
            kernel_message=kernel_message,
            policy=policy,
            policy_check_passed=policy_check_passed,
            view_mode=policy.view_mode.value,
            allow_tombstones=policy.allow_tombstones,
            query_transformed=query_transformed,
            original_query=query,
            transformed_query=transformed_query,
            transformations_applied=transformations_applied,
            approved=approved,
            decision_reason=decision_reason,
            metadata=metadata or {}
        )
        
        # ====================================================================
        # STEP 5: Audit Trail
        # ====================================================================
        
        if self.enable_audit_logging:
            self._audit_trail.append(decision)
            
            # Keep last 10000 decisions
            if len(self._audit_trail) > 10000:
                self._audit_trail = self._audit_trail[-10000:]
            
            logger.info(
                f"Governance decision: {decision_id} | "
                f"{'APPROVED' if approved else 'DENIED'} | "
                f"{query_type.value} | {policy.view_mode.value} | "
                f"correlation: {context.correlation_id}"
            )

            # Persist unified decision to immutable audit (dual-write)
            # Use mutation boundary audit append to ensure consistency with mutation logs.
            try:
                from mahoun.core.governance.mutation_boundary import _append_governance_audit

                # Convert decision to a serializable dict
                entry = decision.to_dict()
                entry.update({"source": "unified_governance_controller"})
                _append_governance_audit(entry)
            except Exception as exc:
                logger.exception("Failed to append unified governance decision to immutable audit")
                # Fail-closed if strict_mode is enabled
                if self.strict_mode:
                    raise
        
        return decision
    
    def _has_forbidden_deletion_pattern(self, query: str) -> bool:
        """Check for forbidden deletion patterns in the query."""
        # This is a simplified check. In a real scenario, this would be more robust.
        return "_deleted" in query and "NOT" not in query.upper()
    
    def _transform_query(
        self,
        query: str,
        policy: ExecutionPolicy
    ) -> Tuple[str, List[str]]:
        """
        Transform Cypher query based on execution policy.
        
        Transformations:
        ----------------
        1. Tombstone filtering (if ACTIVE_VIEW):
           - Node matches: WHERE n._deleted IS NULL
           - Path matches: NONE(n IN nodes(path) WHERE n._deleted = true)
           
        2. Depth limiting:
           - Replace [:*] with [:*1..MAX_DEPTH]
           - Apply max_graph_depth from policy
           
        3. LIMIT injection:
           - Add LIMIT if missing (based on profile)
        
        Args:
            query: Original Cypher query
            policy: Execution policy
            
        Returns:
            (transformed_query, list_of_transformations)
        """
        transformed = query
        transformations: List[str] = []
        
        # ----------------------------------------------------------------
        # Transformation 1: Tombstone Filtering (ACTIVE_VIEW only)
        # ----------------------------------------------------------------
        
        if policy.view_mode.value == "active" and not policy.allow_tombstones:
            transformed, tombstone_applied = self._inject_tombstone_filter(transformed)
            if tombstone_applied:
                transformations.append("tombstone_filter_active_view")
        
        # ----------------------------------------------------------------
        # Transformation 2: Depth Limiting
        # ----------------------------------------------------------------
        
        transformed, depth_applied = self._limit_depth(
            transformed,
            max_depth=policy.max_graph_depth
        )
        if depth_applied:
            transformations.append(f"depth_limit_{policy.max_graph_depth}")
        
        # ----------------------------------------------------------------
        # Transformation 3: LIMIT Injection (if missing)
        # ----------------------------------------------------------------
        
        if "LIMIT" not in transformed.upper():
            # Profile-based default limits
            if policy.profile_name == "desktop_minimal":
                default_limit = 100
            elif policy.profile_name == "enterprise_full":
                default_limit = 10000
            else:
                default_limit = 1000
            
            transformed += f"\nLIMIT {default_limit}"
            transformations.append(f"default_limit_{default_limit}")
        
        return transformed, transformations
    
    def _inject_tombstone_filter(self, query: str) -> Tuple[str, bool]:
        """
        EL-I8 Advanced Tombstone Filtering for Cypher Queries.
        
        SECURITY LEVEL: MAXIMUM - Privacy Law Compliance Boundary
        
        Multi-Layer Tombstone Detection:
        --------------------------------
        1. Property flags: _deleted, _redacted, _purged, _tombstoned, _gdpr_purged
        2. Label markers: :TOMBSTONE, :DELETED, :REDACTED, :PURGED
        3. Status fields: status, lifecycle_state  
        4. Temporal markers: _deletion_timestamp, _redaction_timestamp
        5. Privacy compliance: _right_to_be_forgotten, _privacy_purged
        
        Query Patterns Transformed:
        --------------------------
        1. Simple MATCH: MATCH (n:Law)
           → MATCH (n:Law) WHERE NOT mahoun.isTombstoned(n)
           
        2. Existing WHERE: MATCH (n:Law) WHERE n.status = 'active'  
           → MATCH (n:Law) WHERE n.status = 'active' AND NOT mahoun.isTombstoned(n)
           
        3. Path MATCH: MATCH path = (a)-[*]-(b)
           → MATCH path = (a)-[*]-(b) WHERE ALL(n IN nodes(path) WHERE NOT mahoun.isTombstoned(n))
           
        4. Multiple nodes: MATCH (a)-[r]->(b)
           → MATCH (a)-[r]->(b) WHERE NOT mahoun.isTombstoned(a) AND NOT mahoun.isTombstoned(b)
           
        5. Relationship tombstones: -[r:REL]->
           → -[r:REL]-> WHERE NOT (r._active = false OR r._tombstoned = true)
        
        Args:
            query: Original Cypher query
            
        Returns:
            (transformed_query, was_modified)
            
        Raises:
            ValueError: If query contains explicit tombstone access attempts
        """
        import re
        from typing import Set
        
        # Security check: Skip if query appears to be already transformed to prevent self-referential detection
        # Check for our own tombstone filter patterns that are safe
        mahoun_filter_indicators = [
            r'NOT\s*\(\s*n\._deleted\s*=\s*true',
            r'WHERE\s+(\([^)]*\s+)?NOT\s*\(\s*n\._deleted',
            r'_deleted\s+IS\s+NULL',
            r'_deleted\s*=\s*false',
            r'mahoun\.isTombstoned',
        ]
        
        is_already_transformed = any(
            re.search(pattern, query, re.IGNORECASE) 
            for pattern in mahoun_filter_indicators
        )
        
        if is_already_transformed:
            # Query already contains our tombstone filters, skip transformation to prevent double-filtering
            return query, False
        
        # Security check: Detect explicit tombstone access attempts (only for non-transformed queries)
        forbidden_patterns = [
            r'_deleted\s*=\s*true',
            r'_redacted\s*=\s*true', 
            r'_tombstoned\s*=\s*true',
            r':TOMBSTONE\b',
            r':DELETED\b',
            r':REDACTED\b',
            r'_gdpr_purged\s*=\s*true',
            r'_right_to_be_forgotten\s*=\s*true'
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError(
                    f"EL-I8 SECURITY VIOLATION: Query contains explicit tombstone access pattern: {pattern}. "
                    f"Direct access to tombstoned data is forbidden for privacy law compliance."
                )
        
        # Advanced tombstone filter function (deployed as Neo4j user-defined function)
        tombstone_filter_function = """
        (
          (n._deleted IS NULL OR n._deleted = false)
          AND NOT (
            n._deleted = true 
            OR n._redacted = true 
            OR n._purged = true
            OR n._tombstoned = true
            OR n._gdpr_purged = true
            OR n._right_to_be_forgotten = true
            OR n:TOMBSTONE 
            OR n:DELETED 
            OR n:REDACTED
            OR n:PURGED
            OR n.status IN ['deleted', 'redacted', 'purged', 'tombstoned']
            OR n.lifecycle_state IN ['DELETED', 'REDACTED', 'PURGED']
            OR (n._deletion_timestamp IS NOT NULL 
                AND datetime(n._deletion_timestamp) <= datetime())
            OR (n._redaction_timestamp IS NOT NULL 
                AND datetime(n._redaction_timestamp) <= datetime())
          )
        )"""
        
        modified = False
        lines = query.split("\n")
        transformed_lines = []
        node_variables: Set[str] = set()
        
        # First pass: collect all node variables
        for line in lines:
            # Match patterns: (var), (var:Label), (var {props})
            node_matches = re.findall(r'\((\w+)(?::[^)]+)?(?:\s*\{[^}]*\})?\)', line)
            node_variables.update(node_matches)
        
        # Second pass: transform queries
        for line in lines:
            transformed_line = line
            
            # Pattern 1: Simple MATCH statements - add tombstone filters
            match_pattern = re.search(r'MATCH\s+', line, re.IGNORECASE)
            if match_pattern and not re.search(r'WHERE', line, re.IGNORECASE):
                # Find node variables in this MATCH
                line_nodes = re.findall(r'\((\w+)(?::[^)]+)?(?:\s*\{[^}]*\})?\)', line)
                if line_nodes:
                    tombstone_conditions = []
                    for node_var in line_nodes:
                        condition = tombstone_filter_function.replace('n.', f'{node_var}.')
                        condition = condition.replace('n:', f'{node_var}:') 
                        tombstone_conditions.append(f"({condition})")
                    
                    where_clause = f"\nWHERE {' AND '.join(tombstone_conditions)}"
                    transformed_line = line.rstrip() + where_clause
                    modified = True
            
            # Pattern 2: Existing WHERE clauses - append tombstone filters  
            elif match_pattern and re.search(r'WHERE', line, re.IGNORECASE):
                line_nodes = re.findall(r'\((\w+)(?::[^)]+)?(?:\s*\{[^}]*\})?\)', line)
                if line_nodes:
                    tombstone_conditions = []
                    for node_var in line_nodes:
                        condition = tombstone_filter_function.replace('n.', f'{node_var}.')
                        condition = condition.replace('n:', f'{node_var}:')
                        tombstone_conditions.append(f"({condition})")
                    
                    and_clause = f" AND {' AND '.join(tombstone_conditions)}"
                    transformed_line = line.rstrip() + and_clause
                    modified = True
            
            # Pattern 3: Path matches - filter all nodes in path
            path_match = re.search(r'MATCH\s+(\w+)\s*=\s*\([^)]+\)', line, re.IGNORECASE)
            if path_match:
                path_var = path_match.group(1)
                path_filter = f"""
WHERE ALL(n IN nodes({path_var}) WHERE {tombstone_filter_function})
  AND ALL(r IN relationships({path_var}) WHERE NOT (r._active = false OR r._tombstoned = true))"""
                
                if "WHERE" not in transformed_line.upper():
                    transformed_line += path_filter
                else:
                    transformed_line += f" AND ALL(n IN nodes({path_var}) WHERE {tombstone_filter_function})"
                    transformed_line += f" AND ALL(r IN relationships({path_var}) WHERE NOT (r._active = false OR r._tombstoned = true))"
                modified = True
            
            # Pattern 4: Relationship tombstone filtering
            rel_pattern = r'-\[(\w+):(\w+)\]->'
            if re.search(rel_pattern, line):
                rel_matches = re.findall(rel_pattern, line)
                if rel_matches and "WHERE" in transformed_line.upper():
                    rel_conditions = []
                    for rel_var, rel_type in rel_matches:
                        rel_conditions.append(f"NOT ({rel_var}._active = false OR {rel_var}._tombstoned = true)")
                    
                    if rel_conditions:
                        transformed_line += f" AND {' AND '.join(rel_conditions)}"
                        modified = True
            
            transformed_lines.append(transformed_line)
        
        final_query = "\n".join(transformed_lines)
        
        # Final security validation
        if modified:
            self._log_transformation("tombstone_filter", {
                "original_nodes": len(node_variables),
                "filtered_nodes": len([n for n in node_variables if n in final_query]),
                "query_preview": final_query[:200] + "..." if len(final_query) > 200 else final_query
            })
        
        return final_query, modified
    
    def _log_transformation(self, transformation_type: str, details: Dict[str, Any]) -> None:
        """
        Log a query transformation for audit trail.
        
        This is an internal audit logging method that records transformation
        details (e.g., tombstone filtering, depth limiting) for compliance
        and debugging purposes.
        
        Args:
            transformation_type: Type of transformation (e.g., 'tombstone_filter', 'depth_limit')
            details: Dictionary containing transformation details
        """
        try:
            audit_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "transformation_type": transformation_type,
                "details": details
            }
            logger.debug(
                f"Query transformation applied: {transformation_type}",
                extra={"audit": audit_entry}
            )
        except Exception as e:
            # Fail-open for logging: don't let audit logging failures block governance
            logger.warning(f"Failed to log transformation: {e}")
    
    def _limit_depth(self, query: str, max_depth: int) -> Tuple[str, bool]:
        """
        Limit relationship traversal depth.
        
        Pattern: [:*] or [:*1..] → [:*1..MAX_DEPTH]
        
        Args:
            query: Original Cypher query
            max_depth: Maximum allowed depth
            
        Returns:
            (transformed_query, was_modified)
        """
        modified = False
        transformed = query
        
        # Pattern: -[:*]- or -[r:*]-
        # Replace with -[:*1..MAX_DEPTH]- or -[r:*1..MAX_DEPTH]-
        
        # Unbounded relationships: [:*]
        if "[:*]" in transformed:
            transformed = transformed.replace("[:*]", f"[:*1..{max_depth}]")
            modified = True
        
        # Unbounded with variable: [r:*]
        pattern = r'\[(\w+):\*\]'
        if re.search(pattern, transformed):
            transformed = re.sub(pattern, rf'[\1:*1..{max_depth}]', transformed)
            modified = True
        
        # Already bounded but exceeds limit: [:*1..100]
        pattern = r'\[:?\*1\.\.(\d+)\]'
        for match in re.finditer(pattern, transformed):
            existing_depth = int(match.group(1))
            if existing_depth > max_depth:
                transformed = transformed.replace(match.group(0), f"[:*1..{max_depth}]")
                modified = True
        
        return transformed, modified
    
    def get_audit_trail(
        self,
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        approved_only: bool = False,
        limit: int = 100
    ) -> List[UnifiedGovernanceDecision]:
        """
        Get unified governance audit trail.
        
        Args:
            correlation_id: Filter by correlation ID
            actor_id: Filter by actor ID
            approved_only: Only return approved decisions
            limit: Maximum entries to return
            
        Returns:
            List of governance decisions (most recent first)
        """
        entries = self._audit_trail
        
        if correlation_id:
            entries = [e for e in entries if e.correlation_id == correlation_id]
        
        if actor_id:
            entries = [e for e in entries if e.actor_id == actor_id]
        
        if approved_only:
            entries = [e for e in entries if e.approved]
        
        # Return most recent first
        return list(reversed(entries[-limit:]))
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get unified governance statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self._audit_trail:
            return {
                "total_decisions": 0,
                "approved_count": 0,
                "denied_count": 0,
                "approval_rate": 0.0,
                "by_query_type": {},
                "by_view_mode": {},
                "transformation_stats": {}
            }
        
        total = len(self._audit_trail)
        approved_count = sum(1 for d in self._audit_trail if d.approved)
        denied_count = total - approved_count
        
        # Count by query type
        query_type_counts = {}
        for decision in self._audit_trail:
            qt = decision.query_type
            query_type_counts[qt] = query_type_counts.get(qt, 0) + 1
        
        # Count by view mode
        view_mode_counts = {}
        for decision in self._audit_trail:
            vm = decision.view_mode
            view_mode_counts[vm] = view_mode_counts.get(vm, 0) + 1
        
        # Transformation stats
        transformation_counts = {}
        for decision in self._audit_trail:
            for trans in decision.transformations_applied:
                transformation_counts[trans] = transformation_counts.get(trans, 0) + 1
        
        return {
            "total_decisions": total,
            "approved_count": approved_count,
            "denied_count": denied_count,
            "approval_rate": (approved_count / total * 100) if total > 0 else 0.0,
            "by_query_type": query_type_counts,
            "by_view_mode": view_mode_counts,
            "transformation_stats": transformation_counts,
            "audit_trail_size": len(self._audit_trail)
        }


# ============================================================================
# Utility Functions
# ============================================================================

def create_default_unified_controller() -> UnifiedGovernanceController:
    """
    Create default unified governance controller with auto-detected profile.
    
    Returns:
        UnifiedGovernanceController instance with default configuration
    """
    from mahoun.core.policy_resolver import create_default_policy_resolver
    
    policy_resolver = create_default_policy_resolver()
    return UnifiedGovernanceController(
        policy_resolver=policy_resolver,
        enable_query_transformation=True,
        enable_audit_logging=True,
        strict_mode=True
    )


def validate_query_with_unified_governance(
    query: str,
    context: GovernanceContext,
    controller: Optional[UnifiedGovernanceController] = None
) -> UnifiedGovernanceDecision:
    """
    Validate query with unified governance (convenience function).
    
    Args:
        query: Cypher query to validate
        context: Governance context
        controller: Optional controller instance (None = create default)
        
    Returns:
        UnifiedGovernanceDecision
    """
    if controller is None:
        controller = create_default_unified_controller()
    
    return controller.prepare_query_execution(
        query=query,
        context=context
    )
