from datetime import datetime, timezone
from typing import Dict, Any


def build_test_provenance(
    correlation_id: str,
    author: str = "automated_test_runner",
    source: str = "test_provenance_builder",
) -> Dict[str, Any]:
    """
    Standard governance-compliant provenance payload
    for test environments.

    This helper exists to ensure all governance-aware
    tests use a stable and future-compatible provenance
    contract.
    
    CRITICAL: Returns full provenance dict with all required fields:
    - source: Origin of the data (required for validation)
    - author: Actor identifier (required for validation)
    - correlation_id: Correlation ID for tracing (required for validation)
    - timestamp: Timestamp of creation (required for validation)
    """

    return {
        "source": source,
        "author": author,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
