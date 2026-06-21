"""
Unit Tests for Input Validation
================================
Fast unit tests for validation module.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from mahoun.core.validation import (
    StringSanitizer,
    SafeString,
    SafeQuery,
    SafeFilename,
    SafeDocumentId,
    ValidatedSearchRequest,
    ValidatedDocumentRequest,
    ValidatedFileUpload,
    validate_and_sanitize_dict,
    validate_list_of_strings,
)
from mahoun.core.exceptions import ValidationError


# =============================================================================
# StringSanitizer Tests
# =============================================================================

def test_sql_injection_detected():
    """Test SQL injection patterns are detected."""
    injections = [
        "'; DROP TABLE users--",
        "1' OR '1'='1",
        "admin'--",
        "' UNION SELECT * FROM passwords--",
    ]
    
    for injection in injections:
        assert StringSanitizer.check_sql_injection(injection), \
            f"SQL injection not detected: {injection}"
        
        with pytest.raises(ValidationError, match="injection"):
            StringSanitizer.sanitize(injection, check_injections=True)


def test_command_injection_detected():
    """Test command injection patterns are detected."""
    injections = [
        "; rm -rf /",
        "| cat /etc/passwd",
        "$(whoami)",
        "`id`",
        "${USER}",
    ]
    
    for injection in injections:
        assert StringSanitizer.check_command_injection(injection), \
            f"Command injection not detected: {injection}"
        
        with pytest.raises(ValidationError, match="injection"):
            StringSanitizer.sanitize(injection, check_injections=True)


def test_path_traversal_detected():
    """Test path traversal patterns are detected."""
    traversals = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "~/secret",
        "../../config",
    ]
    
    for traversal in traversals:
        assert StringSanitizer.check_path_traversal(traversal), \
            f"Path traversal not detected: {traversal}"
        
        with pytest.raises(ValidationError, match="traversal"):
            StringSanitizer.sanitize(traversal, check_injections=True)


def test_html_escaped():
    """Test HTML special characters are escaped."""
    html = "<script>alert('XSS')</script>"
    escaped = StringSanitizer.sanitize_html(html)
    
    assert '&lt;' in escaped
    assert '&gt;' in escaped
    assert '<script>' not in escaped


def test_null_bytes_removed():
    """Test null bytes are removed."""
    text = "hello\x00world"
    sanitized = StringSanitizer.remove_null_bytes(text)
    
    assert sanitized == "helloworld"
    assert '\x00' not in sanitized


def test_safe_strings_accepted():
    """Test safe strings pass validation."""
    safe_strings = [
        "Hello World",
        "Test 123",
        "Valid-text_here",
        "مرحبا",  # Persian text
    ]
    
    for text in safe_strings:
        sanitized = StringSanitizer.sanitize(text, max_length=1000)
        assert isinstance(sanitized, str)


def test_length_limit_enforced():
    """Test length limits are enforced."""
    long_text = "a" * 101
    
    with pytest.raises(ValidationError, match="too long"):
        StringSanitizer.sanitize(long_text, max_length=100)


# =============================================================================
# Validated Types Tests
# =============================================================================

def test_safe_string_valid():
    """Test SafeString accepts valid input."""
    safe = SafeString(value="Valid text")
    assert safe.value == "Valid text"


def test_safe_string_too_long():
    """Test SafeString rejects too long input."""
    with pytest.raises((ValidationError, PydanticValidationError)):
        SafeString(value="a" * 10001)


def test_safe_query_valid():
    """Test SafeQuery accepts valid queries."""
    query = SafeQuery(value="search term")
    assert query.value == "search term"


def test_safe_filename_valid():
    """Test SafeFilename accepts valid filenames."""
    filename = SafeFilename(value="document.pdf")
    assert filename.value == "document.pdf"


def test_safe_filename_rejects_traversal():
    """Test SafeFilename rejects path traversal."""
    with pytest.raises((ValidationError, PydanticValidationError)):
        SafeFilename(value="../etc/passwd")


def test_safe_filename_rejects_hidden():
    """Test SafeFilename rejects hidden files."""
    with pytest.raises((ValidationError, PydanticValidationError)):
        SafeFilename(value=".hidden")


def test_safe_document_id_valid():
    """Test SafeDocumentId accepts valid IDs."""
    doc_id = SafeDocumentId(value="doc-123_abc")
    assert doc_id.value == "doc-123_abc"


def test_safe_document_id_rejects_special_chars():
    """Test SafeDocumentId rejects special characters."""
    with pytest.raises((ValidationError, PydanticValidationError)):
        SafeDocumentId(value="doc@123")


# =============================================================================
# Request Validation Tests
# =============================================================================

def test_validated_search_request_valid():
    """Test ValidatedSearchRequest accepts valid input."""
    request = ValidatedSearchRequest(
        query="test query",
        limit=10,
        offset=0
    )
    
    assert request.query == "test query"
    assert request.limit == 10
    assert request.offset == 0


def test_validated_search_request_defaults():
    """Test ValidatedSearchRequest uses defaults."""
    request = ValidatedSearchRequest(query="test")
    
    assert request.limit == 10
    assert request.offset == 0


def test_validated_search_request_rejects_invalid_limit():
    """Test ValidatedSearchRequest rejects invalid limits."""
    with pytest.raises(PydanticValidationError):
        ValidatedSearchRequest(query="test", limit=0)
    
    with pytest.raises(PydanticValidationError):
        ValidatedSearchRequest(query="test", limit=101)


def test_validated_document_request_valid():
    """Test ValidatedDocumentRequest accepts valid input."""
    request = ValidatedDocumentRequest(
        title="Test Document",
        content="Document content here",
        doc_type="legal"
    )
    
    assert request.title == "Test Document"
    assert request.content == "Document content here"
    assert request.doc_type == "legal"


def test_validated_document_request_with_metadata():
    """Test ValidatedDocumentRequest accepts metadata."""
    request = ValidatedDocumentRequest(
        title="Test",
        content="Content",
        doc_type="test",
        metadata={"key": "value"}
    )
    
    assert request.metadata == {"key": "value"}


def test_validated_document_request_rejects_too_many_metadata():
    """Test ValidatedDocumentRequest rejects too many metadata fields."""
    metadata = {f"key_{i}": f"value_{i}" for i in range(51)}
    
    with pytest.raises((ValidationError, PydanticValidationError)):
        ValidatedDocumentRequest(
            title="Test",
            content="Content",
            doc_type="test",
            metadata=metadata
        )


def test_validated_file_upload_valid():
    """Test ValidatedFileUpload accepts valid input."""
    upload = ValidatedFileUpload(
        filename="document.pdf",
        content_type="application/pdf",
        size_bytes=1000
    )
    
    assert upload.filename == "document.pdf"
    assert upload.content_type == "application/pdf"
    assert upload.size_bytes == 1000


def test_validated_file_upload_rejects_invalid_type():
    """Test ValidatedFileUpload rejects unsupported types."""
    with pytest.raises((ValidationError, PydanticValidationError)):
        ValidatedFileUpload(
            filename="file.exe",
            content_type="application/x-executable",
            size_bytes=1000
        )


def test_validated_file_upload_rejects_too_large():
    """Test ValidatedFileUpload rejects files that are too large."""
    with pytest.raises(PydanticValidationError):
        ValidatedFileUpload(
            filename="huge.pdf",
            content_type="application/pdf",
            size_bytes=200_000_000  # 200MB
        )


# =============================================================================
# Utility Function Tests
# =============================================================================

def test_validate_list_of_strings():
    """Test validate_list_of_strings sanitizes all items."""
    items = ["item1", "item2", "item3"]
    sanitized = validate_list_of_strings(items)
    
    assert len(sanitized) == 3
    assert all(isinstance(item, str) for item in sanitized)


def test_validate_list_rejects_too_many():
    """Test validate_list_of_strings rejects too many items."""
    items = [f"item_{i}" for i in range(101)]
    
    with pytest.raises(ValidationError, match="Too many items"):
        validate_list_of_strings(items, max_items=100)


def test_validate_dict():
    """Test validate_and_sanitize_dict sanitizes all values."""
    data = {
        "key1": "value1",
        "key2": 123,
        "key3": True,
    }
    
    sanitized = validate_and_sanitize_dict(data)
    
    assert len(sanitized) == 3
    assert sanitized["key1"] == "value1"
    assert sanitized["key2"] == 123
    assert sanitized["key3"] is True


def test_validate_dict_nested():
    """Test validate_and_sanitize_dict handles nested dicts."""
    data = {
        "outer": {
            "inner": "value"
        }
    }
    
    sanitized = validate_and_sanitize_dict(data)
    
    assert sanitized["outer"]["inner"] == "value"


def test_validate_dict_rejects_too_deep():
    """Test validate_and_sanitize_dict rejects too deep nesting."""
    # Create deeply nested dict (7 levels)
    data = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {
                        "level5": {
                            "level6": {
                                "level7": "value"
                            }
                        }
                    }
                }
            }
        }
    }
    
    with pytest.raises(ValidationError, match="too deep"):
        validate_and_sanitize_dict(data, max_depth=5)


# =============================================================================
# Integration Tests
# =============================================================================

def test_end_to_end_search_validation():
    """Test end-to-end search request validation."""
    # Valid request
    request = ValidatedSearchRequest(
        query="legal document search",
        limit=20,
        offset=10
    )
    
    assert request.query == "legal document search"
    assert 1 <= request.limit <= 100
    assert request.offset >= 0


def test_end_to_end_document_validation():
    """Test end-to-end document validation."""
    # Valid document
    request = ValidatedDocumentRequest(
        title="Contract Agreement",
        content="This is a legal contract...",
        doc_type="contract",
        metadata={
            "date": "2024-01-01",
            "parties": "Company A, Company B"
        }
    )
    
    assert request.title == "Contract Agreement"
    assert len(request.content) > 0
    assert request.metadata is not None


def test_injection_attack_prevented():
    """Test that injection attacks are prevented."""
    attacks = [
        "'; DROP TABLE users--",
        "; rm -rf /",
        "../../../etc/passwd",
        "<script>alert(1)</script>",
    ]
    
    for attack in attacks:
        with pytest.raises((ValidationError, PydanticValidationError)):
            ValidatedSearchRequest(query=attack)
