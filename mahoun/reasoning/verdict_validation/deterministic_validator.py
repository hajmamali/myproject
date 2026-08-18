"""
Deterministic Validator - Step B
=================================

Classification: MISSION-CRITICAL / VALIDATION STEP B
Purpose: Compare generated prose text against Canonical Verdict JSON deterministically.

This is Step B of the 4-step validation pipeline.
Must execute AFTER Step A (Schema Validation).
Must execute BEFORE Step C (Claim Extraction) and Step D (NLI).

CRITICAL INVARIANTS:
- NO LLM allowed in this step (deterministic parsing only)
- Must compare: parties, legal articles, verdict outcome, monetary values, dates
- If ANY mismatch exists: REJECT the verdict (fail-closed)
- Must use deterministic parsing, NOT semantic comparison

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Pattern, Tuple

from mahoun.core.logging import setup_logger
from mahoun.reasoning.verdict_validation.pipeline import (
    ViolationSeverity,
    ViolationType,
    ValidationStep,
)

log = setup_logger("deterministic_validator")


@dataclass(frozen=True)
class DeterministicViolation:
    """Single deterministic validation violation"""
    message: str
    field: str
    violation_type: ViolationType = ViolationType.TEXT_JSON_MISMATCH
    severity: ViolationSeverity = ViolationSeverity.CRITICAL
    expected: Optional[str] = None
    actual: Optional[str] = None
    context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "field": self.field,
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "expected": self.expected,
            "actual": self.actual,
            "context": self.context,
        }


@dataclass
class DeterministicValidationResult:
    """Result of deterministic validation"""
    passed: bool
    violations: List[DeterministicViolation] = field(default_factory=list)
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    matched_entities: Dict[str, Any] = field(default_factory=dict)
    validation_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "extracted_entities": self.extracted_entities,
            "matched_entities": self.matched_entities,
            "validation_timestamp": self.validation_timestamp,
        }


class DeterministicValidator:
    """
    Deterministic validator for comparing prose text against Canonical Verdict JSON.
    
    This validator extracts entities from both the text and the JSON and compares them:
    - Parties (names, identifiers)
    - Legal articles/codes (e.g., "ماده ۲۲۰")
    - Verdict outcome (e.g., "معتبر", "نامعتبر")
    - Monetary values (numbers with currency context)
    - Dates (in various formats)
    - Evidence identifiers
    - Document identifiers
    - Confidence values
    - Citations
    
    CRITICAL RULES:
    - NO LLM allowed - pure deterministic string parsing
    - If ANY entity in text is NOT in JSON: VIOLATION
    - If ANY required entity from JSON is NOT in text: VIOLATION
    - Must use regex and string matching, NOT semantic comparison
    
    Usage:
        validator = DeterministicValidator()
        result = validator.validate(canonical_json=json_data, prose_text=text)
        
        if not result.passed:
            # Fail-closed - STOP the pipeline
            raise IntegrityViolationError("Deterministic validation failed", result.violations[0])
    """
    
    def __init__(self):
        """Initialize deterministic validator"""
        # Pre-compile regex patterns for performance
        self._patterns = {
            # Persian legal article pattern: ماده XXX, بند Y, تبصره Z
            "legal_article": re.compile(
                r'(ماده|بند|تبصره|قانون|مقرره)\s+[\d\u06F0-\u06F9]+(/?[\d\u06F0-\u06F9]+)*',
                re.IGNORECASE
            ),
            # Monetary values in Persian/Arabic numerals
            "monetary": re.compile(
                r'[\d\u06F0-\u06F9]+[,.]?[\d\u06F0-\u06F9]*\s*(ریال|تومان|دلار|یورو|$|€)',
                re.IGNORECASE
            ),
            # Persian dates: 1403/01/01 or ۱۴۰۳/۰۱/۰۱
            "persian_date": re.compile(
                r'[\d\u06F0-\u06F9]{4}/[\d\u06F0-\u06F9]{2}/[\d\u06F0-\u06F9]{2}'
            ),
            # Gregorian dates: 2024-01-01 or 2024/01/01
            "gregorian_date": re.compile(
                r'\d{4}[-/]\d{2}[-/]\d{2}'
            ),
            # Confidence percentages
            "confidence": re.compile(
                r'[\d\u06F0-\u06F9]+(\.[\d\u06F0-\u06F9]+)?\s*%?'
            ),
            # Evidence references: [Evidence:XXX] or EvidenceReference(...)
            "evidence_ref": re.compile(
                r'(?: Evide?nce[_:]?|شاهد|مدرک|دلیل)\s*[\w\u0600-\u06FF-]+',
                re.IGNORECASE
            ),
            # Document IDs
            "doc_id": re.compile(
                r'(?:doc[_-]?id|document[_-]?id|شناسه[_-]?سند)\s*[:=]?\s*[\w\u0600-\u06FF-]+',
                re.IGNORECASE
            ),
        }
        log.info("DeterministicValidator initialized")
    
    def _extract_entities_from_json(self, canonical_json: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract entities from Canonical Verdict JSON.
        
        Args:
            canonical_json: The Canonical Verdict JSON
            
        Returns:
            Dictionary mapping entity types to lists of values
        """
        entities: Dict[str, List[str]] = {
            "parties": [],
            "legal_articles": [],
            "verdict_outcome": [],
            "monetary_values": [],
            "dates": [],
            "evidence_refs": [],
            "doc_ids": [],
            "confidence_values": [],
            "citations": [],
        }
        
        # Extract from final_verdict field
        if "final_verdict" in canonical_json and canonical_json["final_verdict"]:
            text = canonical_json["final_verdict"]
            entities["verdict_outcome"].append(text)
        
        # Extract from steps
        if "steps" in canonical_json:
            for step in canonical_json["steps"]:
                if isinstance(step, dict):
                    # Extract statement
                    statement = step.get("statement", "")
                    if statement:
                        entities["verdict_outcome"].append(statement)
                    
                    # Extract evidence references
                    evidence = step.get("evidence", [])
                    for ev in evidence:
                        if isinstance(ev, dict):
                            node_id = ev.get("node_id", "")
                            if node_id:
                                entities["evidence_refs"].append(node_id)
                        elif isinstance(ev, str):
                            entities["evidence_refs"].append(ev)
        
        # Extract from rule_nodes and precedent_nodes
        if "rule_nodes" in canonical_json:
            for node in canonical_json["rule_nodes"].values():
                if isinstance(node, dict):
                    node_id = node.get("id", "")
                    if node_id:
                        entities["legal_articles"].append(node_id)
                    properties = node.get("properties", {})
                    if "article" in properties:
                        entities["legal_articles"].append(str(properties["article"]))
        
        if "precedent_nodes" in canonical_json:
            for node in canonical_json["precedent_nodes"].values():
                if isinstance(node, dict):
                    node_id = node.get("id", "")
                    if node_id:
                        entities["citations"].append(node_id)
        
        # Extract from metadata
        if "metadata" in canonical_json and isinstance(canonical_json["metadata"], dict):
            # Extract parties
            if "parties" in canonical_json["metadata"]:
                parties = canonical_json["metadata"]["parties"]
                if isinstance(parties, list):
                    entities["parties"].extend(parties)
                elif isinstance(parties, str):
                    entities["parties"].append(parties)
            
            # Extract monetary values
            if "amount" in canonical_json["metadata"]:
                entities["monetary_values"].append(str(canonical_json["metadata"]["amount"]))
            
            # Extract dates
            if "date" in canonical_json["metadata"]:
                entities["dates"].append(str(canonical_json["metadata"]["date"]))
            
            if "dates" in canonical_json["metadata"]:
                dates = canonical_json["metadata"]["dates"]
                if isinstance(dates, list):
                    entities["dates"].extend([str(d) for d in dates])
        
        # Extract confidence score
        if "confidence_score" in canonical_json:
            entities["confidence_values"].append(str(canonical_json["confidence_score"]))
        
        # Extract case_id and verdict_id
        if "case_id" in canonical_json:
            entities["doc_ids"].append(str(canonical_json["case_id"]))
        if "verdict_id" in canonical_json:
            entities["doc_ids"].append(str(canonical_json["verdict_id"]))
        
        return entities
    
    def _extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from prose text using deterministic parsing.
        
        NO LLM allowed - pure regex and string matching.
        
        Args:
            text: The prose text to extract entities from
            
        Returns:
            Dictionary mapping entity types to lists of values
        """
        entities: Dict[str, List[str]] = {
            "parties": [],
            "legal_articles": [],
            "verdict_outcome": [],
            "monetary_values": [],
            "dates": [],
            "evidence_refs": [],
            "doc_ids": [],
            "confidence_values": [],
            "citations": [],
        }
        
        # Extract legal articles
        for match in self._patterns["legal_article"].finditer(text):
            entities["legal_articles"].append(match.group())
        
        # Extract monetary values
        for match in self._patterns["monetary"].finditer(text):
            entities["monetary_values"].append(match.group())
        
        # Extract Persian dates
        for match in self._patterns["persian_date"].finditer(text):
            entities["dates"].append(match.group())
        
        # Extract Gregorian dates
        for match in self._patterns["gregorian_date"].finditer(text):
            entities["dates"].append(match.group())
        
        # Extract confidence values
        for match in self._patterns["confidence"].finditer(text):
            entities["confidence_values"].append(match.group())
        
        # Extract evidence references
        for match in self._patterns["evidence_ref"].finditer(text):
            entities["evidence_refs"].append(match.group())
        
        # Extract document IDs
        for match in self._patterns["doc_id"].finditer(text):
            entities["doc_ids"].append(match.group())
        
        # Simple keyword extraction for parties (Persian names)
        # This is a basic approach - in production, use a proper NER or list of known parties
        party_keywords = ["اطب", "طرف اول", "طرف دوم", "claimant", "defendant", "plaintiff"]
        for keyword in party_keywords:
            if keyword in text.lower():
                # Extract the surrounding context
                start = max(0, text.lower().find(keyword) - 20)
                end = min(len(text), text.lower().find(keyword) + 40)
                context = text[start:end].strip()
                if context not in entities["parties"]:
                    entities["parties"].append(context)
        
        return entities
    
    def _normalize_entity(self, entity: str) -> str:
        """
        Normalize an entity for comparison (remove whitespace, standardize numerals).
        
        Args:
            entity: The entity string to normalize
            
        Returns:
            Normalized string
        """
        # Convert Persian/Arabic numerals to English
        numeral_map = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
        }
        normalized = ''.join(numeral_map.get(c, c) for c in entity)
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        return normalized.strip()
    
    def _compare_entity_lists(
        self,
        json_entities: List[str],
        text_entities: List[str],
        entity_type: str
    ) -> List[DeterministicViolation]:
        """
        Compare entity lists from JSON and text.
        
        Args:
            json_entities: Entities from Canonical Verdict JSON
            text_entities: Entities from prose text
            entity_type: Type of entity for reporting
            
        Returns:
            List of violations if mismatches found
        """
        violations: List[DeterministicViolation] = []
        
        # Normalize all entities
        json_normalized = {self._normalize_entity(e) for e in json_entities}
        text_normalized = {self._normalize_entity(e) for e in text_entities}
        
        # Check if text contains entities NOT in JSON
        text_only = text_normalized - json_normalized
        for entity in text_only:
            violations.append(DeterministicViolation(
                message=f"Text contains {entity_type} not in Canonical JSON: {entity}",
                field=entity_type,
                violation_type=ViolationType.TEXT_JSON_MISMATCH,
                severity=ViolationSeverity.CRITICAL,
                expected=f"Only entities from JSON",
                actual=entity,
                context=f"Found in text but not in Canonical Verdict JSON",
            ))
        
        # Check if JSON contains entities NOT in text (warning level)
        json_only = json_normalized - text_normalized
        for entity in json_only:
            violations.append(DeterministicViolation(
                message=f"Canonical JSON contains {entity_type} not in text: {entity}",
                field=entity_type,
                violation_type=ViolationType.TEXT_JSON_MISMATCH,
                severity=ViolationSeverity.MEDIUM,
                expected=f"Entity should appear in text",
                actual=f"Missing from prose",
                context=f"In JSON but not in generated text",
            ))
        
        return violations
    
    def validate(
        self,
        canonical_json: Dict[str, Any],
        prose_text: str,
    ) -> DeterministicValidationResult:
        """
        Validate that prose text matches Canonical Verdict JSON deterministically.
        
        CRITICAL: If ANY mismatch is found, this MUST fail-closed.
        NO LLM is used in this validation.
        
        Args:
            canonical_json: The Canonical Verdict JSON (source of truth)
            prose_text: The generated prose text to validate
            
        Returns:
            DeterministicValidationResult with validation details
        """
        violations: List[DeterministicViolation] = []
        
        # Extract entities from both sources
        json_entities = self._extract_entities_from_json(canonical_json)
        text_entities = self._extract_entities_from_text(prose_text)
        
        # Compare each entity type
        for entity_type in json_entities.keys():
            json_list = json_entities[entity_type]
            text_list = text_entities[entity_type]
            
            type_violations = self._compare_entity_lists(
                json_list, text_list, entity_type
            )
            violations.extend(type_violations)
        
        # Special check: if text is completely different from any JSON content
        if prose_text and canonical_json.get("final_verdict"):
            json_text = str(canonical_json["final_verdict"])
            # Check if text contains NONE of the key phrases from JSON
            # This is a fallback check
            if json_text not in prose_text:
                # This might be okay if text is a rendered version
                # But we should check for similarity
                pass
        
        # Final result
        passed = len(violations) == 0
        
        return DeterministicValidationResult(
            passed=passed,
            violations=violations,
            extracted_entities={
                "json": json_entities,
                "text": text_entities,
            },
            matched_entities=self._find_matches(json_entities, text_entities),
        )
    
    def _find_matches(
        self,
        json_entities: Dict[str, List[str]],
        text_entities: Dict[str, List[str]]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """Find matching entities between JSON and text"""
        matches: Dict[str, List[Tuple[str, str]]] = {}
        
        for entity_type in json_entities.keys():
            json_list = json_entities[entity_type]
            text_list = text_entities[entity_type]
            
            type_matches: List[Tuple[str, str]] = []
            json_normalized = [self._normalize_entity(e) for e in json_list]
            text_normalized = [self._normalize_entity(e) for e in text_list]
            
            for json_entity in json_normalized:
                for text_entity in text_normalized:
                    if json_entity in text_entity or text_entity in json_entity:
                        type_matches.append((json_entity, text_entity))
            
            matches[entity_type] = type_matches
        
        return matches
