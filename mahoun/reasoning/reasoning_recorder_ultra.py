"""
MAHOUN Ultra-Advanced Reasoning Recorder
=========================================
Enterprise-grade reasoning step recording with cryptographic integrity.

KEY FEATURES:
✓ Cryptographic hash-chain with tamper detection
✓ Multi-backend storage (Memory, File, SQLite)
✓ Automatic payload compression
✓ Merkle tree for batch verification
✓ Query interface for forensic analysis
✓ Snapshot/checkpoint system
✓ Full P0-1/P0-5/P1-2 compliance
✓ Thread-safe async operations
✓ Performance metrics and statistics

COMPLIANCE:
- P0-1: Production provenance requires GovernanceContext
- P0-5: Real hash-chain validation with tampering detection
- P1-2: Development mode explicit audit logging
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import zlib
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
from mahoun.core.logging import setup_logger
from mahoun.invariants.versions import INVARIANT_VERSION

log = setup_logger("ultra_reasoning_recorder")


class StepType(str, Enum):
    """Reasoning step type taxonomy."""
    RULE_MATCH = "rule_match"
    SEMANTIC_MATCH = "semantic_match"
    CONTRADICTION_RESOLUTION = "contradiction_resolution"
    EVIDENCE_SYNTHESIS = "evidence_synthesis"
    CAUSAL_INFERENCE = "causal_inference"
    SYMBOLIC_DERIVATION = "symbolic_derivation"
    NEURAL_INFERENCE = "neural_inference"
    GRAPH_TRAVERSAL = "graph_traversal"
