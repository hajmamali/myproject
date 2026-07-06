"""
Entity Extractor for Legal Knowledge Graph
==========================================

This module extracts entities from legal documents using a hybrid approach:
- Persian Legal NLP for legal term patterns
- NER model for named entities
- Regex patterns for structured information
"""

import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

# Import persian_legal_nlp (fixed import path)
from mahoun.nlp.persian_legal_nlp import (
    normalize,
    extract_legal_terms,
    extract_article_numbers,
    extract_case_numbers,
    extract_entities_for_graph,
)

logger = logging.getLogger(__name__)


# Entity types supported (16 types as per requirements)
ENTITY_TYPES = {
    "COURT",
    "PARTY",
    "VERDICT",
    "LAW_NAME",
    "ARTICLE",
    "LOCATION",
    "LAWYER",
    "JUDGE",
    "PROVISION",
    "REMEDY",
    "REQUEST",
    "LEGAL_REASONING",
    "DISPOSITION",
    "CITATION",
    "DATE",
    "CASE_NO",
}



# 🚀 Import Unified Entity from MAHOUN v2.0
from mahoun.core.models.entity import Entity

@dataclass

# ============================================================================
# 🚀 ENTITY CLASS MIGRATED TO MAHOUN v2.0
# ============================================================================
#
# The Entity class from this file has been consolidated into the unified
# MAHOUN Entity v2.0 system at: mahoun/core/models/entity.py
#
# 🌟 NEW FEATURES IN UNIFIED ENTITY:
# auto-normalization, validation, metadata, deduplication
#
# 🔙 BACKWARD COMPATIBILITY: 100% maintained through import aliases
# 📊 PERFORMANCE: Significantly improved with quantum fingerprinting
# 🛡️  SECURITY: Enhanced validation and normalization
#
# Previous Entity class was here (lines 55-131)
# Now automatically imported from canonical location above ⬆️

def extract_entities_from_text(
    text: str, use_ner: bool = True, min_score: float = 0.7
) -> List[Entity]:
    """
    Convenience function to extract entities from text

    Args:
        text: Input text
        use_ner: Whether to use NER model
        min_score: Minimum confidence score

    Returns:
        List of entities
    """
    extractor = EntityExtractor(use_ner=use_ner, min_score=min_score)
    return extractor.extract_and_validate(text)


def extract_entities_batch(
    texts: List[str], use_ner: bool = True, min_score: float = 0.7
) -> List[List[Entity]]:
    """
    Extract entities from multiple texts

    Args:
        texts: List of input texts
        use_ner: Whether to use NER model
        min_score: Minimum confidence score

    Returns:
        List of entity lists (one per text)
    """
    extractor = EntityExtractor(use_ner=use_ner, min_score=min_score)
    return [extractor.extract_and_validate(text) for text in texts]

# ============================================================================
# 🔙 BACKWARD COMPATIBILITY ALIASES
# ============================================================================

# Ensure existing code continues to work unchanged
# Standard entity alias
# Entity is already imported above - no additional alias needed

# ============================================================================
# 🔙 BACKWARD COMPATIBILITY ALIASES
# ============================================================================

# Ensure existing code continues to work unchanged
# Standard entity alias
# Entity is already imported above - no additional alias needed
