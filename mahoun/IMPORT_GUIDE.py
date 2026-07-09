"""
🎯 MAHOUN Smart Import Guide
===========================

این فایل IDE تو guide می‌کنه تا درست import کنه.
Developer هم می‌تونه با Ctrl+F کلاس موردنظر رو پیدا کنه.

═══════════ TOP 10 MOST USED CLASSES ═══════════

from mahoun.core import ReasoningResult       # ✅ CANONICAL (48 files use this)
from mahoun.core import SecurityBreachException # ✅ CANONICAL (17 files use this) 
from mahoun.core import Entity                # ✅ CANONICAL (7 files use this)
from mahoun.reasoning import ReasoningMode    # ✅ CANONICAL (60+ files use this)

═══════════ DUPLICATE CLASS RESOLVER ═══════════

🔍 ReasoningResult duplicates:
  ✅ mahoun.core.models.ReasoningResult                    ← USE THIS
  ❌ mahoun.reasoning.reasoning_recorder.ReasoningResult   ← DEPRECATED  
  ❌ mahoun.rag.ultra_evaluation_system.ReasoningResult   ← DEPRECATED

🔍 Entity duplicates:  
  ✅ mahoun.core.models.Entity                           ← USE THIS
  ❌ mahoun.graph.builders.entity_extractor.Entity       ← DEPRECATED
  ❌ mahoun.pipelines.embed_index.Entity                 ← DEPRECATED

🔍 SecurityBreachException duplicates:
  ✅ mahoun.core.exceptions.SecurityBreachException      ← USE THIS  
  ❌ mahoun.guardrails.exceptions.SecurityBreachException ← DEPRECATED

🔍 ReasoningMode duplicates:
  ✅ mahoun.reasoning.unified_reasoning_service.ReasoningMode ← USE THIS (CANONICAL)
  ❌ mahoun.reasoning.reasoning_chain.ReasoningChainMode      ← RENAMED 
  ❌ mahoun.reasoning.symbolic_reasoner.SymbolicReasoningMode ← RENAMED
  ❌ mahoun.agents.contract_agent.ContractReasoningMode       ← RENAMED
  ❌ mahoun.orchestrator.runtime_profile.RuntimeReasoningMode ← RENAMED

🔍 FaithfulnessCalculator duplicates:
  ✅ mahoun.rag.ultra_evaluation_system.FaithfulnessCalculator ← USE THIS
  ❌ mahoun.monitoring.legal_metrics.FaithfulnessCalculator    ← DEPRECATED
  ❌ mahoun.finetuning.feedback_pipeline.FaithfulnessCalculator ← DEPRECATED

═══════════ QUICK PATTERNS ═══════════

# Core business logic:
from mahoun.core import ReasoningResult, SecurityBreachException, Entity

# Reasoning & AI:  
from mahoun.reasoning import ReasoningMode, UnifiedReasoningService
from mahoun.reasoning import ChainOfThoughtReasoner

# RAG & Retrieval:
from mahoun.rag import HybridRAGService, FaithfulnessCalculator  

# Graph & Neo4j:
from mahoun.graph import GraphQueryService, UltraGraphBuilder

═══════════ IDE AUTOCOMPLETE HELPERS ═══════════

# These imports help IDEs suggest the right paths:
"""

# Primary canonical classes (IDE should suggest these first)
from mahoun.core.models import ReasoningResult as _ReasoningResult_PREFERRED
from mahoun.core.models import Entity as _Entity_PREFERRED  
from mahoun.core.exceptions import SecurityBreachException as _SecurityBreachException_PREFERRED
from mahoun.reasoning.unified_reasoning_service import ReasoningMode as _ReasoningMode_PREFERRED
from mahoun.rag.ultra_evaluation_system import FaithfulnessCalculator as _FaithfulnessCalculator_PREFERRED

# Development note: Don't import this file in runtime code - it's for IDE/developer reference only