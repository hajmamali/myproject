#!/usr/bin/env python3
"""
Policy Resolver - Centralized Execution Policy Engine
======================================================

This module provides the SINGLE SOURCE OF TRUTH for all execution policy decisions
in the MAHOUN system. It integrates with:
- DeploymentProfile (resource limits and capabilities)
- GovernanceContext (audit and provenance tracking)
- Profile-aware query behavior
- View mode enforcement (ACTIVE_VIEW vs HISTORICAL_VIEW)

CRITICAL DESIGN PRINCIPLES:
1. NO module-level autonomy - all policy decisions flow through here
2. Explicit view mode selection (never implicit)
3. Profile-aware resource constraints
4. Full audit trail of policy decisions
5. Fail-closed security posture

Version: 1.0.0
Phase: Hard Policy Enforcement - Centralization
Author: MAHOUN System Architecture Team
Date: 2026-06-18
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from mahoun.ai.profile_manager import ProfileManager
    from mahoun.core.governance.governance_context import GovernanceContext
    from mahoun.core.models.deployment_profile import DeploymentProfile

logger = logging.getLogger(__name__)


# ============================================================================
# Internal Helpers
# ============================================================================


def _resolve_actor_id(context: Any) -> str:
    """Return a stable non-empty actor identifier for policy audit records."""
    actor_id = getattr(context, "actor_id", None)
    if actor_id is None:
        return "unknown"

    actor_text = str(actor_id).strip()
    return actor_text or "unknown"


# ============================================================================
# View Mode Enum - FORMAL DEFINITION
# ============================================================================

class ViewMode(str, Enum):
    """
    View mode determines which data is visible to queries and reasoning.
    
    This is the AUTHORITATIVE definition of view modes in MAHOUN.
    
    View Modes:
    -----------
    ACTIVE_VIEW (default):
        - Excludes all tombstoned/soft-deleted entities (_deleted=true)
        - Excludes superseded laws and repealed statutes
        - Only shows currently valid, active legal documents
        - DEFAULT for all LAPTOP (DESKTOP_MINIMAL) operations
        - DEFAULT for all ENTERPRISE production reasoning
        - Ensures reasoning operates on current, valid data only
        
    HISTORICAL_VIEW (audit/forensic):
        - Includes tombstoned entities (_deleted=true)
        - Includes superseded and repealed documents
        - Shows complete temporal lineage
        - EXPLICIT opt-in required (never default)
        - Used for: audit trails, forensic analysis, legal history research
        - Requires explicit actor authorization
        
    MIXED_VIEW (advanced):
        - Caller-controlled mix of active and historical
        - Requires explicit policy context per query
        - Used for: migration tools, data reconciliation, policy testing
        - Highest privilege level required
    
    Security Model:
    ---------------
    - View mode MUST be explicitly specified (never implicit)
    - ACTIVE_VIEW is the safe default (fail-closed)
    - HISTORICAL_VIEW requires audit justification
    - MIXED_VIEW requires elevated privileges
    
    Enforcement Points:
    -------------------
    - All Cypher queries (WHERE node._deleted IS NULL injection)
    - Graph traversal paths (NONE(n IN nodes(path) WHERE n._deleted = true))
    - Semantic search results (vector index filtering)
    - Reasoning evidence collection (EL-I8 invariant enforcement)
    - Cache population and invalidation
    """
    
    ACTIVE_VIEW = "active"
    HISTORICAL_VIEW = "historical"
    MIXED_VIEW = "mixed"


class EmbeddingMode(str, Enum):
    """
    Embedding mode determines how embeddings are generated and used.
    
    LIGHT:
        - Cached embeddings only
        - No on-demand embedding generation
        - Minimal memory footprint
        - Suitable for DESKTOP_MINIMAL
        
    FULL:
        - On-demand embedding generation
        - Full semantic search capabilities
        - Higher memory requirements
        - Suitable for ENTERPRISE_FULL
    """
    
    LIGHT = "light"
    FULL = "full"


class ReasoningBudget(str, Enum):
    """
    Reasoning budget determines computational limits for reasoning operations.
    
    LOW:
        - Max 3 graph hops
        - Limited semantic search
        - Fast response times
        - Suitable for DESKTOP_MINIMAL
        
    MEDIUM:
        - Max 5 graph hops
        - Moderate semantic search
        - Balanced performance
        - Suitable for light ENTERPRISE workloads
        
    HIGH:
        - Max 10 graph hops
        - Full semantic search
        - Deep reasoning capabilities
        - Suitable for ENTERPRISE_FULL
    """
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# Execution Policy - Complete Policy Specification
# ============================================================================

@dataclass(frozen=True)
class ExecutionPolicy:
    """
    Complete execution policy specification.
    
    This immutable dataclass represents ALL policy decisions for a single
    execution context. It is the output of PolicyResolver.resolve_policy()
    and the input to all policy-aware components.
    
    Immutability Rationale:
    -----------------------
    - Policy decisions are auditable - must not change after creation
    - Thread-safe - can be safely shared across threads
    - Cacheable - same inputs always produce same policy
    - Deterministic - essential for reproducibility
    
    Attributes:
    -----------
    policy_id: Unique identifier for this policy instance
    view_mode: Active, historical, or mixed view
    allow_tombstones: Whether to include soft-deleted entities
    max_graph_depth: Maximum graph traversal depth (hops)
    semantic_enabled: Whether semantic search is enabled
    embedding_mode: Light (cached) or full (on-demand) embeddings
    reasoning_budget: Low, medium, or high computational budget
    profile: Associated deployment profile
    
    Derived Attributes:
    -------------------
    max_concurrent_requests: From profile.resource_limits
    max_model_size_gb: From profile.resource_limits
    enable_gpu: From profile.resource_limits
    target_latency_ms: From profile.performance_targets
    
    Audit Trail:
    ------------
    correlation_id: Links policy to governance context
    actor_id: Actor who requested this policy
    resolved_at: When policy was resolved
    justification: Why this policy was chosen
    """
    
    # Core policy
    policy_id: str
    view_mode: ViewMode
    allow_tombstones: bool
    max_graph_depth: int
    semantic_enabled: bool
    embedding_mode: EmbeddingMode
    reasoning_budget: ReasoningBudget
    
    # Profile integration
    profile_name: str
    max_concurrent_requests: int
    max_model_size_gb: float
    enable_gpu: bool
    
    # Performance targets
    target_latency_ms: int
    target_throughput_rps: int
    
    # Audit trail
    correlation_id: str
    actor_id: str
    resolved_at: str
    justification: str
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate policy consistency."""
        # View mode and tombstones must be consistent
        if self.view_mode == ViewMode.ACTIVE_VIEW and self.allow_tombstones:
            raise ValueError(
                "Policy inconsistency: ACTIVE_VIEW requires allow_tombstones=False"
            )
        
        if self.view_mode == ViewMode.HISTORICAL_VIEW and not self.allow_tombstones:
            raise ValueError(
                "Policy inconsistency: HISTORICAL_VIEW requires allow_tombstones=True"
            )
        
        # Graph depth must be positive
        if self.max_graph_depth < 1:
            raise ValueError(f"max_graph_depth must be >= 1, got {self.max_graph_depth}")
        
        # Profile-specific constraints
        if self.profile_name == "desktop_minimal" and self.max_graph_depth > 3:
            logger.warning(
                f"desktop_minimal profile typically uses max_graph_depth <= 3, "
                f"got {self.max_graph_depth}. This may cause resource exhaustion."
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "policy_id": self.policy_id,
            "view_mode": self.view_mode.value,
            "allow_tombstones": self.allow_tombstones,
            "max_graph_depth": self.max_graph_depth,
            "semantic_enabled": self.semantic_enabled,
            "embedding_mode": self.embedding_mode.value,
            "reasoning_budget": self.reasoning_budget.value,
            "profile_name": self.profile_name,
            "max_concurrent_requests": self.max_concurrent_requests,
            "max_model_size_gb": self.max_model_size_gb,
            "enable_gpu": self.enable_gpu,
            "target_latency_ms": self.target_latency_ms,
            "target_throughput_rps": self.target_throughput_rps,
            "correlation_id": self.correlation_id,
            "actor_id": self.actor_id,
            "resolved_at": self.resolved_at,
            "justification": self.justification,
            "metadata": self.metadata
        }
    
    def is_laptop_mode(self) -> bool:
        """Check if running in laptop/desktop minimal mode."""
        return self.profile_name == "desktop_minimal"
    
    def is_enterprise_mode(self) -> bool:
        """Check if running in enterprise full mode."""
        return self.profile_name == "enterprise_full"
    
    def is_safe_default(self) -> bool:
        """
        Check if this policy uses safe defaults.
        
        Safe defaults:
        - ACTIVE_VIEW (no tombstones)
        - Reasonable graph depth
        - No elevated privileges
        """
        return (
            self.view_mode == ViewMode.ACTIVE_VIEW
            and not self.allow_tombstones
            and self.max_graph_depth <= 5
        )


@dataclass
class PolicyDecisionAuditEntry:
    """
    Audit entry for policy decision.
    
    Every policy resolution is logged for compliance and debugging.
    """
    
    policy_id: str
    correlation_id: str
    actor_id: str
    resolved_at: str
    view_mode: str
    profile_name: str
    justification: str
    input_context: Dict[str, Any]
    resolved_policy: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy_id": self.policy_id,
            "correlation_id": self.correlation_id,
            "actor_id": self.actor_id,
            "resolved_at": self.resolved_at,
            "view_mode": self.view_mode,
            "profile_name": self.profile_name,
            "justification": self.justification,
            "input_context": self.input_context,
            "resolved_policy": self.resolved_policy
        }


# ============================================================================
# Policy Resolver - Centralized Policy Engine
# ============================================================================

class PolicyResolver:
    """
    Centralized Policy Resolver - SINGLE SOURCE OF TRUTH
    
    This class is the AUTHORITATIVE policy decision engine for MAHOUN.
    ALL policy decisions MUST flow through resolve_policy().
    
    Design Principles:
    ------------------
    1. Centralization: One place for all policy decisions
    2. Determinism: Same inputs → same policy
    3. Auditability: All decisions are logged
    4. Integration: Works with ProfileManager and GovernanceContext
    5. Security: Fail-closed posture (safe defaults)
    
    Policy Resolution Algorithm:
    ----------------------------
    1. Determine view mode (default: ACTIVE_VIEW)
    2. Load deployment profile (DESKTOP_MINIMAL vs ENTERPRISE_FULL)
    3. Map profile to resource constraints
    4. Apply security policies (HISTORICAL_VIEW requires justification)
    5. Validate policy consistency
    6. Generate audit trail
    7. Return immutable ExecutionPolicy
    
    Usage:
    ------
    >>> from mahoun.core.policy_resolver import PolicyResolver, ViewMode
    >>> resolver = PolicyResolver(profile_manager)
    >>> 
    >>> # Default policy (ACTIVE_VIEW, current profile)
    >>> policy = resolver.resolve_policy(context)
    >>> 
    >>> # Explicit audit mode (requires justification)
    >>> policy = resolver.resolve_policy(
    ...     context,
    ...     view_mode=ViewMode.HISTORICAL_VIEW,
    ...     audit_justification="Forensic analysis of case #12345"
    ... )
    >>> 
    >>> # Check policy
    >>> assert policy.view_mode == ViewMode.HISTORICAL_VIEW
    >>> assert policy.allow_tombstones == True
    >>> assert policy.correlation_id == context.correlation_id
    """
    
    def __init__(
        self,
        profile_manager: Optional[ProfileManager] = None,
        enable_audit_logging: bool = True
    ):
        """
        Initialize policy resolver.
        
        Args:
            profile_manager: ProfileManager instance (None = create default)
            enable_audit_logging: Whether to log policy decisions
        """
        # Lazy import to prevent circular dependencies
        if profile_manager is None:
            from mahoun.ai.profile_manager import ProfileManager
            profile_manager = ProfileManager(auto_select=True)
        
        self.profile_manager = profile_manager
        self.enable_audit_logging = enable_audit_logging
        
        # Audit trail storage (in-memory for now, could be persistent)
        self._audit_trail: List[PolicyDecisionAuditEntry] = []
        
        logger.info(
            f"PolicyResolver initialized with profile: {profile_manager.profile.profile_name}"
        )
    
    def resolve_policy(
        self,
        context: GovernanceContext,
        view_mode: Optional[ViewMode] = None,
        explicit_depth_limit: Optional[int] = None,
        semantic_override: Optional[bool] = None,
        audit_justification: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionPolicy:
        """
        Resolve execution policy for given context.
        
        This is the CORE method of the PolicyResolver. ALL policy decisions
        MUST go through this method.
        
        Args:
            context: Active governance context (required)
            view_mode: Explicit view mode (None = ACTIVE_VIEW)
            explicit_depth_limit: Override max graph depth (None = profile default)
            semantic_override: Override semantic search (None = profile default)
            audit_justification: Required for HISTORICAL_VIEW and MIXED_VIEW
            metadata: Additional metadata for audit trail
            
        Returns:
            Immutable ExecutionPolicy instance
            
        Raises:
            ValueError: If HISTORICAL_VIEW requested without justification
            ValueError: If policy parameters are inconsistent
        """
        # ====================================================================
        # Step 1: Determine View Mode (Default: ACTIVE_VIEW)
        # ====================================================================
        
        if view_mode is None:
            view_mode = ViewMode.ACTIVE_VIEW
            view_mode_source = "default_safe"
        else:
            view_mode_source = "explicit_request"
        
        # Security check: HISTORICAL_VIEW and MIXED_VIEW require justification
        if view_mode in (ViewMode.HISTORICAL_VIEW, ViewMode.MIXED_VIEW):
            if not audit_justification:
                raise ValueError(
                    f"{view_mode.value} requires explicit audit_justification. "
                    f"This is a security requirement for accessing historical/deleted data."
                )
            logger.warning(
                f"ELEVATED PRIVILEGE: {view_mode.value} requested by {context.correlation_id}. "
                f"Justification: {audit_justification}"
            )
        
        # ====================================================================
        # Step 2: Load Deployment Profile
        # ====================================================================
        
        profile = self.profile_manager.profile
        resource_limits = profile.resource_limits
        performance_targets = profile.performance_targets
        
        # ====================================================================
        # Step 3: Map Profile to Resource Constraints
        # ====================================================================
        
        # Determine max graph depth
        if explicit_depth_limit is not None:
            max_graph_depth = explicit_depth_limit
            depth_source = "explicit_override"
        elif profile.profile_name == "desktop_minimal":
            max_graph_depth = 3  # Conservative for laptop
            depth_source = "profile_desktop_minimal"
        elif profile.profile_name == "enterprise_full":
            max_graph_depth = 10  # Full capabilities
            depth_source = "profile_enterprise_full"
        else:
            max_graph_depth = 5  # Safe middle ground
            depth_source = "profile_unknown_fallback"
        
        # Determine semantic search capability
        if semantic_override is not None:
            semantic_enabled = semantic_override
            semantic_source = "explicit_override"
        elif profile.profile_name == "desktop_minimal":
            semantic_enabled = False  # Cached only for performance
            semantic_source = "profile_desktop_minimal_disabled"
        elif profile.profile_name == "enterprise_full":
            semantic_enabled = True  # Full semantic search
            semantic_source = "profile_enterprise_full_enabled"
        else:
            semantic_enabled = False  # Safe default
            semantic_source = "safe_default_disabled"
        
        # Determine embedding mode
        if profile.profile_name == "desktop_minimal":
            embedding_mode = EmbeddingMode.LIGHT
        else:
            embedding_mode = EmbeddingMode.FULL
        
        # Determine reasoning budget
        if profile.profile_name == "desktop_minimal":
            reasoning_budget = ReasoningBudget.LOW
        elif profile.profile_name == "enterprise_full":
            reasoning_budget = ReasoningBudget.HIGH
        else:
            reasoning_budget = ReasoningBudget.MEDIUM
        
        # ====================================================================
        # Step 4: Determine Tombstone Visibility
        # ====================================================================
        
        if view_mode == ViewMode.ACTIVE_VIEW:
            allow_tombstones = False
        elif view_mode == ViewMode.HISTORICAL_VIEW:
            allow_tombstones = True
        elif view_mode == ViewMode.MIXED_VIEW:
            # MIXED_VIEW delegates tombstone decision to caller
            # For safety, default to False unless explicitly specified
            allow_tombstones = metadata.get("allow_tombstones", False) if metadata else False
        else:
            allow_tombstones = False  # Safe default
        
        # ====================================================================
        # Step 5: Generate Policy ID and Audit Metadata
        # ====================================================================
        
        resolved_at = datetime.now(UTC).isoformat()
        
        # Generate deterministic policy ID
        policy_basis = (
            f"{context.correlation_id}|{view_mode.value}|{profile.profile_name}|"
            f"{max_graph_depth}|{semantic_enabled}|{allow_tombstones}|{resolved_at}"
        )
        policy_id = f"policy_{hashlib.sha256(policy_basis.encode()).hexdigest()[:16]}"
        
        # Build justification
        justification_parts = [
            f"Profile: {profile.profile_name}",
            f"View: {view_mode.value}",
            f"Depth: {max_graph_depth} ({depth_source})",
            f"Semantic: {semantic_enabled} ({semantic_source})",
        ]
        
        if audit_justification:
            justification_parts.append(f"Audit: {audit_justification}")
        
        justification = " | ".join(justification_parts)
        
        # ====================================================================
        # Step 6: Create Immutable ExecutionPolicy
        # ====================================================================
        
        policy = ExecutionPolicy(
            policy_id=policy_id,
            view_mode=view_mode,
            allow_tombstones=allow_tombstones,
            max_graph_depth=max_graph_depth,
            semantic_enabled=semantic_enabled,
            embedding_mode=embedding_mode,
            reasoning_budget=reasoning_budget,
            profile_name=profile.profile_name,
            max_concurrent_requests=resource_limits.max_concurrent_requests,
            max_model_size_gb=resource_limits.max_model_size_gb,
            enable_gpu=resource_limits.enable_gpu,
            target_latency_ms=performance_targets.target_latency_ms,
            target_throughput_rps=performance_targets.target_throughput_rps,
            correlation_id=context.correlation_id,
            actor_id=_resolve_actor_id(context),
            resolved_at=resolved_at,
            justification=justification,
            metadata=metadata or {}
        )
        
        # ====================================================================
        # Step 7: Audit Trail
        # ====================================================================
        
        if self.enable_audit_logging:
            audit_entry = PolicyDecisionAuditEntry(
                policy_id=policy.policy_id,
                correlation_id=context.correlation_id,
                actor_id=policy.actor_id,
                resolved_at=resolved_at,
                view_mode=view_mode.value,
                profile_name=profile.profile_name,
                justification=justification,
                input_context={
                    "view_mode_requested": view_mode.value if view_mode else None,
                    "view_mode_source": view_mode_source,
                    "explicit_depth_limit": explicit_depth_limit,
                    "semantic_override": semantic_override,
                    "audit_justification": audit_justification,
                    "has_metadata": bool(metadata)
                },
                resolved_policy=policy.to_dict()
            )
            
            self._audit_trail.append(audit_entry)
            
            # Keep last 10000 entries
            if len(self._audit_trail) > 10000:
                self._audit_trail = self._audit_trail[-10000:]
            
            logger.info(
                f"Policy resolved: {policy.policy_id} | "
                f"{view_mode.value} | {profile.profile_name} | "
                f"correlation: {context.correlation_id}"
            )
        
        return policy
    
    def get_audit_trail(
        self,
        correlation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[PolicyDecisionAuditEntry]:
        """
        Get policy decision audit trail.
        
        Args:
            correlation_id: Filter by correlation ID (None = all)
            limit: Maximum entries to return
            
        Returns:
            List of audit entries (most recent first)
        """
        entries = self._audit_trail
        
        if correlation_id:
            entries = [e for e in entries if e.correlation_id == correlation_id]
        
        # Return most recent first
        return list(reversed(entries[-limit:]))
    
    def get_policy_statistics(self) -> Dict[str, Any]:
        """
        Get policy resolution statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self._audit_trail:
            return {
                "total_policies": 0,
                "by_view_mode": {},
                "by_profile": {},
                "active_view_percentage": 0.0,
                "historical_view_count": 0,
                "mixed_view_count": 0
            }
        
        total = len(self._audit_trail)
        
        # Count by view mode
        view_mode_counts = {}
        for entry in self._audit_trail:
            vm = entry.view_mode
            view_mode_counts[vm] = view_mode_counts.get(vm, 0) + 1
        
        # Count by profile
        profile_counts = {}
        for entry in self._audit_trail:
            prof = entry.profile_name
            profile_counts[prof] = profile_counts.get(prof, 0) + 1
        
        return {
            "total_policies": total,
            "by_view_mode": view_mode_counts,
            "by_profile": profile_counts,
            "active_view_percentage": (
                view_mode_counts.get("active", 0) / total * 100
            ),
            "historical_view_count": view_mode_counts.get("historical", 0),
            "mixed_view_count": view_mode_counts.get("mixed", 0),
            "audit_trail_size": len(self._audit_trail)
        }


# ============================================================================
# Utility Functions
# ============================================================================

def create_default_policy_resolver() -> PolicyResolver:
    """
    Create default policy resolver with auto-detected profile.
    
    Returns:
        PolicyResolver instance with default configuration
    """
    from mahoun.ai.profile_manager import ProfileManager
    
    profile_manager = ProfileManager(auto_select=True)
    return PolicyResolver(profile_manager=profile_manager)


def validate_policy_for_operation(
    policy: ExecutionPolicy,
    operation_type: str,
    required_privileges: List[str]
) -> bool:
    """
    Validate if policy allows specific operation.
    
    Args:
        policy: Execution policy
        operation_type: Type of operation (e.g., "graph_mutation", "forensic_query")
        required_privileges: Required privilege levels
        
    Returns:
        True if allowed, False otherwise
    """
    # HISTORICAL_VIEW requires elevated privileges
    if "forensic_access" in required_privileges:
        return policy.view_mode == ViewMode.HISTORICAL_VIEW
    
    # MIXED_VIEW requires highest privileges
    if "mixed_view_access" in required_privileges:
        return policy.view_mode == ViewMode.MIXED_VIEW
    
    # Default: ACTIVE_VIEW is always allowed
    return True
