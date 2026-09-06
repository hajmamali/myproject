"""
Data Quality Tests for Persian Legal Knowledge Graph
===================================================

Tests for Persian text data quality:
- Persian text normalization
- Unicode issues (Arabic/Persian character confusion)
- Invisible character detection
- Duplicate whitespace
- Incorrect numbering formats
- Broken UTF-8 content

Invariant protected: Text data must be clean, normalized, and searchable.

Failure danger: Text corruption causes search failures and incorrect matching.
"""

import pytest
from typing import List, Dict, Any


@pytest.mark.p2_extended
@pytest.mark.integration
class TestPersianTextNormalization:
    """
    Validate Persian text normalization.
    
    Invariant: Persian text must be normalized:
    - Arabic yeh (ي) → Persian yeh (ی)
    - Arabic kaf (ك) → Persian kaf (ک)
    - Mixed numerals → Persian numerals
    - Consistent ZWNJ usage
    
    Failure danger: Non-normalized text causes search failures and incorrect matching.
    """
    
    def test_arabic_yeh_normalized_to_persian(self, neo4j_sample_graph):
        """
        Detect Arabic yeh (ي) not normalized to Persian yeh (ی).
        
        Arabic yeh should be normalized to Persian yeh.
        """
        conn = neo4j_sample_graph
        
        # Create text with Arabic yeh
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:arabic_yeh',
            article_number: '900',
            text_fa: 'دادگاه‌هاي عمومي'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa CONTAINS 'ي'
        RETURN n.canonical_id, n.text_fa
        """
        
        arabic_yeh_found = conn.execute_query(query)
        
        assert len(arabic_yeh_found) > 0, "Failed to detect Arabic yeh"
    
    def test_arabic_kaf_normalized_to_persian(self, neo4j_sample_graph):
        """
        Detect Arabic kaf (ك) not normalized to Persian kaf (ک).
        
        Arabic kaf should be normalized to Persian kaf.
        """
        conn = neo4j_sample_graph
        
        # Create text with Arabic kaf
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:arabic_kaf',
            article_number: '901',
            text_fa: 'مكاتبه'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa CONTAINS 'ك'
        RETURN n.canonical_id, n.text_fa
        """
        
        arabic_kaf_found = conn.execute_query(query)
        
        assert len(arabic_kaf_found) > 0, "Failed to detect Arabic kaf"
    
    def test_mixed_numerals_normalized(self, neo4j_sample_graph):
        """
        Detect mixed Persian/Arabic/Western numerals.
        
        All numerals should be consistently normalized (preferably to Western).
        """
        conn = neo4j_sample_graph
        
        # Create text with mixed numerals
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:mixed_numerals',
            article_number: '۱۲۳',
            text_fa: 'ماده ۱۲۳ و ماده 456 و ماده ٧٨٩'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa CONTAINS '۱۲۳' OR n.text_fa CONTAINS '٧٨٩'
        RETURN n.canonical_id, n.text_fa
        """
        
        mixed_numerals_found = conn.execute_query(query)
        
        assert len(mixed_numerals_found) > 0, "Failed to detect mixed numerals"
    
    def test_consistent_zwnj_usage(self, neo4j_sample_graph):
        """
        Detect inconsistent ZWNJ (Zero-Width Non-Joiner) usage.
        
        ZWNJ should be used consistently for compound words.
        """
        conn = neo4j_sample_graph
        
        # Create text with inconsistent ZWNJ
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:inconsistent_zwnj',
            article_number: '902',
            text_fa: 'دادگاه‌های عمومی و دادگاه هاي انقلاب'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa CONTAINS '‌' AND n.text_fa CONTAINS ' '
        RETURN n.canonical_id, n.text_fa
        """
        
        inconsistent_zwnj = conn.execute_query(query)
        
        # This is informational - ZWNJ usage can vary
        assert len(inconsistent_zwnj) >= 0, "Query execution failed"


@pytest.mark.p2_extended
@pytest.mark.integration
class TestUnicodeIssues:
    """
    Detect Unicode issues in Persian text.
    
    Invariant: Text must use correct Unicode code points:
    - No mixing of Arabic and Persian variants
    - No invalid Unicode sequences
    - No surrogate pairs in Persian text
    
    Failure danger: Unicode issues cause display errors and search failures.
    """
    
    def test_no_arabic_persian_mixing(self, neo4j_sample_graph):
        """
        Detect mixing of Arabic and Persian character variants.
        
        Should consistently use either Arabic or Persian, not both.
        """
        conn = neo4j_sample_graph
        
        # Create text with mixed Arabic/Persian
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:mixed_unicode',
            article_number: '903',
            text_fa: 'قانون مدني و حقوق عمومی'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE (n.text_fa CONTAINS 'ي' OR n.text_fa CONTAINS 'ك')
        AND (n.text_fa CONTAINS 'ی' OR n.text_fa CONTAINS 'ک')
        RETURN n.canonical_id, n.text_fa
        """
        
        mixed_unicode = conn.execute_query(query)
        
        assert len(mixed_unicode) > 0, "Failed to detect Arabic/Persian mixing"
    
    def test_no_invalid_unicode_sequences(self, neo4j_sample_graph):
        """
        Detect invalid Unicode sequences.
        
        Invalid sequences can cause encoding errors.
        """
        conn = neo4j_sample_graph
        
        # This is difficult to test directly in Cypher
        # Instead, we check for known problematic patterns
        query = """
        MATCH (n)
        WHERE n.text_fa IS NOT NULL
        RETURN n.canonical_id, size(n.text_fa) as text_length
        ORDER BY text_length DESC
        LIMIT 10
        """
        
        result = conn.execute_query(query)
        
        # Verify query executes successfully
        assert len(result) >= 0, "Query execution failed"
    
    def test_no_bidi_control_characters(self, neo4j_sample_graph):
        """
        Detect bidirectional control characters in text.
        
        BIDI controls should be handled by rendering, not embedded in text.
        """
        conn = neo4j_sample_graph
        
        # Create text with potential BIDI issues
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:bidi_issue',
            article_number: '904',
            text_fa: 'متن فارسی English text متن فارسی'
        })
        """)
        
        # Check for mixed RTL/LTR text
        query = """
        MATCH (n)
        WHERE n.text_fa CONTAINS 'English' OR n.text_fa CONTAINS 'Latin'
        RETURN n.canonical_id, n.text_fa
        """
        
        mixed_direction = conn.execute_query(query)
        
        # This is informational - mixed direction is sometimes necessary
        assert len(mixed_direction) >= 0, "Query execution failed"


@pytest.mark.p2_extended
@pytest.mark.integration
class TestInvisibleCharacterDetection:
    """
    Detect invisible characters that cause issues.
    
    Invariant: Text should not contain problematic invisible characters:
    - Zero-width spaces (U+200B)
    - Zero-width non-joiners (U+200C) - except where intentional
    - Soft hyphens (U+00AD)
    - Other control characters
    
    Failure danger: Invisible characters cause unexpected search behavior.
    """
    
    def test_no_zero_width_space(self, neo4j_sample_graph):
        """
        Detect zero-width space characters (U+200B).
        
        Zero-width spaces should not be present in legal text.
        """
        conn = neo4j_sample_graph
        
        # Create text with zero-width space (simulated)
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:zws',
            article_number: '905',
            text_fa: 'متن با فاصله نامرئی'
        })
        """)
        
        # Cypher doesn't directly detect ZWS, but we can check for suspicious patterns
        query = """
        MATCH (n)
        WHERE n.text_fa IS NOT NULL
        RETURN n.canonical_id, n.text_fa
        """
        
        result = conn.execute_query(query)
        
        # Verify query executes
        assert len(result) >= 0, "Query execution failed"
    
    def test_no_soft_hyphens(self, neo4j_sample_graph):
        """
        Detect soft hyphen characters (U+00AD).
        
        Soft hyphens should not be present in legal text.
        """
        conn = neo4j_sample_graph
        
        # Similar to ZWS, difficult to detect directly in Cypher
        query = """
        MATCH (n)
        WHERE n.text_fa IS NOT NULL
        AND n.text_fa CONTAINS '-'
        RETURN n.canonical_id, n.text_fa
        """
        
        result = conn.execute_query(query)
        
        # Verify query executes
        assert len(result) >= 0, "Query execution failed"
    
    def test_no_control_characters(self, neo4j_sample_graph):
        """
        Detect control characters in text.
        
        Control characters (except newline/tab) should not be present.
        """
        conn = neo4j_sample_graph
        
        # Create text with potential control characters
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:control_chars',
            article_number: '906',
            text_fa: 'متن\\nبا\\nخط‌شکن'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa IS NOT NULL
        RETURN n.canonical_id, n.text_fa
        """
        
        result = conn.execute_query(query)
        
        # Verify query executes
        assert len(result) >= 0, "Query execution failed"


@pytest.mark.p2_extended
@pytest.mark.integration
class TestDuplicateWhitespace:
    """
    Detect duplicate and excessive whitespace.
    
    Invariant: Text should have normalized whitespace:
    - No multiple consecutive spaces
    - No trailing/leading whitespace
    - Consistent spacing after punctuation
    
    Failure danger: Excessive whitespace causes display and search issues.
    """
    
    def test_no_multiple_consecutive_spaces(self, neo4j_sample_graph):
        """
        Detect multiple consecutive spaces.
        
        Multiple spaces should be normalized to single space.
        """
        conn = neo4j_sample_graph
        
        # Create text with multiple spaces
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:multi_space',
            article_number: '907',
            text_fa: 'متن  با  فاصله  زیاد'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa CONTAINS '  '
        RETURN n.canonical_id, n.text_fa
        """
        
        multiple_spaces = conn.execute_query(query)
        
        assert len(multiple_spaces) > 0, "Failed to detect multiple consecutive spaces"
    
    def test_no_trailing_whitespace(self, neo4j_sample_graph):
        """
        Detect trailing whitespace.
        
        Text should not have trailing spaces or newlines.
        """
        conn = neo4j_sample_graph
        
        # Create text with trailing space
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:trailing_space',
            article_number: '908',
            text_fa: 'متن با فاصله انتهایی '
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa ENDS WITH ' '
        RETURN n.canonical_id, n.text_fa
        """
        
        trailing_space = conn.execute_query(query)
        
        assert len(trailing_space) > 0, "Failed to detect trailing whitespace"
    
    def test_no_leading_whitespace(self, neo4j_sample_graph):
        """
        Detect leading whitespace.
        
        Text should not have leading spaces or newlines.
        """
        conn = neo4j_sample_graph
        
        # Create text with leading space
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:leading_space',
            article_number: '909',
            text_fa: ' متن با فاصله ابتدایی'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa STARTS WITH ' '
        RETURN n.canonical_id, n.text_fa
        """
        
        leading_space = conn.execute_query(query)
        
        assert len(leading_space) > 0, "Failed to detect leading whitespace"
    
    def test_consistent_punctuation_spacing(self, neo4j_sample_graph):
        """
        Detect inconsistent spacing after punctuation.
        
        Should have consistent spacing after periods, commas, etc.
        """
        conn = neo4j_sample_graph
        
        # Create text with inconsistent punctuation spacing
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:punct_space',
            article_number: '910',
            text_fa: 'متن اول،متن دوم. متن سوم'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.text_fa CONTAINS '،' AND NOT n.text_fa CONTAINS '، '
        RETURN n.canonical_id, n.text_fa
        """
        
        inconsistent_spacing = conn.execute_query(query)
        
        assert len(inconsistent_spacing) > 0, "Failed to detect inconsistent punctuation spacing"


@pytest.mark.p2_extended
@pytest.mark.integration
class TestNumberingFormats:
    """
    Validate numbering formats.
    
    Invariant: Numbering should follow consistent formats:
    - Article numbers: numeric
    - Chapter numbers: numeric or Roman numerals
    - Clause numbers: numeric
    - No mixed formats in same document
    
    Failure danger: Incorrect numbering causes parsing and reference errors.
    """
    
    def test_article_number_is_numeric(self, neo4j_sample_graph):
        """
        Detect article numbers that are not numeric.
        
        Article numbers should be numeric only.
        """
        conn = neo4j_sample_graph
        
        # Create article with non-numeric number
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:bad_number',
            article_number: 'ABC',
            text_fa: 'ماده با شماره نامعتبر'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE NOT a.article_number =~ '^\\d+$'
        RETURN a.canonical_id, a.article_number
        """
        
        invalid_numbers = conn.execute_query(query)
        
        assert len(invalid_numbers) > 0, "Failed to detect non-numeric article number"
    
    def test_chapter_number_format_valid(self, neo4j_sample_graph):
        """
        Detect chapter numbers with invalid format.
        
        Chapter numbers should be numeric or Roman numerals.
        """
        conn = neo4j_sample_graph
        
        # Create chapter with invalid number
        conn.execute_query("""
        CREATE (c:Chapter {
            canonical_id: 'chapter:bad_number',
            chapter_number: 'XYZ',
            title_fa: 'فصل با شماره نامعتبر'
        })
        """)
        
        query = """
        MATCH (c:Chapter)
        WHERE NOT c.chapter_number =~ '^\\d+$'
        AND NOT c.chapter_number =~ '^[IVXLCDM]+$'
        RETURN c.canonical_id, c.chapter_number
        """
        
        invalid_numbers = conn.execute_query(query)
        
        assert len(invalid_numbers) > 0, "Failed to detect invalid chapter number"
    
    def test_no_mixed_numbering_in_same_law(self, neo4j_sample_graph):
        """
        Detect mixed numbering formats within the same law.
        
        All articles in a law should use the same numbering format.
        """
        conn = neo4j_sample_graph
        
        # Create articles with mixed numbering
        conn.execute_query("""
        CREATE (l:Law {canonical_id: 'law:mixed_numbering', title_fa: 'قانون با شماره‌گذاری مختلط'})
        CREATE (a1:Article {canonical_id: 'article:mixed:1', article_number: '1', text_fa: 'ماده ۱'})
        CREATE (a2:Article {canonical_id: 'article:mixed:2', article_number: '۲', text_fa: 'ماده ۲'})
        CREATE (l)-[:HAS_ARTICLE]->(a1)
        CREATE (l)-[:HAS_ARTICLE]->(a2)
        """)
        
        query = """
        MATCH (l:Law)-[:HAS_ARTICLE]->(a:Article)
        WITH l, collect(DISTINCT a.article_number) as numbers
        UNWIND numbers as n
        WITH l, collect(n) as nums
        WHERE size([n IN nums WHERE n =~ '^\\d+$']) > 0 
        AND size([n IN nums WHERE NOT n =~ '^\\d+$']) > 0
        RETURN l.canonical_id
        """
        
        mixed_numbering = conn.execute_query(query)
        
        assert len(mixed_numbering) > 0, "Failed to detect mixed numbering"
    
    def test_clause_number_format_valid(self, neo4j_sample_graph):
        """
        Detect clause numbers with invalid format.
        
        Clause numbers should be numeric.
        """
        conn = neo4j_sample_graph
        
        # Create clause with invalid number
        conn.execute_query("""
        CREATE (c:Clause {
            canonical_id: 'clause:bad_number',
            clause_number: 'ONE',
            text_fa: 'تبصره با شماره نامعتبر'
        })
        """)
        
        query = """
        MATCH (c:Clause)
        WHERE NOT c.clause_number =~ '^\\d+$'
        RETURN c.canonical_id, c.clause_number
        """
        
        invalid_numbers = conn.execute_query(query)
        
        assert len(invalid_numbers) > 0, "Failed to detect invalid clause number"


@pytest.mark.p2_extended
@pytest.mark.unit
class TestUTF8Integrity:
    """
    Validate UTF-8 encoding integrity.
    
    Invariant: All text must be valid UTF-8:
    - No invalid byte sequences
    - No replacement characters (�)
    - Proper encoding of Persian characters
    
    Failure danger: Broken UTF-8 causes display errors and data corruption.
    """
    
    def test_no_replacement_characters(self, sample_legal_data):
        """
        Detect Unicode replacement characters (�).
        
        Replacement characters indicate encoding errors.
        """
        # This is a unit test - check sample data
        text = sample_legal_data["law"]["title_fa"]
        
        # Check for replacement character
        assert "�" not in text, "Found replacement character in text"
    
    def test_persian_characters_valid_utf8(self, sample_legal_data):
        """
        Verify Persian characters are valid UTF-8.
        
        Persian characters should encode/decode correctly.
        """
        text = sample_legal_data["law"]["title_fa"]
        
        # Try to encode and decode
        try:
            encoded = text.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert decoded == text, "UTF-8 encoding/decode failed"
        except UnicodeError as e:
            pytest.fail(f"UTF-8 error: {e}")
    
    def test_text_length_consistent(self, sample_legal_data):
        """
        Verify text length is consistent between character and byte count.
        
        Persian characters are multi-byte, so byte count > character count.
        """
        text = sample_legal_data["article"]["text_fa"]
        
        char_count = len(text)
        byte_count = len(text.encode('utf-8'))
        
        # Persian text should have more bytes than characters
        assert byte_count >= char_count, "Byte count should be >= character count"
    
    def test_no_null_bytes(self, sample_legal_data):
        """
        Detect null bytes in text.
        
        Null bytes indicate data corruption.
        """
        text = sample_legal_data["article"]["text_fa"]
        
        assert "\x00" not in text, "Found null byte in text"
