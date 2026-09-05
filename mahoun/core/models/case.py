"""
MAHOUN Case Management Models (Phase 2C)
========================================
Classification: CANONICAL CASE ISOLATION MODELS
Purpose: Case identity, ownership, lifecycle, and security boundary management.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4


class CaseLifecycleState(str, Enum):
    """Lifecycle states of a legal case."""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class CaseAccessLevel(str, Enum):
    """Access levels for case data."""
    OWNER = "OWNER"          # Full read/write access
    COLLABORATOR = "COLLABORATOR"  # Read/write access to shared content
    VIEWER = "VIEWER"        # Read-only access
    NO_ACCESS = "NO_ACCESS"  # No access


@dataclass(frozen=True)
class CaseIdentity:
    """
    Canonical case identifier with deterministic generation.
    Replaces inconsistent case_id semantics from Phase 2B audit.
    """
    case_id: str
    content_fingerprint: str  # SHA-256 of question + facts (deterministic)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None  # User ID
    correlation_id: Optional[str] = None  # Request correlation
    
    @classmethod
    def from_content(
        cls, 
        question: str, 
        facts: List[str],
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> "CaseIdentity":
        """
        Create deterministic case identity from content.
        Same content = same case_id (idempotent).
        """
        # Sort facts for deterministic hash
        sorted_facts = sorted(facts) if facts else []
        case_basis = f"{question}|{'|'.join(sorted_facts)}"
        content_fingerprint = hashlib.sha256(case_basis.encode("utf-8")).hexdigest()
        case_id = f"case_{content_fingerprint[:16]}"
        
        return cls(
            case_id=case_id,
            content_fingerprint=content_fingerprint,
            created_by=user_id,
            correlation_id=correlation_id
        )
    
    @classmethod
    def from_user_provided(
        cls,
        case_id: str,
        question: str,
        facts: List[str],
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> "CaseIdentity":
        """
        Create case identity from user-provided case_id.
        Used when user wants to specify their own case identifier.
        """
        # Still compute content fingerprint for integrity
        sorted_facts = sorted(facts) if facts else []
        case_basis = f"{question}|{'|'.join(sorted_facts)}"
        content_fingerprint = hashlib.sha256(case_basis.encode("utf-8")).hexdigest()
        
        return cls(
            case_id=case_id,
            content_fingerprint=content_fingerprint,
            created_by=user_id,
            correlation_id=correlation_id
        )

    def validate(self) -> bool:
        """Validate case identity integrity."""
        return (
            self.case_id and 
            self.content_fingerprint and
            len(self.content_fingerprint) == 64  # Full SHA-256
        )


@dataclass
class CaseOwnership:
    """
    Case ownership and access control model.
    Enforces user → case relationship.
    """
    case_id: str
    owner_user_id: str
    collaborators: Set[str] = field(default_factory=set)
    viewers: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_access_level(self, user_id: str) -> CaseAccessLevel:
        """Get user's access level for this case."""
        if user_id == self.owner_user_id:
            return CaseAccessLevel.OWNER
        elif user_id in self.collaborators:
            return CaseAccessLevel.COLLABORATOR
        elif user_id in self.viewers:
            return CaseAccessLevel.VIEWER
        else:
            return CaseAccessLevel.NO_ACCESS
    
    def can_read(self, user_id: str) -> bool:
        """Check if user can read case data."""
        return self.get_access_level(user_id) != CaseAccessLevel.NO_ACCESS
    
    def can_write(self, user_id: str) -> bool:
        """Check if user can write to case."""
        access_level = self.get_access_level(user_id)
        return access_level in {CaseAccessLevel.OWNER, CaseAccessLevel.COLLABORATOR}
    
    def can_manage(self, user_id: str) -> bool:
        """Check if user can manage case (add/remove users, change state)."""
        return self.get_access_level(user_id) == CaseAccessLevel.OWNER
    
    def add_collaborator(self, user_id: str, added_by: str) -> bool:
        """Add collaborator (only owners can do this)."""
        if not self.can_manage(added_by):
            return False
        self.collaborators.add(user_id)
        self.updated_at = datetime.now(timezone.utc)
        return True
    
    def add_viewer(self, user_id: str, added_by: str) -> bool:
        """Add viewer (only owners can do this)."""
        if not self.can_manage(added_by):
            return False
        self.viewers.add(user_id)
        self.updated_at = datetime.now(timezone.utc)
        return True


@dataclass
class CaseLifecycle:
    """
    Case lifecycle management.
    Tracks state transitions and business rules.
    """
    case_id: str
    state: CaseLifecycleState = CaseLifecycleState.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def transition_to(self, new_state: CaseLifecycleState, user_id: str, reason: str = "") -> bool:
        """
        Transition case to new state with validation.
        """
        if not self._is_valid_transition(self.state, new_state):
            return False
        
        # Record transition
        transition = {
            "from_state": self.state.value,
            "to_state": new_state.value,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "reason": reason
        }
        self.state_history.append(transition)
        
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        return True
    
    def _is_valid_transition(self, from_state: CaseLifecycleState, to_state: CaseLifecycleState) -> bool:
        """Validate state transition rules."""
        valid_transitions = {
            CaseLifecycleState.CREATED: {CaseLifecycleState.ACTIVE},
            CaseLifecycleState.ACTIVE: {CaseLifecycleState.UNDER_REVIEW, CaseLifecycleState.CLOSED},
            CaseLifecycleState.UNDER_REVIEW: {CaseLifecycleState.ACTIVE, CaseLifecycleState.CLOSED},
            CaseLifecycleState.CLOSED: {CaseLifecycleState.ARCHIVED},
            CaseLifecycleState.ARCHIVED: set()  # Terminal state
        }
        
        return to_state in valid_transitions.get(from_state, set())
    
    def can_modify(self) -> bool:
        """Check if case can be modified (not closed/archived)."""
        return self.state not in {CaseLifecycleState.CLOSED, CaseLifecycleState.ARCHIVED}


@dataclass
class CaseSecurityBoundary:
    """
    Security boundary enforcement for case isolation.
    Central point for all case access control decisions.
    """
    identity: CaseIdentity
    ownership: CaseOwnership
    lifecycle: CaseLifecycle
    
    @classmethod
    def create_new_case(
        cls,
        question: str,
        facts: List[str],
        owner_user_id: str,
        case_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> "CaseSecurityBoundary":
        """Create new case with proper security setup."""
        # Create identity
        if case_id:
            identity = CaseIdentity.from_user_provided(
                case_id=case_id,
                question=question,
                facts=facts,
                user_id=owner_user_id,
                correlation_id=correlation_id
            )
        else:
            identity = CaseIdentity.from_content(
                question=question,
                facts=facts,
                user_id=owner_user_id,
                correlation_id=correlation_id
            )
        
        # Create ownership
        ownership = CaseOwnership(
            case_id=identity.case_id,
            owner_user_id=owner_user_id
        )
        
        # Create lifecycle
        lifecycle = CaseLifecycle(case_id=identity.case_id)
        
        return cls(
            identity=identity,
            ownership=ownership,
            lifecycle=lifecycle
        )
    
    def authorize_read(self, user_id: str) -> bool:
        """Authorize read access with full security check."""
        return (
            self.ownership.can_read(user_id) and
            self.lifecycle.state != CaseLifecycleState.ARCHIVED
        )
    
    def authorize_write(self, user_id: str) -> bool:
        """Authorize write access with full security check."""
        return (
            self.ownership.can_write(user_id) and
            self.lifecycle.can_modify()
        )
    
    def authorize_manage(self, user_id: str) -> bool:
        """Authorize management access."""
        return self.ownership.can_manage(user_id)


class CaseAuthorizationError(Exception):
    """Exception raised when case authorization fails."""
    
    def __init__(self, case_id: str, user_id: str, operation: str, reason: str = ""):
        self.case_id = case_id
        self.user_id = user_id
        self.operation = operation
        self.reason = reason
        super().__init__(
            f"Case authorization failed: user '{user_id}' cannot '{operation}' "
            f"case '{case_id}'{': ' + reason if reason else ''}"
        )


class CaseValidationError(Exception):
    """Exception raised when case validation fails."""
    
    def __init__(self, case_id: str, issue: str):
        self.case_id = case_id
        self.issue = issue
        super().__init__(f"Case validation failed for '{case_id}': {issue}")


@dataclass
class CaseScopeFilter:
    """
    Filter for case-scoped queries and operations.
    Used to enforce case isolation in RAG, Graph, and Evidence queries.
    """
    case_id: str
    user_id: str
    access_level: CaseAccessLevel
    include_system_knowledge: bool = True  # Whether to include shared legal knowledge
    
    def should_include_content(self, content_case_id: Optional[str]) -> bool:
        """Determine if content should be included based on case scope."""
        # Always include system/shared knowledge (no case_id)
        if not content_case_id and self.include_system_knowledge:
            return True
        
        # Include content from same case
        if content_case_id == self.case_id:
            return True
        
        # Exclude everything else (cross-case isolation)
        return False
    
    def get_case_filter_params(self) -> Dict[str, Any]:
        """Get parameters for case filtering in queries."""
        return {
            "case_id": self.case_id,
            "user_id": self.user_id,
            "include_system": self.include_system_knowledge
        }