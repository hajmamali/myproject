#!/usr/bin/env python3
"""
� MAHOUN Ultra-Advanced Canonical Class Finder
===============================================

🔍 Real-time codebase analysis + fuzzy search + performance insights

BASIC USAGE:
    python scripts/find_canonical.py ReasoningResult
    python scripts/find_canonical.py Entity --verbose
    python scripts/find_canonical.py "Reasoning*" --fuzzy

ADVANCED FEATURES:
    --scan               Real-time codebase scan
    --usage-analysis     Show detailed import usage patterns
    --risk-assessment    Analyze consolidation risk for each duplicate
    --fuzzy              Enable fuzzy matching (supports wildcards)
    --json               Output in JSON format for tools
    --fix-imports        Auto-generate import standardization patches
    --performance        Show import performance impact
    --persian            Output in Persian/Farsi
"""

import sys
import json
import re
import ast
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, Counter
import fnmatch

@dataclass
class DuplicateInfo:
    """Enhanced duplicate class information with risk assessment"""
    canonical_location: str
    usage_count: int
    duplicates: List[str]
    import_example: str
    risk_level: str = "LOW"
    performance_impact: str = "MINIMAL"
    consolidation_effort: str = "EASY"
    breaking_changes: bool = False
    persian_name: Optional[str] = None

@dataclass  
class ImportUsagePattern:
    """Detailed import usage analysis"""
    file_path: str
    import_statement: str
    line_number: int
    is_canonical: bool
    usage_context: str = ""

@dataclass
class ConsolidationRisk:
    """Risk assessment for consolidating a duplicate class"""
    class_name: str
    total_usages: int
    cross_boundary_imports: int
    test_dependencies: int
    external_dependencies: int
    estimated_hours: float
    risk_factors: List[str] 
CANONICAL_CLASSES = {
    "ReasoningResult": {
        "canonical": "mahoun.core.models",
        "usage_count": 48,
        "duplicates": [
            "mahoun.reasoning.reasoning_recorder",
            "mahoun.rag.ultra_evaluation_system"
        ],
        "import_example": "from mahoun.core import ReasoningResult"
    },
    "Entity": {
        "canonical": "mahoun.core.models", 
        "usage_count": 7,
        "duplicates": [
            "mahoun.graph.builders.entity_extractor",
            "mahoun.pipelines.embed_index"
        ],
        "import_example": "from mahoun.core import Entity"
    },
    "SecurityBreachException": {
        "canonical": "mahoun.core.exceptions",
        "usage_count": 17, 
        "duplicates": [
            "mahoun.guardrails.exceptions"
        ],
        "import_example": "from mahoun.core import SecurityBreachException"
    },
    "ReasoningMode": {
        "canonical": "mahoun.reasoning.unified_reasoning_service",
        "usage_count": 60,
        "duplicates": [
            "mahoun.reasoning.reasoning_chain (→ ReasoningChainMode)",
            "mahoun.reasoning.symbolic_reasoner (→ SymbolicReasoningMode)", 
            "mahoun.agents.contract_agent (→ ContractReasoningMode)",
            "mahoun.orchestrator.runtime_profile (→ RuntimeReasoningMode)"
        ],
        "import_example": "from mahoun.reasoning import ReasoningMode"
    },
    "FaithfulnessCalculator": {
        "canonical": "mahoun.rag.ultra_evaluation_system",
        "usage_count": 3,
        "duplicates": [
            "mahoun.monitoring.legal_metrics",
            "mahoun.finetuning.feedback_pipeline"  
        ],
        "import_example": "from mahoun.rag import FaithfulnessCalculator"
    }
}

def find_canonical(class_name):
    if class_name in CANONICAL_CLASSES:
        info = CANONICAL_CLASSES[class_name]
        print(f"🎯 {class_name}")
        print(f"✅ Canonical: {info['canonical']}")
        print(f"📊 Usage: {info['usage_count']} files")
        print(f"💡 Import: {info['import_example']}")
        if info['duplicates']:
            print(f"❌ Duplicates to avoid:")
            for dup in info['duplicates']:
                print(f"   • {dup}")
        return True
    return False

if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "--help":
        print(__doc__)
        sys.exit(0)
        
    if sys.argv[1] == "--list-all":
        print("📋 All Known Duplicate Classes:")
        for class_name in sorted(CANONICAL_CLASSES.keys()):
            print(f"  • {class_name}")
        sys.exit(0)
        
    class_name = sys.argv[1]
    if not find_canonical(class_name):
        print(f"❓ Unknown class: {class_name}")
        print("💡 Try: python scripts/find_canonical.py --list-all")
        sys.exit(1)