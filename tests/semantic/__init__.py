"""
Phase 2A Semantic Enrichment Tests.

This package contains acceptance tests for the semantic schema contract.

Priority: Negative tests > Positive tests
Philosophy: Zero-hallucination depends on REJECTING bad inputs.

Test Categories:
1. Negative Tests (PRIORITY 1):
   - Missing evidence rejection
   - Unverified endpoint rejection
   - Duplicate identity rejection
   - Ambiguous extraction handling
   - Governance bypass prevention
   - CI enforcement

2. Positive Tests (PRIORITY 2):
   - Valid entity creation
   - Valid assertion creation
   - Provenance chain integrity
   - Schema compliance
"""
