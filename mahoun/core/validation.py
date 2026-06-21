"""
Input Validation and Sanitization
==================================
Comprehensive input validation for MAHOUN platform.

Requirements:
- Validate all inputs at API boundary (Req 10.1)
- Use Pydantic for structured validation (Req 10.2)
- Reject invalid inputs with clear errors (Req 10.3)
- Sanitize string inputs to prevent injection (Req 10.4)
"""

import re
import html
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field, field_validator, model_validator
from mahoun.core.exceptions import ValidationError


# =============================================================================
# String Sanitization
# =============================================================================

class StringSanitizer:
    """
    Sanitize string inputs to prevent injection attacks.
    
    Protections:
    - HTML/XSS injection
    - SQL injection patterns
    - Command injection
    - Path traversal
    - Null bytes
    """
    
    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"('.*--)",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",
        r"\$\{.*\}",
        r"\$\(.*\)",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.",
        r"~\/",
    ]
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Escape HTML special characters.
        
        Prevents XSS attacks by converting < > & " ' to HTML entities.
        """
        return html.escape(text, quote=True)
    
    @staticmethod
    def remove_null_bytes(text: str) -> str:
        """Remove null bytes that can cause security issues."""
        return text.replace('\x00', '')
    
    @staticmethod
    def check_sql_injection(text: str) -> bool:
        """
        Check if text contains SQL injection patterns.
        
        Returns True if suspicious patterns found.
        """
        text_upper = text.upper()
        for pattern in StringSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def check_command_injection(text: str) -> bool:
        """
        Check if text contains command injection patterns.
        
        Returns True if suspicious patterns found.
        """
        for pattern in StringSanitizer.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text):
                return True
        return False
    
    @staticmethod
    def check_path_traversal(text: str) -> bool:
        """
        Check if text contains path traversal patterns.
        
        Returns True if suspicious patterns found.
        """
        for pattern in StringSanitizer.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text):
                return True
        return False
    
    @classmethod
    def sanitize(
        cls,
        text: str,
        max_length: Optional[int] = None,
        allow_html: bool = False,
        check_injections: bool = True
    ) -> str:
        """
        Comprehensive string sanitization.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length (None = no limit)
            allow_html: If False, escape HTML characters
            check_injections: If True, check for injection patterns
        
        Returns:
            Sanitized text
        
        Raises:
            ValidationError: If dangerous patterns detected
        """
        if not isinstance(text, str):
            raise ValidationError(f"Expected string, got {type(text).__name__}")
        
        # Remove null bytes
        text = cls.remove_null_bytes(text)
        
        # Check length
        if max_length and len(text) > max_length:
            raise ValidationError(
                f"Text too long: {len(text)} characters (max: {max_length})"
            )
        
        # Check for injection patterns
        if check_injections:
            if cls.check_command_injection(text):
                raise ValidationError("Potential command injection detected")
            
            if cls.check_sql_injection(text):
                raise ValidationError("Potential SQL injection detected")
            
            if cls.check_path_traversal(text):
                raise ValidationError("Potential path traversal detected")
        
        # Escape HTML if needed
        if not allow_html:
            text = cls.sanitize_html(text)
        
        return text


# =============================================================================
# Validated String Types
# =============================================================================

class SafeString(BaseModel):
    """
    A validated and sanitized string.
    
    Use this for user inputs that need sanitization.
    """
    value: str = Field(..., min_length=1, max_length=10000)
    
    @field_validator('value')
    @classmethod
    def sanitize_value(cls, v: str) -> str:
        """Sanitize the string value."""
        return StringSanitizer.sanitize(
            v,
            max_length=10000,
            allow_html=False,
            check_injections=True
        )


class SafeQuery(BaseModel):
    """
    A validated search query string.
    
    More permissive than SafeString but still protected.
    """
    value: str = Field(..., min_length=1, max_length=2000)
    
    @field_validator('value')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize query string."""
        # Queries can contain special chars but not injections
        return StringSanitizer.sanitize(
            v,
            max_length=2000,
            allow_html=False,
            check_injections=True
        )


class SafeFilename(BaseModel):
    """
    A validated filename.
    
    Prevents path traversal and dangerous characters.
    """
    value: str = Field(..., min_length=1, max_length=255)
    
    @field_validator('value')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename."""
        # Remove null bytes
        v = StringSanitizer.remove_null_bytes(v)
        
        # Check for path traversal
        if StringSanitizer.check_path_traversal(v):
            raise ValidationError("Invalid filename: path traversal detected")
        
        # Check for dangerous characters
        if re.search(r'[<>:"|?*\x00-\x1f]', v):
            raise ValidationError("Invalid filename: contains forbidden characters")
        
        # Must not start with dot (hidden files)
        if v.startswith('.'):
            raise ValidationError("Invalid filename: cannot start with dot")
        
        return v


class SafeDocumentId(BaseModel):
    """
    A validated document ID.
    
    Must be alphanumeric with hyphens/underscores only.
    """
    value: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('value')
    @classmethod
    def validate_doc_id(cls, v: str) -> str:
        """Validate document ID."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValidationError(
                "Invalid document ID: must contain only alphanumeric, hyphens, underscores"
            )
        return v


# =============================================================================
# Validated Request Models
# =============================================================================

class ValidatedSearchRequest(BaseModel):
    """
    Validated search request.
    
    Ensures query is safe and parameters are within bounds.
    """
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)
    
    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize search query."""
        return StringSanitizer.sanitize(v, max_length=2000)


class ValidatedDocumentRequest(BaseModel):
    """
    Validated document ingestion request.
    
    Ensures all fields are safe and within limits.
    """
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=1_000_000)  # 1MB text
    doc_type: str = Field(..., min_length=1, max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    
    @field_validator('title', 'doc_type')
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        """Sanitize string fields."""
        return StringSanitizer.sanitize(v, max_length=500)
    
    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Sanitize content (allow more characters)."""
        # Content can be longer but still check for injections
        v = StringSanitizer.remove_null_bytes(v)
        if len(v) > 1_000_000:
            raise ValidationError("Content too large (max 1MB)")
        return v
    
    @model_validator(mode='after')
    def validate_metadata(self) -> 'ValidatedDocumentRequest':
        """Validate metadata dictionary."""
        if self.metadata:
            # Limit metadata size
            if len(self.metadata) > 50:
                raise ValidationError("Too many metadata fields (max 50)")
            
            # Validate each key and value
            for key, value in self.metadata.items():
                if not isinstance(key, str):
                    raise ValidationError(f"Metadata key must be string: {key}")
                
                if len(key) > 100:
                    raise ValidationError(f"Metadata key too long: {key}")
                
                # Sanitize string values
                if isinstance(value, str):
                    if len(value) > 1000:
                        raise ValidationError(f"Metadata value too long for key: {key}")
                    self.metadata[key] = StringSanitizer.sanitize(value, max_length=1000)
        
        return self


class ValidatedFileUpload(BaseModel):
    """
    Validated file upload request.
    
    Ensures filename and file type are safe.
    """
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    size_bytes: int = Field(..., ge=1, le=100_000_000)  # Max 100MB
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename."""
        return SafeFilename(value=v).value
    
    @field_validator('content_type')
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type."""
        # Allow only safe content types
        allowed_types = {
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/markdown',
            'application/json',
        }
        
        if v not in allowed_types:
            raise ValidationError(f"Unsupported content type: {v}")
        
        return v


# =============================================================================
# Validation Utilities
# =============================================================================

def validate_and_sanitize_dict(
    data: Dict[str, Any],
    max_depth: int = 5,
    current_depth: int = 0
) -> Dict[str, Any]:
    """
    Recursively validate and sanitize a dictionary.
    
    Args:
        data: Dictionary to sanitize
        max_depth: Maximum nesting depth
        current_depth: Current recursion depth
    
    Returns:
        Sanitized dictionary
    
    Raises:
        ValidationError: If validation fails
    """
    if current_depth > max_depth:
        raise ValidationError(f"Dictionary nesting too deep (max: {max_depth})")
    
    sanitized = {}
    
    for key, value in data.items():
        # Validate key
        if not isinstance(key, str):
            raise ValidationError(f"Dictionary key must be string: {key}")
        
        if len(key) > 100:
            raise ValidationError(f"Dictionary key too long: {key}")
        
        # Sanitize key
        safe_key = StringSanitizer.sanitize(key, max_length=100)
        
        # Sanitize value based on type
        if isinstance(value, str):
            sanitized[safe_key] = StringSanitizer.sanitize(value, max_length=10000)
        elif isinstance(value, dict):
            sanitized[safe_key] = validate_and_sanitize_dict(
                value,
                max_depth=max_depth,
                current_depth=current_depth + 1
            )
        elif isinstance(value, list):
            sanitized[safe_key] = [
                StringSanitizer.sanitize(item, max_length=10000)
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            # Numbers, booleans, None are safe
            sanitized[safe_key] = value
    
    return sanitized


def validate_list_of_strings(
    items: List[str],
    max_items: int = 100,
    max_length: int = 1000
) -> List[str]:
    """
    Validate and sanitize a list of strings.
    
    Args:
        items: List of strings to validate
        max_items: Maximum number of items
        max_length: Maximum length per item
    
    Returns:
        Sanitized list
    
    Raises:
        ValidationError: If validation fails
    """
    if len(items) > max_items:
        raise ValidationError(f"Too many items: {len(items)} (max: {max_items})")
    
    return [
        StringSanitizer.sanitize(item, max_length=max_length)
        for item in items
    ]
