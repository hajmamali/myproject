"""
MAHOUN Provenance Factory
==========================

Single point of creation for all provenance metadata.
Ensures cryptographic integrity and governance compliance.

All Producers MUST use this factory instead of manual dict construction.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata


class ProvenanceFactory:
    """
    Factory for creating governance-compliant provenance metadata.
    
    CRITICAL: This is the ONLY way to create valid provenance.
    All graph writes MUST use this factory or GovernanceContextManager.require_provenance().
    
    Usage:
        # In production (with active governance context):
        prov = ProvenanceFactory.create_for_graph_write(
            source="ingestion_pipeline:ner",
            author="worker-123",
            correlation_id="corr-abc"
        )
        
        # In tests (without governance context):
        prov = ProvenanceFactory.create_test(
            source="test",
            author="test_runner",
            correlation_id="test-123"
        )
    """
    
    @staticmethod
    def create(
        source: str,
        correlation_id: str,
        author: str,
        governance_scope_id: str,
        runtime_attestation_id: str,
        lineage_parent: Optional[str] = None,
        document_id: Optional[str] = None,
        pipeline_version: Optional[str] = None,
    ) -> ProvenanceMetadata:
        """
        Create full ProvenanceMetadata with cryptographic attestation.
        
        This is the canonical factory method. All other methods delegate to this.
        """
        return ProvenanceMetadata.create(
            source=source,
            correlation_id=correlation_id,
            author=author,
            governance_scope_id=governance_scope_id,
            runtime_attestation_id=runtime_attestation_id,
            lineage_parent=lineage_parent,
            document_id=document_id,
            pipeline_version=pipeline_version,
        )
    
    @staticmethod
    def create_for_graph_write(
        source: str,
        author: str,
        correlation_id: str,
        lineage_parent: Optional[str] = None,
        document_id: Optional[str] = None,
        pipeline_version: Optional[str] = None,
    ) -> ProvenanceMetadata:
        """
        Create provenance for a graph write operation.
        
        Requires active GovernanceContext. Extracts governance_scope_id
        and runtime_attestation_id from the current context.
        
        Args:
            source: Origin of the data (e.g., "ingestion_pipeline:ner")
            author: Actor identifier
            correlation_id: Correlation ID for tracing
            lineage_parent: Optional parent provenance ID
            document_id: Optional source document ID
            pipeline_version: Optional pipeline version
            
        Returns:
            Complete ProvenanceMetadata with cryptographic attestation
            
        Raises:
            GovernanceViolationError: If no active governance context
        """
        ctx = GovernanceContextManager.require_context()
        
        return ProvenanceMetadata.create(
            source=source,
            correlation_id=correlation_id,
            author=author,
            governance_scope_id=ctx.context_id,
            runtime_attestation_id=ctx.runtime_attestation.get("context_id", ctx.context_id),
            lineage_parent=lineage_parent,
            document_id=document_id,
            pipeline_version=pipeline_version,
        )
    
    @staticmethod
    def create_test(
        source: str,
        author: str,
        correlation_id: str,
        governance_scope_id: str = "test-scope",
        runtime_attestation_id: str = "test-attestation",
        lineage_parent: Optional[str] = None,
        document_id: Optional[str] = None,
        pipeline_version: Optional[str] = "test",
    ) -> Dict[str, Any]:
        """
        Create test provenance as a plain dict (for unit tests).
        
        IMPORTANT: This creates a dict representation, not ProvenanceMetadata.
        Use only in tests where governance context is not available.
        
        Args:
            source: Origin of the data
            author: Actor identifier
            correlation_id: Correlation ID for tracing
            governance_scope_id: Test governance scope ID
            runtime_attestation_id: Test attestation ID
            lineage_parent: Optional parent provenance ID
            document_id: Optional source document ID
            pipeline_version: Optional pipeline version
            
        Returns:
            Complete provenance dict with all required fields
        """
        # Generate timestamp internally (NOT externally writable)
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Build base data for hashing
        base_data = {
            "source": source,
            "timestamp": timestamp,
            "correlation_id": correlation_id,
            "author": author,
            "document_id": document_id,
            "pipeline_version": pipeline_version,
        }
        
        # Compute cryptographic hash
        provenance_hash = ProvenanceFactory._compute_hash(base_data)
        
        # Compute cryptographic signature
        provenance_signature = ProvenanceFactory._sign_provenance(
            base_data, governance_scope_id
        )
        
        return {
            "source": source,
            "timestamp": timestamp,
            "correlation_id": correlation_id,
            "author": author,
            "provenance_hash": provenance_hash,
            "provenance_signature": provenance_signature,
            "governance_scope_id": governance_scope_id,
            "runtime_attestation_id": runtime_attestation_id,
            "lineage_parent": lineage_parent,
            "document_id": document_id,
            "pipeline_version": pipeline_version,
        }
    
    @staticmethod
    def create_test_metadata(
        source: str,
        author: str,
        correlation_id: str,
        governance_scope_id: str = "test-scope",
        runtime_attestation_id: str = "test-attestation",
    ) -> ProvenanceMetadata:
        """
        Create test ProvenanceMetadata instance (for tests that need the object).
        
        Args:
            source: Origin of the data
            author: Actor identifier
            correlation_id: Correlation ID for tracing
            governance_scope_id: Test governance scope ID
            runtime_attestation_id: Test attestation ID
            
        Returns:
            ProvenanceMetadata instance with test attestation
        """
        return ProvenanceMetadata.create(
            source=source,
            correlation_id=correlation_id,
            author=author,
            governance_scope_id=governance_scope_id,
            runtime_attestation_id=runtime_attestation_id,
            pipeline_version="test",
        )
    
    @staticmethod
    def _compute_hash(data: Dict[str, Any]) -> str:
        """Compute SHA256 hash of provenance data for cryptographic integrity."""
        # Sort keys for deterministic hashing
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    @staticmethod
    def _sign_provenance(data: Dict[str, Any], governance_scope_id: str) -> str:
        """Sign provenance data with governance scope for attestation."""
        combined = json.dumps(data, sort_keys=True, default=str) + governance_scope_id
        return hashlib.sha256(combined.encode()).hexdigest()


# Convenience function for tests
def build_test_provenance(
    correlation_id: str,
    author: str = "automated_test_runner",
    source: str = "test",
) -> Dict[str, Any]:
    """
    Standard governance-compliant provenance payload for test environments.
    
    This helper ensures all governance-aware tests use a stable and 
    future-compatible provenance contract.
    
    Returns complete dict with all required fields including
    cryptographic attestation.
    """
    return ProvenanceFactory.create_test(
        source=source,
        author=author,
        correlation_id=correlation_id,
    )


# Backwards compatibility alias
def build_provenance_dict(
    source: str,
    author: str,
    correlation_id: str,
    governance_scope_id: str = "test-scope",
    runtime_attestation_id: str = "test-attestation",
) -> Dict[str, Any]:
    """Deprecated: Use ProvenanceFactory.create_test() instead."""
    return ProvenanceFactory.create_test(
        source=source,
        author=author,
        correlation_id=correlation_id,
        governance_scope_id=governance_scope_id,
        runtime_attestation_id=runtime_attestation_id,
    )