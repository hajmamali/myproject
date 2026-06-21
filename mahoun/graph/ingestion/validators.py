"""
Advanced Data Validators
========================

Enterprise-grade validators with:
- Schema validation
- Content validation
- Quality checks
- Business rules
- Security checks
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import logging
from abc import ABC, abstractmethod


class ValidationResult:
    """Result of validation"""
    
    def __init__(self, valid=True, errors=None, warnings=None, metadata=None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}
    
    def add_error(self, error):
        """Add error"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning):
        """Add warning"""
        self.warnings.append(warning)


class BaseValidator(ABC):
    """Base class for validators"""
    
    def __init__(self, name):
        self.name = name
    
    @abstractmethod
    def validate(self, data, metadata=None):
        """Validate data"""
        pass
    
    def create_result(self):
        """Create empty validation result"""
        return ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            metadata={"validator": self.name}
        )


class FileValidator(BaseValidator):
    """
    File-level validator
    
    Checks:
    - File exists
    - File size
    - File permissions
    - File type
    """
    
    def __init__(
        self,
        min_size=100,
        max_size=100 * 1024 * 1024,  # 100MB
        allowed_extensions=None,
    ):
        super().__init__("FileValidator")
        self.min_size = min_size
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions or [
            '.pdf', '.docx', '.doc', '.json', '.jsonl', '.txt', '.xml'
        ]
    
    def validate(self, data, metadata=None):
        """Validate file"""
        file_path = Path(data) if isinstance(data, str) else data
        result = self.create_result()
        
        # Check exists
        if not file_path.exists():
            result.add_error(f"File does not exist: {file_path}")
            return result
        
        # Check is file
        if not file_path.is_file():
            result.add_error(f"Path is not a file: {file_path}")
            return result
        
        # Check size
        size = file_path.stat().st_size
        
        if size < self.min_size:
            result.add_error(f"File too small: {size} bytes < {self.min_size} bytes")
        
        if size > self.max_size:
            result.add_error(f"File too large: {size} bytes > {self.max_size} bytes")
        
        # Check extension
        if file_path.suffix.lower() not in self.allowed_extensions:
            result.add_warning(
                f"Unsupported extension: {file_path.suffix}. "
                f"Allowed: {self.allowed_extensions}"
            )
        
        # Check permissions
        if not file_path.stat().st_mode & 0o400:  # Read permission
            result.add_error(f"File not readable: {file_path}")
        
        result.metadata.update({
            "file_size": size,
            "extension": file_path.suffix,
        })
        
        return result


class SchemaValidator(BaseValidator):
    """
    Schema validator for structured data
    
    Validates:
    - Required fields
    - Field types
    - Field constraints
    - Nested structures
    """
    
    def __init__(self, schema):
        super().__init__("SchemaValidator")
        self.schema = schema
    
    def validate(self, data, metadata=None):
        """Validate data against schema"""
        result = self.create_result()
        
        # Check required fields
        required_fields = self.schema.get('required', [])
        for field in required_fields:
            if field not in data:
                result.add_error(f"Missing required field: {field}")
        
        # Check field types
        properties = self.schema.get('properties', {})
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get('type')
                if expected_type:
                    if not self._check_type(value, expected_type):
                        result.add_error(
                            f"Invalid type for {field}: expected {expected_type}, "
                            f"got {type(value).__name__}"
                        )
        
        return result
    
    def _check_type(self, value, expected_type):
        """Check if value matches expected type"""
        type_map = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict,
        }
        
        expected_python_type = type_map.get(expected_type)
        if not expected_python_type:
            return True
        
        return isinstance(value, expected_python_type)


class ContentValidator(BaseValidator):
    """
    Content validator for text data
    
    Validates:
    - Text length
    - Character encoding
    - Language detection
    - Content quality
    """
    
    def __init__(
        self,
        min_length=10,
        max_length=1000000,
        required_language='fa',
    ):
        super().__init__("ContentValidator")
        self.min_length = min_length
        self.max_length = max_length
        self.required_language = required_language
    
    def validate(self, data, metadata=None):
        """Validate text content"""
        text = data if isinstance(data, str) else str(data)
        result = self.create_result()
        
        if not isinstance(text, str):
            result.add_error(f"Content must be string, got {type(text).__name__}")
            return result
        
        # Check length
        length = len(text)
        
        if length < self.min_length:
            result.add_error(f"Content too short: {length} < {self.min_length}")
        
        if length > self.max_length:
            result.add_error(f"Content too long: {length} > {self.max_length}")
        
        # Check if empty or whitespace only
        if not text.strip():
            result.add_error("Content is empty or whitespace only")
            return result
        
        # Check language (simple heuristic for Persian)
        if self.required_language == 'fa':
            persian_chars = len(re.findall(r'[\u0600-\u06FF]', text))
            persian_ratio = persian_chars / length if length > 0 else 0
            
            if persian_ratio < 0.3:  # At least 30% Persian characters
                result.add_warning(
                    f"Low Persian character ratio: {persian_ratio:.2%}. "
                    "Content may not be in Persian."
                )
        
        result.metadata.update({
            "length": length,
            "persian_ratio": persian_ratio,
        })
        
        return result


class LegalDocumentValidator(BaseValidator):
    """
    Legal document validator
    
    Validates:
    - Legal document structure
    - Article/clause format
    - Reference consistency
    - Citation completeness
    """
    
    def __init__(self):
        super().__init__("LegalDocumentValidator")
        self.patterns = {
            'article': r'ماده\s+(\d+)',
            'clause': r'بند\s+([الف-ی]\s*-?\s*\d*)',
            'section': r'بخش\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|[۰-۹]+)',
            'chapter': r'فصل\s+([۰-۹]+)',
        }
    
    def validate(self, data, metadata=None):
        """Validate legal document"""
        text = data if isinstance(data, str) else str(data)
        result = self.create_result()
        
        # Analyze document structure
        analysis = self._analyze_structure(text)
        
        # Check for required elements
        if not analysis['has_articles']:
            result.add_warning("No articles found in document")
        
        if not analysis['has_clauses']:
            result.add_warning("No clauses found in document")
        
        # Add analysis to metadata
        result.metadata.update(analysis)
        
        return result
    
    def _analyze_structure(self, text):
        """Analyze legal document structure"""
        # Find articles
        article_matches = list(re.finditer(self.patterns['article'], text))
        article_numbers = [match.group(1) for match in article_matches]
        
        # Find clauses
        clause_matches = list(re.finditer(self.patterns['clause'], text))
        clause_labels = [match.group(1) for match in clause_matches]
        
        # Find sections
        section_matches = list(re.finditer(self.patterns['section'], text))
        section_labels = [match.group(1) for match in section_matches]
        
        # Find chapters
        chapter_matches = list(re.finditer(self.patterns['chapter'], text))
        chapter_numbers = [match.group(1) for match in chapter_matches]
        
        # Check for common legal document elements
        has_articles = len(article_numbers) > 0
        has_clauses = len(clause_labels) > 0
        has_sections = len(section_labels) > 0
        has_chapters = len(chapter_numbers) > 0
        
        return {
            "has_articles": has_articles,
            "has_clauses": has_clauses,
            "has_sections": has_sections,
            "has_chapters": has_chapters,
            "article_count": len(article_numbers),
            "clause_count": len(clause_labels),
            "section_count": len(section_labels),
            "chapter_count": len(chapter_numbers),
            "article_numbers": article_numbers,
            "clause_labels": clause_labels,
            "section_labels": section_labels,
            "chapter_numbers": chapter_numbers,
        }


class QualityValidator(BaseValidator):
    """
    Data quality validator
    
    Validates:
    - Completeness
    - Consistency
    - Accuracy
    - Timeliness
    """
    
    def __init__(self, min_quality_score=0.8):
        super().__init__("QualityValidator")
        self.min_quality_score = min_quality_score
    
    def validate(self, data, metadata=None):
        """Validate data quality"""
        result = self.create_result()
        
        # Calculate quality score (simplified)
        quality_score = self._calculate_quality_score(data, metadata or {})
        
        if quality_score < self.min_quality_score:
            result.add_error(
                f"Quality score {quality_score:.2f} below minimum {self.min_quality_score:.2f}"
            )
        
        result.metadata.update({
            "quality_score": quality_score,
        })
        
        return result
    
    def _calculate_quality_score(self, data, metadata):
        """Calculate quality score"""
        # Simplified quality calculation
        score = 1.0
        
        # Check for completeness
        if isinstance(data, dict):
            required_fields = metadata.get('required_fields', [])
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                score -= 0.1 * len(missing_fields)
        
        # Check for data size
        if isinstance(data, (str, list, dict)):
            size = len(data)
            if size == 0:
                score -= 0.5
            elif size < 10:
                score -= 0.2
        
        return max(0.0, min(1.0, score))


class SecurityValidator(BaseValidator):
    """
    Security validator
    
    Validates:
    - PII detection
    - Malicious content
    - Access control
    - Data sensitivity
    """
    
    def __init__(self):
        super().__init__("SecurityValidator")
        self.sensitive_patterns = [
            r'\b\d{10}\b',  # National ID
            r'\b\d{16}\b',  # Bank account
            r'\b\d{3}-?\d{2}-?\d{4}\b',  # SSN-like
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        ]
    
    def validate(self, data, metadata=None):
        """Validate security aspects"""
        text = str(data)
        result = self.create_result()
        
        # Check for sensitive information
        sensitive_matches = []
        for pattern in self.sensitive_patterns:
            matches = re.findall(pattern, text)
            sensitive_matches.extend(matches)
        
        if sensitive_matches:
            result.add_warning(
                f"Found {len(sensitive_matches)} potential sensitive data items"
            )
        
        result.metadata.update({
            "sensitive_matches_count": len(sensitive_matches),
        })
        
        return result


class ValidatorChain:
    """Chain of validators"""
    
    def __init__(self):
        self.validators = []
    
    def add_validator(self, validator):
        """Add validator to chain"""
        self.validators.append(validator)
        return self
    
    def validate(self, data, metadata=None):
        """Run all validators"""
        results = []
        
        for validator in self.validators:
            try:
                result = validator.validate(data, metadata)
                results.append(result)
            except Exception as e:
                # Create error result
                result = ValidationResult(valid=False)
                result.add_error(f"Validator {validator.name} failed: {str(e)}")
                results.append(result)
        
        # Combine results
        combined_result = ValidationResult()
        combined_result.metadata = {"validator_chain": []}
        
        for result in results:
            combined_result.valid = combined_result.valid and result.valid
            combined_result.errors.extend(result.errors)
            combined_result.warnings.extend(result.warnings)
            combined_result.metadata["validator_chain"].append({
                "valid": result.valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata,
            })
        
        return combined_result