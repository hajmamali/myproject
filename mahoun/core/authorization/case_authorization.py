"""
MAHOUN Case Authorization Service (Phase 2C)
============================================
Classification: CANONICAL CASE AUTHORIZATION ENGINE
Purpose: Centralized case access control and security boundary enforcement.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, List, Set
from datetime import datetime, timezone
import sqlite3
import json
import os

from mahoun.core.models.case import (
    CaseIdentity,
    CaseOwnership,
    CaseLifecycle,
    CaseSecurityBoundary,
    CaseAuthorizationError,
    CaseValidationError,
    CaseAccessLevel,
    CaseLifecycleState,
    CaseScopeFilter,
)

logger = logging.getLogger(__name__)


class CaseAuthorizationService:
    """
    Centralized service for case authorization and access control.
    Enforces security boundaries for case isolation.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize with SQLite storage for case metadata."""
        self.storage_path = storage_path or ".mahoun/case_authorization.db"
        self._ensure_storage_directory()
        self._init_database()
        
        # In-memory cache for performance
        self._case_cache: Dict[str, CaseSecurityBoundary] = {}
    
    def _ensure_storage_directory(self):
        """Ensure storage directory exists."""
        storage_dir = os.path.dirname(self.storage_path)
        if storage_dir:
            os.makedirs(storage_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize SQLite database with case tables."""
        with sqlite3.connect(self.storage_path) as conn:
            # Case identities table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS case_identities (
                    case_id TEXT PRIMARY KEY,
                    content_fingerprint TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT,
                    correlation_id TEXT,
                    UNIQUE(content_fingerprint)
                )
            """)
            
            # Case ownership table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS case_ownership (
                    case_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    collaborators TEXT,  -- JSON array
                    viewers TEXT,        -- JSON array
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES case_identities (case_id)
                )
            """)
            
            # Case lifecycle table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS case_lifecycle (
                    case_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    state_history TEXT,  -- JSON array
                    FOREIGN KEY (case_id) REFERENCES case_identities (case_id)
                )
            """)
            
            # Index for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_owner_user_id ON case_ownership (owner_user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_fingerprint ON case_identities (content_fingerprint)")
            
            conn.commit()
    
    def create_case(
        self,
        question: str,
        facts: List[str],
        owner_user_id: str,
        case_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> CaseSecurityBoundary:
        """
        Create new case with proper authorization setup.
        Returns existing case if deterministic content already exists.
        """
        logger.info(f"Creating case for user {owner_user_id}")
        
        # Check if deterministic case already exists
        identity = CaseIdentity.from_content(question, facts, owner_user_id, correlation_id)
        existing = self._get_case_by_fingerprint(identity.content_fingerprint)
        
        if existing:
            logger.info(f"Case already exists with fingerprint {identity.content_fingerprint[:8]}...")
            # Verify user has access to existing case
            if not existing.authorize_read(owner_user_id):
                raise CaseAuthorizationError(
                    existing.identity.case_id,
                    owner_user_id,
                    "access_existing",
                    "Case with same content exists but user lacks access"
                )
            return existing
        
        # Create new case boundary
        boundary = CaseSecurityBoundary.create_new_case(
            question=question,
            facts=facts,
            owner_user_id=owner_user_id,
            case_id=case_id,
            correlation_id=correlation_id
        )
        
        # Validate boundary
        if not boundary.identity.validate():
            raise CaseValidationError(boundary.identity.case_id, "Invalid case identity")
        
        # Store in database
        self._store_case_boundary(boundary)
        
        # Cache for performance
        self._case_cache[boundary.identity.case_id] = boundary
        
        logger.info(f"Created case {boundary.identity.case_id} for user {owner_user_id}")
        return boundary
    
    def get_case(self, case_id: str) -> Optional[CaseSecurityBoundary]:
        """Get case boundary by ID."""
        # Check cache first
        if case_id in self._case_cache:
            return self._case_cache[case_id]
        
        # Load from database
        boundary = self._load_case_boundary(case_id)
        if boundary:
            self._case_cache[case_id] = boundary
        
        return boundary
    
    def authorize_case_access(
        self,
        case_id: str,
        user_id: str,
        operation: str = "read"
    ) -> CaseSecurityBoundary:
        """
        Authorize user access to case.
        Raises CaseAuthorizationError if access denied.
        Returns CaseSecurityBoundary if authorized.
        """
        boundary = self.get_case(case_id)
        if not boundary:
            raise CaseAuthorizationError(case_id, user_id, operation, "Case does not exist")
        
        # Check authorization based on operation
        if operation == "read":
            if not boundary.authorize_read(user_id):
                raise CaseAuthorizationError(case_id, user_id, operation, "Read access denied")
        elif operation == "write":
            if not boundary.authorize_write(user_id):
                raise CaseAuthorizationError(case_id, user_id, operation, "Write access denied")
        elif operation == "manage":
            if not boundary.authorize_manage(user_id):
                raise CaseAuthorizationError(case_id, user_id, operation, "Management access denied")
        else:
            raise CaseAuthorizationError(case_id, user_id, operation, f"Unknown operation: {operation}")
        
        return boundary
    
    def get_user_cases(self, user_id: str) -> List[CaseSecurityBoundary]:
        """Get all cases accessible to user."""
        cases = []
        
        with sqlite3.connect(self.storage_path) as conn:
            # Get owned cases
            cursor = conn.execute("""
                SELECT case_id FROM case_ownership 
                WHERE owner_user_id = ? 
                ORDER BY created_at DESC
            """, (user_id,))
            
            for (case_id,) in cursor.fetchall():
                boundary = self.get_case(case_id)
                if boundary:
                    cases.append(boundary)
            
            # Get cases where user is collaborator/viewer
            cursor = conn.execute("""
                SELECT case_id, collaborators, viewers FROM case_ownership
                WHERE collaborators LIKE ? OR viewers LIKE ?
                ORDER BY created_at DESC
            """, (f'%"{user_id}"%', f'%"{user_id}"%'))
            
            for case_id, collaborators_json, viewers_json in cursor.fetchall():
                if case_id not in [c.identity.case_id for c in cases]:  # Avoid duplicates
                    collaborators = set(json.loads(collaborators_json or "[]"))
                    viewers = set(json.loads(viewers_json or "[]"))
                    
                    if user_id in collaborators or user_id in viewers:
                        boundary = self.get_case(case_id)
                        if boundary:
                            cases.append(boundary)
        
        return cases
    
    def create_case_scope_filter(
        self,
        case_id: str,
        user_id: str,
        include_system_knowledge: bool = True
    ) -> CaseScopeFilter:
        """
        Create case scope filter for RAG/Graph queries.
        """
        boundary = self.authorize_case_access(case_id, user_id, "read")
        access_level = boundary.ownership.get_access_level(user_id)
        
        return CaseScopeFilter(
            case_id=case_id,
            user_id=user_id,
            access_level=access_level,
            include_system_knowledge=include_system_knowledge
        )
    
    def validate_case_id(self, case_id: str) -> bool:
        """Validate case ID format and existence."""
        if not case_id or not isinstance(case_id, str):
            return False
        
        # Check format (basic validation)
        if len(case_id) > 255 or len(case_id) < 1:
            return False
        
        # Check if exists
        return self.get_case(case_id) is not None
    
    def _get_case_by_fingerprint(self, fingerprint: str) -> Optional[CaseSecurityBoundary]:
        """Get case by content fingerprint (for deterministic lookup)."""
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute(
                "SELECT case_id FROM case_identities WHERE content_fingerprint = ?",
                (fingerprint,)
            )
            row = cursor.fetchone()
            if row:
                return self.get_case(row[0])
        return None
    
    def _store_case_boundary(self, boundary: CaseSecurityBoundary):
        """Store case boundary in database."""
        with sqlite3.connect(self.storage_path) as conn:
            # Store identity
            conn.execute("""
                INSERT OR REPLACE INTO case_identities 
                (case_id, content_fingerprint, created_at, created_by, correlation_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                boundary.identity.case_id,
                boundary.identity.content_fingerprint,
                boundary.identity.created_at.isoformat(),
                boundary.identity.created_by,
                boundary.identity.correlation_id
            ))
            
            # Store ownership
            conn.execute("""
                INSERT OR REPLACE INTO case_ownership
                (case_id, owner_user_id, collaborators, viewers, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                boundary.ownership.case_id,
                boundary.ownership.owner_user_id,
                json.dumps(list(boundary.ownership.collaborators)),
                json.dumps(list(boundary.ownership.viewers)),
                boundary.ownership.created_at.isoformat(),
                boundary.ownership.updated_at.isoformat()
            ))
            
            # Store lifecycle
            conn.execute("""
                INSERT OR REPLACE INTO case_lifecycle
                (case_id, state, created_at, updated_at, state_history)
                VALUES (?, ?, ?, ?, ?)
            """, (
                boundary.lifecycle.case_id,
                boundary.lifecycle.state.value,
                boundary.lifecycle.created_at.isoformat(),
                boundary.lifecycle.updated_at.isoformat(),
                json.dumps(boundary.lifecycle.state_history)
            ))
            
            conn.commit()
    
    def _load_case_boundary(self, case_id: str) -> Optional[CaseSecurityBoundary]:
        """Load case boundary from database."""
        with sqlite3.connect(self.storage_path) as conn:
            # Load identity
            cursor = conn.execute("""
                SELECT case_id, content_fingerprint, created_at, created_by, correlation_id
                FROM case_identities WHERE case_id = ?
            """, (case_id,))
            identity_row = cursor.fetchone()
            if not identity_row:
                return None
            
            identity = CaseIdentity(
                case_id=identity_row[0],
                content_fingerprint=identity_row[1],
                created_at=datetime.fromisoformat(identity_row[2]),
                created_by=identity_row[3],
                correlation_id=identity_row[4]
            )
            
            # Load ownership
            cursor = conn.execute("""
                SELECT owner_user_id, collaborators, viewers, created_at, updated_at
                FROM case_ownership WHERE case_id = ?
            """, (case_id,))
            ownership_row = cursor.fetchone()
            if not ownership_row:
                return None
            
            ownership = CaseOwnership(
                case_id=case_id,
                owner_user_id=ownership_row[0],
                collaborators=set(json.loads(ownership_row[1] or "[]")),
                viewers=set(json.loads(ownership_row[2] or "[]")),
                created_at=datetime.fromisoformat(ownership_row[3]),
                updated_at=datetime.fromisoformat(ownership_row[4])
            )
            
            # Load lifecycle
            cursor = conn.execute("""
                SELECT state, created_at, updated_at, state_history
                FROM case_lifecycle WHERE case_id = ?
            """, (case_id,))
            lifecycle_row = cursor.fetchone()
            if not lifecycle_row:
                return None
            
            lifecycle = CaseLifecycle(
                case_id=case_id,
                state=CaseLifecycleState(lifecycle_row[0]),
                created_at=datetime.fromisoformat(lifecycle_row[1]),
                updated_at=datetime.fromisoformat(lifecycle_row[2]),
                state_history=json.loads(lifecycle_row[3] or "[]")
            )
            
            return CaseSecurityBoundary(
                identity=identity,
                ownership=ownership,
                lifecycle=lifecycle
            )


# Global service instance (initialized lazily)
_case_authorization_service: Optional[CaseAuthorizationService] = None


def get_case_authorization_service() -> CaseAuthorizationService:
    """Get global case authorization service (singleton)."""
    global _case_authorization_service
    if _case_authorization_service is None:
        _case_authorization_service = CaseAuthorizationService()
    return _case_authorization_service


def authorize_case_access(case_id: str, user_id: str, operation: str = "read") -> CaseSecurityBoundary:
    """
    Convenience function for case authorization.
    Raises CaseAuthorizationError if access denied.
    """
    service = get_case_authorization_service()
    return service.authorize_case_access(case_id, user_id, operation)


def create_or_get_case(
    question: str,
    facts: List[str],
    owner_user_id: str,
    case_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> CaseSecurityBoundary:
    """
    Convenience function for case creation.
    Returns existing case if deterministic content matches.
    """
    service = get_case_authorization_service()
    return service.create_case(question, facts, owner_user_id, case_id, correlation_id)