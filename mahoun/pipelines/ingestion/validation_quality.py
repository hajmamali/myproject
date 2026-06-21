"""
Validation and Quality Checks for Ingestion
===========================================
Comprehensive validation and quality assessment for ingested documents.

Features:
- Field completeness validation
- Cross-reference validation
- Confidence scoring
- Quality metrics calculation
- Flagging low-quality documents
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from .minimal_verdict_parser import validate_verdict_struct

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of document validation"""
    is_valid: bool
    quality_score: float
    missing_fields: List[str] = field(default_factory=list)
    invalid_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


@dataclass
class QualityMetrics:
    """Quality metrics for a document"""
    completeness: float  # Percentage of required fields present
    accuracy: float  # Estimated accuracy based on validation
    consistency: float  # Internal consistency score
    overall_score: float
    flags: List[str] = field(default_factory=list)


class DocumentValidator:
    """
    Comprehensive document validator for verdicts and legal documents.
    
    Validates:
    - Required fields completeness
    - Data format correctness
    - Cross-reference consistency
    - Legal reference validity
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize Document Validator.
        
        Args:
            strict_mode: If True, enforce stricter validation rules
        """
        self.strict_mode = strict_mode
        logger.info(f"DocumentValidator initialized (strict_mode={strict_mode})")
    
    def validate_verdict(
        self,
        verdict_struct: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a verdict structure.
        
        Args:
            verdict_struct: Verdict structure dictionary
        
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True, quality_score=1.0)
        
        # Step 1: Basic structure validation
        basic_valid, errors = validate_verdict_struct(verdict_struct)
        if not basic_valid:
            result.is_valid = False
            result.errors.extend(errors)
        
        # Step 2: Field completeness check
        completeness_result = self._check_completeness(verdict_struct)
        result.missing_fields = completeness_result["missing"]
        result.quality_score *= completeness_result["score"]
        
        # Step 3: Format validation
        format_result = self._validate_formats(verdict_struct)
        result.invalid_fields = format_result["invalid"]
        if format_result["invalid"]:
            result.quality_score *= 0.9
        
        # Step 4: Cross-reference validation
        crossref_result = self._validate_cross_references(verdict_struct)
        result.warnings.extend(crossref_result["warnings"])
        if crossref_result["issues"]:
            result.quality_score *= 0.95
        
        # Step 5: Legal reference validation
        legal_result = self._validate_legal_references(verdict_struct)
        result.warnings.extend(legal_result["warnings"])
        
        # Step 6: Confidence calculation
        result.confidence_score = self._calculate_confidence(verdict_struct)
        
        # Overall validity
        if result.quality_score < 0.7 or result.errors:
            result.is_valid = False
        
        return result
    
    def _check_completeness(
        self,
        verdict_struct: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check field completeness"""
        
        missing: List[Any] = []
        total_fields = 0
        present_fields = 0
        
        # Required top-level fields
        required_fields = [
            "case_meta",
            "parties",
            "claims",
            "legal_references",
            "final_decision"
        ]
        
        for field in required_fields:
            total_fields += 1
            if field in verdict_struct and verdict_struct[field]:
                present_fields += 1
            else:
                missing.append(field)
        
        # Check nested required fields
        case_meta = verdict_struct.get("case_meta", {})
        if case_meta:
            nested_required = ["court_level", "case_type"]
            for field in nested_required:
                total_fields += 1
                if case_meta.get(field):
                    present_fields += 1
                else:
                    missing.append(f"case_meta.{field}")
        
        # Check parties
        parties = verdict_struct.get("parties", {})
        if parties:
            if not parties.get("third_party_objector") and not parties.get("respondents"):
                missing.append("parties.any_party")
        
        # Check claims
        claims = verdict_struct.get("claims", {})
        if claims:
            if not claims.get("main") or len(claims.get("main", [])) == 0:
                missing.append("claims.main")
        
        # Calculate completeness score
        completeness_score = present_fields / total_fields if total_fields > 0 else 0.0
        
        return {
            "missing": missing,
            "score": completeness_score,
            "present": present_fields,
            "total": total_fields
        }
    
    def _validate_formats(
        self,
        verdict_struct: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate data formats"""
        
        invalid: List[Any] = []
        # Validate dates
        case_meta = verdict_struct.get("case_meta", {})
        if case_meta:
            decision_date = case_meta.get("decision_date")
            if decision_date:
                if not self._is_valid_date_format(decision_date):
                    invalid.append("case_meta.decision_date (invalid format)")
        
        # Validate party names
        parties = verdict_struct.get("parties", {})
        for party_type in ["third_party_objector", "respondents"]:
            party_data = parties.get(party_type)
            if isinstance(party_data, list):
                for party in party_data:
                    if isinstance(party, dict) and "name" in party:
                        if not self._is_valid_name(party["name"]):
                            invalid.append(f"parties.{party_type}.name (invalid format)")
            elif isinstance(party_data, dict) and "name" in party_data:
                if not self._is_valid_name(party_data["name"]):
                    invalid.append(f"parties.{party_type}.name (invalid format)")
        
        # Validate legal references
        legal_refs = verdict_struct.get("legal_references", {})
        for ref_type in ["substantive_law", "procedural_law"]:
            refs = legal_refs.get(ref_type, [])
            for ref in refs:
                if not self._is_valid_legal_reference(ref):
                    invalid.append(f"legal_references.{ref_type} (invalid format)")
        
        return {"invalid": invalid}
    
    def _validate_cross_references(
        self,
        verdict_struct: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate cross-references between fields"""
        
        warnings: List[Any] = []
        issues: List[Any] = []
        # Check consistency between court level and procedure stage
        case_meta = verdict_struct.get("case_meta", {})
        court_level = case_meta.get("court_level", "")
        procedure_stage = case_meta.get("procedure_stage", "")
        
        if court_level and procedure_stage:
            if "تجدیدنظر" in court_level and procedure_stage != "تجدیدنظر":
                warnings.append("Court level suggests تجدیدنظر but procedure_stage doesn't match")
                issues.append("court_procedure_mismatch")
        
        # Check finality consistency
        is_final = case_meta.get("is_final", False)
        if is_final and "بدوی" in court_level:
            warnings.append("Verdict marked as final but court level is بدوی")
            issues.append("finality_inconsistency")
        
        # Check parties consistency
        parties = verdict_struct.get("parties", {})
        third_party = parties.get("third_party_objector")
        if third_party and not parties.get("respondents"):
            warnings.append("Third party objector present but no respondents found")
        
        return {"warnings": warnings, "issues": issues}
    
    def _validate_legal_references(
        self,
        verdict_struct: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate legal article references"""
        
        warnings: List[Any] = []
        legal_refs = verdict_struct.get("legal_references", {})
        substantive = legal_refs.get("substantive_law", [])
        procedural = legal_refs.get("procedural_law", [])
        
        # Common legal articles that should exist
        common_articles = ["ماده 10", "ماده 348", "ماده 358", "ماده 519"]
        
        all_refs = substantive + procedural
        refs_text = " ".join(all_refs)
        
        # Check if common procedural articles are present for appeal cases
        case_meta = verdict_struct.get("case_meta", {})
        if "تجدیدنظر" in case_meta.get("court_level", ""):
            if not any("348" in ref or "358" in ref for ref in all_refs):
                warnings.append("Appeal case but no common appeal articles (348, 358) found")
        
        return {"warnings": warnings}
    
    def _calculate_confidence(
        self,
        verdict_struct: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence score"""
        
        confidence = 1.0
        
        # Base confidence from parsing quality
        parsing_quality = verdict_struct.get("_parsing_quality", {})
        base_confidence = parsing_quality.get("confidence_score", 0.8)
        confidence = base_confidence
        
        # Adjust based on field completeness
        completeness = self._check_completeness(verdict_struct)
        confidence = (confidence + completeness["score"]) / 2
        
        # Adjust based on format validation
        format_result = self._validate_formats(verdict_struct)
        if format_result["invalid"]:
            confidence *= 0.95
        
        # Adjust based on cross-references
        crossref_result = self._validate_cross_references(verdict_struct)
        if crossref_result["issues"]:
            confidence *= 0.95
        
        return max(0.0, min(1.0, confidence))
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if date string is in valid format"""
        if not date_str:
            return False
        
        # Accept YYYY/MM/DD or YYYY-MM-DD
        patterns = [
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'\d{4}\.\d{1,2}\.\d{1,2}'
        ]
        
        return any(re.match(pattern, date_str) for pattern in patterns)
    
    def _is_valid_name(self, name: str) -> bool:
        """Check if name is valid"""
        if not name or len(name) < 2:
            return False
        
        # Should not contain only numbers or special chars
        if re.match(r'^[\d\s\.,]+$', name):
            return False
        
        return True
    
    def _is_valid_legal_reference(self, ref: str) -> bool:
        """Check if legal reference format is valid"""
        if not ref:
            return False
        
        # Should contain "ماده" and a number
        return "ماده" in ref and bool(re.search(r'\d+', ref))


class QualityAssessor:
    """
    Assesses overall quality of ingested documents.
    """
    
    def __init__(self):
        """Initialize Quality Assessor"""
        logger.info("QualityAssessor initialized")
    
    def assess_quality(
        self,
        verdict_struct: Dict[str, Any],
        validation_result: Optional[ValidationResult] = None
    ) -> QualityMetrics:
        """
        Assess overall quality of a document.
        
        Args:
            verdict_struct: Verdict structure
            validation_result: Optional validation result
        
        Returns:
            QualityMetrics with quality scores
        """
        # Get validation result if not provided
        if validation_result is None:
            validator = DocumentValidator()
            validation_result = validator.validate_verdict(verdict_struct)
        
        # Calculate metrics
        completeness = 1.0 - (len(validation_result.missing_fields) / 10.0)
        completeness = max(0.0, min(1.0, completeness))
        
        accuracy = validation_result.confidence_score
        
        consistency = self._calculate_consistency(verdict_struct)
        
        overall_score = (completeness * 0.3 + accuracy * 0.4 + consistency * 0.3)
        
        # Generate flags
        flags: List[Any] = []
        if overall_score < 0.7:
            flags.append("LOW_QUALITY")
        if validation_result.missing_fields:
            flags.append("INCOMPLETE")
        if validation_result.invalid_fields:
            flags.append("FORMAT_ISSUES")
        if validation_result.warnings:
            flags.append("WARNINGS")
        
        return QualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            overall_score=overall_score,
            flags=flags
        )
    
    def _calculate_consistency(self, verdict_struct: Dict[str, Any]) -> float:
        """Calculate internal consistency score"""
        consistency = 1.0
        
        case_meta = verdict_struct.get("case_meta", {})
        
        # Check court level and procedure stage consistency
        court_level = case_meta.get("court_level", "")
        procedure_stage = case_meta.get("procedure_stage", "")
        
        if court_level and procedure_stage:
            if "تجدیدنظر" in court_level and "تجدیدنظر" not in procedure_stage:
                consistency *= 0.9
        
        # Check parties consistency
        parties = verdict_struct.get("parties", {})
        if parties.get("third_party_objector") and not parties.get("respondents"):
            consistency *= 0.95
        
        return consistency


# Convenience functions
def validate_document(
    verdict_struct: Dict[str, Any],
    strict_mode: bool = False
) -> ValidationResult:
    """
    Validate a verdict document.
    
    Args:
        verdict_struct: Verdict structure dictionary
        strict_mode: Whether to use strict validation
    
    Returns:
        ValidationResult
    """
    validator = DocumentValidator(strict_mode=strict_mode)
    return validator.validate_verdict(verdict_struct)


def assess_document_quality(
    verdict_struct: Dict[str, Any],
    validation_result: Optional[ValidationResult] = None
) -> QualityMetrics:
    """
    Assess quality of a document.
    
    Args:
        verdict_struct: Verdict structure dictionary
        validation_result: Optional validation result
    
    Returns:
        QualityMetrics
    """
    assessor = QualityAssessor()
    return assessor.assess_quality(verdict_struct, validation_result)

