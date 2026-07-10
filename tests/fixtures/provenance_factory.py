from datetime import datetime, timezone
from typing import Dict, Any


def build_test_provenance(
    correlation_id: str,
    author: str = "automated_test_runner",
) -> Dict[str, Any]:
    """
    Standard governance-compliant provenance payload
    for test environments.

    This helper exists to ensure all governance-aware
    tests use a stable and future-compatible provenance
    contract.
    """

    return {
        "author": author,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
