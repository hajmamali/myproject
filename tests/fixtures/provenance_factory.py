from datetime import datetime, timezone
from typing import Dict, Any

from mahoun.core.governance.provenance_factory import ProvenanceFactory


def build_test_provenance(
    correlation_id: str,
    author: str = "automated_test_runner",
    source: str = "test",
) -> Dict[str, Any]:
    """
    Standard governance-compliant provenance payload
    for test environments.

    This helper exists to ensure all governance-aware
    tests use a stable and future-compatible provenance
    contract.
    """
    return ProvenanceFactory.create_test(
        source=source,
        author=author,
        correlation_id=correlation_id,
    )
