# ADR-0002: Unified Bootstrap Manager Architecture

**Status:** PROPOSED  
**Date:** 2026-07-29  
**Impact:** TIER-1 CRITICAL

## Context

فعلاً startup پراکنده است:
- api/main.py → lifespan()
- mahoun/bootstrap/runtime.py
- Scattered initialization

## Decision

BootstrapManager با 12 phases:
1. Runtime Integrity
2. Configuration
3. Governance Kernel
4. Immutable Ledger
5. Neo4j
6. Policy Engine
7. Embedding Models
8. LLM Loader
9. Agent Registry
10. Services
11. API
12. Readiness Gate

## Benefits

- Single Point of Truth
- Fail-Fast with Context
- Observable
- Testable
- Rollback-Ready

## Implementation

Phase 1: Create BootstrapManager
Phase 2: Advanced patterns (circuit breaker, metrics)
Phase 3: Production integration
