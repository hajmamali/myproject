# mahoun/invariants/versions.py
"""
Invariant Versioning
====================

Tracks versions of system invariants for auditability.
Versions are immutable and recorded per verdict.
"""

# Current invariant version - must be updated when invariants change
INVARIANT_VERSION = "1.1.0"

# Changelog of invariant changes
CHANGELOG = {
    "1.0.0": "Initial evidence ledger invariants",
    "1.1.0": "Added privacy filtering for sensitive facts",
}