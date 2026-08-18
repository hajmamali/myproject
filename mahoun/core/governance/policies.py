"""
MAHOUN Governance Policies
===========================

Classification: CRITICAL / CENTRALIZED POLICY DEFINITIONS
Purpose: Single source of truth for all governance policies.

Policies are loaded from constitution/RedLines.yaml and are immutable
after initialization. Both Runtime and Lifecycle governance layers
consume policies from this module.

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple


@dataclass(frozen=True)
class GovernancePolicy:
    """Immutable governance policy definition.

    Attributes:
        name: Policy identifier (e.g., 'proof_tree_required').
        description: Human-readable description.
        enabled: Whether the policy is active.
        threshold: Numeric threshold (if applicable).
        required_fields: Fields that must be present.
        forbidden_patterns: Patterns that must not appear.
    """

    name: str
    description: str
    enabled: bool = True
    threshold: Optional[float] = None
    required_fields: FrozenSet[str] = field(default_factory=frozenset)
    forbidden_patterns: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Policy name cannot be empty")
        if self.threshold is not None and not (0.0 <= self.threshold <= 1.0):
            if self.name not in (
                "max_reasoning_time_ms",
                "max_recursion_depth",
            ):
                raise ValueError(
                    f"Threshold must be in [0.0, 1.0] for policy '{self.name}', "
                    f"got {self.threshold}"
                )


class PolicyRegistry:
    """Thread-safe, immutable registry of governance policies.

    Policies are loaded once and cannot be modified at runtime.
    This ensures deterministic policy enforcement.
    """

    def __init__(self, policies: List[GovernancePolicy]) -> None:
        self._policies: Dict[str, GovernancePolicy] = {}
        for policy in policies:
            if policy.name in self._policies:
                raise ValueError(f"Duplicate policy name: {policy.name}")
            self._policies[policy.name] = policy
        self._frozen = True

    def get(self, name: str) -> GovernancePolicy:
        """Get policy by name.

        Raises:
            KeyError: If policy does not exist.
        """
        if name not in self._policies:
            raise KeyError(f"Unknown governance policy: {name}")
        return self._policies[name]

    def get_all(self) -> Tuple[GovernancePolicy, ...]:
        """Get all policies as an immutable tuple."""
        return tuple(self._policies.values())

    def get_enabled(self) -> Tuple[GovernancePolicy, ...]:
        """Get all enabled policies."""
        return tuple(p for p in self._policies.values() if p.enabled)

    def __len__(self) -> int:
        return len(self._policies)

    def __contains__(self, name: str) -> bool:
        return name in self._policies

