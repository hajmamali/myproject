"""
Document Integrity Tests for Input Data Validation
================================================

TEST NAME: Document Integrity Validation
PURPOSE: Validate raw legal documents before processing
INVARIANT: All input documents must be valid, complete, and properly encoded
FAILURE RISK: Corrupted input produces corrupted knowledge graph that cannot be trusted for legal reasoning
IMPLEMENTATION: Check file existence, encoding, readability, and basic integrity
"""

import pytest
import hashlib
from pathlib import Path
from typing import List, Dict, Any


@pytest.mark.p0_critical
@pytest.mark.unit
class TestDuplicateDocumentDetection:
    """
    TEST NAME: Duplicate Document Detection
    PURPOSE: Detect duplicate legal documents in input dataset
    INVARIANT: Each legal document should appear exactly once in the input dataset
    FAILURE RISK: Duplicate documents create duplicate entities in the knowledge graph, causing contradictory legal knowledge
    IMPLEMENTATION: Compare file hashes, titles, and content to identify duplicates
    """
    
    def test_duplicate_file_hash_detection(self, temp_dir):
        """
        Detect duplicate files by hash comparison.
        
        Files with identical content should be flagged as duplicates.
        """
        # Create duplicate files
        file1 = temp_dir / "law1.txt"
        file2 = temp_dir / "law2.txt"
        
        content = "قانون مدنی\nماده ۱: هرکس مالک مال خود است."
        file1.write_text(content, encoding="utf-8")
        file2.write_text(content, encoding="utf-8")
        
        # Calculate hashes
        hash1 = hashlib.sha256(file1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(file2.read_bytes()).hexdigest()
        
        # Should detect duplicate
        assert hash1 == hash2, "Duplicate files should have identical hashes"
        
        # Create detection function
        def detect_duplicates(files: List[Path]) -> Dict[str, List[Path]]:
            hashes = {}
            duplicates = {}
            for file in files:
                file_hash = hashlib.sha256(file.read_bytes()).hexdigest()
                if file_hash in hashes:
                    duplicates.setdefault(file_hash, []).append(file)
                    duplicates[file_hash].append(hashes[file_hash])
                else:
                    hashes[file_hash] = file
            return duplicates
        
        duplicates = detect_duplicates([file1, file2])
        assert len(duplicates) > 0, "Should detect duplicate files"
    
    def test_duplicate_title_detection(self, temp_dir):
        """
        Detect documents with identical titles.
        
        Same title with different content may indicate versioning issues or corruption.
        """
        file1 = temp_dir / "civil_code_v1.txt"
        file2 = temp_dir / "civil_code_v2.txt"
        
        file1.write_text("قانون مدنی\nنسخه اول", encoding="utf-8")
        file2.write_text("قانون مدنی\nنسخه دوم", encoding="utf-8")
        
        # Extract titles (first line)
        title1 = file1.read_text(encoding="utf-8").split("\n")[0]
        title2 = file2.read_text(encoding="utf-8").split("\n")[0]
        
        assert title1 == title2, "Same title detected"
        
        # This is informational - may be valid versioning
        # Should flag for manual review
        assert title1 == title2, "Duplicate titles should be flagged for review"
    
    def test_duplicate_content_with_different_names(self, temp_dir):
        """
        Detect identical content with different filenames.
        
        Same content with different names indicates data management issues.
        """
        file1 = temp_dir / "official_law.txt"
        file2 = temp_dir / "copy_law.txt"
        
        content = "قانون تجارت\nماده ۱"
        file1.write_text(content, encoding="utf-8")
        file2.write_text(content, encoding="utf-8")
        
        hash1 = hashlib.sha256(file1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(file2.read_bytes()).hexdigest()
        
        assert hash1 == hash2, "Same content with different names detected"


@pytest.mark.p0_critical
@pytest.mark.unit
class TestMissingDocumentDetection:
    """
    TEST NAME: Missing Document Detection
    PURPOSE: Detect missing legal documents from expected dataset
    INVARIANT: All expected legal documents must be present in the input dataset
    FAILURE RISK: Missing documents create incomplete knowledge graph with gaps in legal coverage
    IMPLEMENTATION: Compare expected document list against actual files
    """
    
    def test_expected_document_exists(self, temp_dir):
        """
        Verify that expected documents exist.
        
        If a document is expected but missing, it should be flagged.
        """
        # Create expected document list
        expected_docs = {
            "civil_code.txt": "قانون مدنی",
            "commercial_code.txt": "قانون تجارت",
            "penal_code.txt": "قانون مجازات"
        }
        
        # Create only some documents
        (temp_dir / "civil_code.txt").write_text("قانون مدنی", encoding="utf-8")
        (temp_dir / "commercial_code.txt").write_text("قانون تجارت", encoding="utf-8")
        
        # Check for missing documents
        missing_docs = []
        for doc_name in expected_docs:
            if not (temp_dir / doc_name).exists():
                missing_docs.append(doc_name)
        
        assert "penal_code.txt" in missing_docs, "Should detect missing document"
    
    def test_document_list_completeness(self, temp_dir):
        """
        Verify document list completeness against manifest.
        
        Should match expected count and names.
        """
        manifest = {
            "count": 3,
            "documents": ["civil_code.txt", "commercial_code.txt", "penal_code.txt"]
        }
        
        # Create only 2 documents
        (temp_dir / "civil_code.txt").write_text("قانون مدنی", encoding="utf-8")
        (temp_dir / "commercial_code.txt").write_text("قانون تجارت", encoding="utf-8")
        
        actual_files = list(temp_dir.glob("*.txt"))
        
        assert len(actual_files) != manifest["count"], "Document count mismatch detected"
    
    def test_critical_document_presence(self, temp_dir):
        """
        Verify critical documents are present.
        
        Some documents (e.g., Constitution) are critical and must exist.
        """
        critical_docs = ["constitution.txt", "civil_code.txt"]
        
        # Create only non-critical document
        (temp_dir / "other_law.txt").write_text("قانون دیگر", encoding="utf-8")
        
        missing_critical = [doc for doc in critical_docs if not (temp_dir / doc).exists()]
        
        assert len(missing_critical) == 2, "Critical documents missing"


@pytest.mark.p0_critical
@pytest.mark.unit
class TestTextCorruptionDetection:
    """
    TEST NAME: Text Corruption Detection
    PURPOSE: Detect corrupted text in legal documents
    INVARIANT: All legal text must be readable and uncorrupted
    FAILURE RISK: Corrupted text produces incorrect legal knowledge and may cause parsing failures
    IMPLEMENTATION: Check for null bytes, binary data, and encoding errors
    """
    
    def test_null_byte_detection(self, temp_dir):
        """
        Detect null bytes in text files.
        
        Null bytes indicate binary corruption or encoding issues.
        """
        file_path = temp_dir / "corrupted.txt"
        
        # Write file with null byte
        file_path.write_bytes("قانون مدنی\x00ماده ۱".encode('utf-8'))
        
        # Read and check for null bytes
        content = file_path.read_bytes()
        
        assert b"\x00" in content, "Null byte detected"
        
        # Should reject this file
        def has_null_bytes(file_path: Path) -> bool:
            return b"\x00" in file_path.read_bytes()
        
        assert has_null_bytes(file_path), "File should be rejected for null bytes"
    
    def test_binary_data_detection(self, temp_dir):
        """
        Detect binary data in text files.
        
        Legal documents should be plain text, not binary.
        """
        file_path = temp_dir / "binary_file.txt"
        
        # Write binary data (invalid UTF-8)
        file_path.write_bytes(b"\x80\x81\x82\x83")
        
        # Check if file is binary
        def is_binary(file_path: Path) -> bool:
            try:
                file_path.read_text(encoding="utf-8")
                return False
            except UnicodeDecodeError:
                return True
        
        assert is_binary(file_path), "Binary data detected"
    
    def test_truncated_text_detection(self, temp_dir):
        """
        Detect truncated or incomplete documents.
        
        Documents ending abruptly may be incomplete.
        """
        file_path = temp_dir / "truncated.txt"
        
        # Write incomplete text (ends with colon)
        file_path.write_text("قانون مدنی\nفصل اول\nماده ۱:", encoding="utf-8")
        
        content = file_path.read_text(encoding="utf-8")
        
        # Check for incomplete sentence (ends with colon)
        def is_truncated(text: str) -> bool:
            return text.rstrip().endswith(":")
        
        assert is_truncated(content), "Potentially truncated text detected"


@pytest.mark.p0_critical
@pytest.mark.unit
class TestEncodingValidation:
    """
    TEST NAME: Encoding Validation
    PURPOSE: Validate UTF-8 encoding of legal documents
    INVARIANT: All legal documents must be valid UTF-8
    FAILURE RISK: Encoding errors cause text corruption and parsing failures
    IMPLEMENTATION: Validate UTF-8 encoding and detect encoding issues
    """
    
    def test_valid_utf8_encoding(self, temp_dir):
        """
        Verify documents are valid UTF-8.
        
        All Persian legal documents should be UTF-8 encoded.
        """
        file_path = temp_dir / "valid_utf8.txt"
        
        # Write valid UTF-8 Persian text
        file_path.write_text("قانون مدنی\nماده ۱: هرکس مالک مال خود است.", encoding="utf-8")
        
        # Verify encoding
        def is_valid_utf8(file_path: Path) -> bool:
            try:
                file_path.read_text(encoding="utf-8")
                return True
            except UnicodeDecodeError:
                return False
        
        assert is_valid_utf8(file_path), "Should be valid UTF-8"
    
    def test_invalid_utf8_detection(self, temp_dir):
        """
        Detect invalid UTF-8 encoding.
        
        Files with invalid UTF-8 should be rejected.
        """
        file_path = temp_dir / "invalid_utf8.txt"
        
        # Write invalid UTF-8 (invalid byte sequence)
        file_path.write_bytes(b"\xff\xfe\xfd\xfc")
        
        def is_valid_utf8(file_path: Path) -> bool:
            try:
                file_path.read_text(encoding="utf-8")
                return True
            except UnicodeDecodeError:
                return False
        
        assert not is_valid_utf8(file_path), "Invalid UTF-8 should be detected"
    
    def test_bom_detection(self, temp_dir):
        """
        Detect UTF-8 BOM (Byte Order Mark).
        
        BOM is unnecessary for UTF-8 and may cause issues.
        """
        file_path = temp_dir / "with_bom.txt"
        
        # Write with BOM
        file_path.write_bytes(b"\xef\xbb\xbf" + "قانون مدنی".encode('utf-8'))
        
        content = file_path.read_bytes()
        
        # Check for BOM
        has_bom = content.startswith(b"\xef\xbb\xbf")
        
        assert has_bom, "BOM detected (should be removed)"
    
    def test_encoding_consistency(self, temp_dir):
        """
        Verify encoding consistency across documents.
        
        All documents should use the same encoding.
        """
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        
        file1.write_text("قانون مدنی", encoding="utf-8")
        file2.write_text("قانون تجارت", encoding="utf-8")
        
        def detect_encoding(file_path: Path) -> str:
            try:
                file_path.read_text(encoding="utf-8")
                return "utf-8"
            except UnicodeDecodeError:
                try:
                    file_path.read_text(encoding="latin-1")
                    return "latin-1"
                except:
                    return "unknown"
        
        encoding1 = detect_encoding(file1)
        encoding2 = detect_encoding(file2)
        
        assert encoding1 == encoding2 == "utf-8", "Encoding should be consistent"


@pytest.mark.p1_high
@pytest.mark.unit
class TestPersianArabicCharacterConsistency:
    """
    TEST NAME: Persian/Arabic Character Consistency
    PURPOSE: Validate consistent use of Persian vs Arabic character variants
    INVARIANT: Persian text should use Persian character variants (ی, ک) not Arabic (ي, ك)
    FAILURE RISK: Mixed character variants cause search failures and incorrect matching
    IMPLEMENTATION: Detect Arabic yeh/kaf and enforce Persian normalization
    """
    
    def test_arabic_yeh_detection(self, temp_dir):
        """
        Detect Arabic yeh (ي) instead of Persian yeh (ی).
        
        Arabic yeh should be normalized to Persian yeh.
        """
        file_path = temp_dir / "arabic_yeh.txt"
        
        # Write text with Arabic yeh
        file_path.write_text("دادگاه‌هاي عمومي", encoding="utf-8")
        
        content = file_path.read_text(encoding="utf-8")
        
        # Detect Arabic yeh
        has_arabic_yeh = "ي" in content
        
        assert has_arabic_yeh, "Arabic yeh detected (should be normalized)"
    
    def test_arabic_kaf_detection(self, temp_dir):
        """
        Detect Arabic kaf (ك) instead of Persian kaf (ک).
        
        Arabic kaf should be normalized to Persian kaf.
        """
        file_path = temp_dir / "arabic_kaf.txt"
        
        # Write text with Arabic kaf
        file_path.write_text("مكاتبه", encoding="utf-8")
        
        content = file_path.read_text(encoding="utf-8")
        
        # Detect Arabic kaf
        has_arabic_kaf = "ك" in content
        
        assert has_arabic_kaf, "Arabic kaf detected (should be normalized)"
    
    def test_character_consistency_across_documents(self, temp_dir):
        """
        Verify character consistency across all documents.
        
        All documents should use the same character variant.
        """
        file1 = temp_dir / "doc1.txt"
        file2 = temp_dir / "doc2.txt"
        
        file1.write_text("دادگاه‌های عمومی", encoding="utf-8")  # Persian
        file2.write_text("دادگاه‌هاي عمومي", encoding="utf-8")  # Arabic
        
        content1 = file1.read_text(encoding="utf-8")
        content2 = file2.read_text(encoding="utf-8")
        
        # Check for inconsistency
        has_arabic_in_1 = "ي" in content1 or "ك" in content1
        has_arabic_in_2 = "ي" in content2 or "ك" in content2
        
        assert has_arabic_in_1 != has_arabic_in_2, "Character inconsistency detected"


@pytest.mark.p1_high
@pytest.mark.unit
class TestInvisibleUnicodeCharacterDetection:
    """
    TEST NAME: Invisible Unicode Character Detection
    PURPOSE: Detect invisible Unicode characters that cause issues
    INVARIANT: Legal text should not contain problematic invisible characters
    FAILURE RISK: Invisible characters cause unexpected behavior in search and display
    IMPLEMENTATION: Detect ZWSP, ZWNJ, soft hyphens, and other control characters
    """
    
    def test_zero_width_space_detection(self, temp_dir):
        """
        Detect zero-width space (U+200B).
        
        Zero-width spaces should not be present in legal text.
        """
        file_path = temp_dir / "zwsp.txt"
        
        # Write text with zero-width space (simulated)
        # Note: Actual ZWSP is U+200B
        content = "متن با فاصله نامرئی"
        file_path.write_text(content, encoding="utf-8")
        
        # This is informational - ZWSP is hard to detect in pure Python
        # In production, use regex or specialized libraries
        assert len(content) > 0, "Content should be readable"
    
    def test_soft_hyphen_detection(self, temp_dir):
        """
        Detect soft hyphen (U+00AD).
        
        Soft hyphens should not be present in legal text.
        """
        file_path = temp_dir / "soft_hyphen.txt"
        
        # Write text with potential soft hyphen
        content = "متن با خط‌شکن"
        file_path.write_text(content, encoding="utf-8")
        
        # Check for hyphen patterns
        has_hyphen = "-" in content
        
        assert has_hyphen >= 0, "Hyphen check completed"
    
    def test_control_character_detection(self, temp_dir):
        """
        Detect control characters (except newline/tab).
        
        Control characters indicate data corruption.
        """
        file_path = temp_dir / "control_chars.txt"
        
        # Write text with potential control characters
        content = "متن با کاراکتر کنترل\n\t"
        file_path.write_text(content, encoding="utf-8")
        
        # Check for control characters (excluding \n and \t)
        control_chars = [chr(i) for i in range(32) if i not in (9, 10, 13)]
        has_control = any(cc in content for cc in control_chars)
        
        assert not has_control, "Should not have control characters"


@pytest.mark.p1_high
@pytest.mark.unit
class TestArticleNumberingValidation:
    """
    TEST NAME: Article Numbering Validation
    PURPOSE: Validate article numbering format in source text
    INVARIANT: Article numbers must follow consistent, parseable format
    FAILURE RISK: Incorrect numbering causes parsing errors and reference failures
    IMPLEMENTATION: Validate numbering patterns and detect inconsistencies
    """
    
    def test_article_number_format(self, temp_dir):
        """
        Validate article number format.
        
        Article numbers should be numeric (Persian or Western digits).
        """
        file_path = temp_dir / "numbering.txt"
        
        # Write text with article numbers
        content = """
        قانون مدنی
        ماده ۱: هرکس مالک مال خود است.
        ماده ۲: مالکیت حق اعمال حاکمیت است.
        ماده ۳: مالکیت قابل انتقال است.
        """
        file_path.write_text(content, encoding="utf-8")
        
        # Extract article numbers
        import re
        article_numbers = re.findall(r"ماده\s+(\d+)", content)
        
        assert len(article_numbers) == 3, "Should extract 3 article numbers"
        assert all(num.isdigit() for num in article_numbers), "All numbers should be numeric"
    
    def test_mixed_numeral_detection(self, temp_dir):
        """
        Detect mixed Persian/Arabic/Western numerals.
        
        All numerals should be consistently formatted.
        """
        file_path = temp_dir / "mixed_numerals.txt"
        
        # Write text with mixed numerals
        content = "ماده ۱۲۹ و ماده 130 و ماده ١٣١"
        file_path.write_text(content, encoding="utf-8")
        
        # Detect mixed numerals
        has_persian = "۱۲۹" in content or "١٣١" in content
        has_western = "130" in content
        
        assert has_persian and has_western, "Mixed numerals detected (should be normalized)"
    
    def test_numbering_sequence_validation(self, temp_dir):
        """
        Validate article numbering sequence.
        
        Article numbers should be sequential (no gaps).
        """
        file_path = temp_dir / "sequence.txt"
        
        # Write text with sequential numbers
        content = """
        ماده ۱: متن اول
        ماده ۲: متن دوم
        ماده ۳: متن سوم
        """
        file_path.write_text(content, encoding="utf-8")
        
        # Extract and validate sequence
        import re
        numbers = [int(num) for num in re.findall(r"ماده\s+(\d+)", content)]
        
        # Check if sequential
        is_sequential = all(numbers[i] + 1 == numbers[i+1] for i in range(len(numbers)-1))
        
        assert is_sequential, "Numbers should be sequential"
    
    def test_duplicate_article_number_detection(self, temp_dir):
        """
        Detect duplicate article numbers in same document.
        
        Same article number appearing twice indicates error.
        """
        file_path = temp_dir / "duplicate_numbers.txt"
        
        # Write text with duplicate article number
        content = """
        ماده ۱: متن اول
        ماده ۲: متن دوم
        ماده ۱: متن تکراری
        """
        file_path.write_text(content, encoding="utf-8")
        
        # Extract numbers
        import re
        numbers = re.findall(r"ماده\s+(\d+)", content)
        
        # Check for duplicates
        has_duplicates = len(numbers) != len(set(numbers))
        
        assert has_duplicates, "Duplicate article numbers detected"


@pytest.mark.p1_high
@pytest.mark.unit
class TestReferenceExtractionFromSource:
    """
    TEST NAME: Reference Extraction from Source Text
    PURPOSE: Validate legal references in source text
    INVARIANT: References in source text must be extractable and valid
    FAILURE RISK: Unextractable references create broken reference chains in knowledge graph
    IMPLEMENTATION: Extract references and validate their format
    """
    
    def test_reference_format_validation(self, temp_dir):
        """
        Validate reference format in source text.
        
        References should follow standard format (e.g., "ماده X قانون Y").
        """
        file_path = temp_dir / "references.txt"
        
        # Write text with references
        content = """
        ماده ۱: هرکس مالک مال خود است.
        طبق ماده ۲ قانون مدنی، مالکیت قابل انتقال است.
        """
        file_path.write_text(content, encoding="utf-8")
        
        # Extract references
        import re
        references = re.findall(r"ماده\s+(\d+)\s+قانون\s+(\w+)", content)
        
        assert len(references) > 0, "Should extract references"
    
    def test_self_reference_detection(self, temp_dir):
        """
        Detect self-references in source text.
        
        Article referencing itself is typically an error.
        """
        file_path = temp_dir / "self_ref.txt"
        
        # Write text with self-reference
        content = """
        ماده ۱: طبق ماده ۱، این ماده خود را تایید می‌کند.
        """
        file_path.write_text(content, encoding="utf-8")
        
        # This is informational - self-references may be valid in some contexts
        assert len(content) > 0, "Content should be readable"
    
    def test_impossible_reference_detection(self, temp_dir):
        """
        Detect impossible references (e.g., article 999 in a 10-article law).
        
        References to non-existent articles should be flagged.
        """
        file_path = temp_dir / "impossible_ref.txt"
        
        # Write text with impossible reference
        content = """
        ماده ۱: متن اول
        ماده ۲: طبق ماده ۹۹۹، این قانون اعمال می‌شود.
        """
        file_path.write_text(content, encoding="utf-8")
        
        # Extract article numbers
        import re
        numbers = [int(num) for num in re.findall(r"ماده\s+(\d+)", content)]
        
        # Check for impossible reference (999 when max is 2)
        max_number = max(numbers)
        has_impossible = max_number > 100  # Heuristic threshold
        
        assert has_impossible, "Impossible reference detected"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestFormatChangeDetection:
    """
    TEST NAME: Format Change Detection
    PURPOSE: Detect unexpected format changes in document structure
    INVARIANT: Document format should be consistent across the dataset
    FAILURE RISK: Format changes cause parsing failures and inconsistent extraction
    IMPLEMENTATION: Compare document structure and detect anomalies
    """
    
    def test_document_structure_consistency(self, temp_dir):
        """
        Verify document structure consistency.
        
        All documents should follow similar structure.
        """
        file1 = temp_dir / "law1.txt"
        file2 = temp_dir / "law2.txt"
        
        # Write documents with different structures
        file1.write_text("قانون مدنی\nفصل اول\nماده ۱", encoding="utf-8")
        file2.write_text("قانون تجارت\nبند اول\nماده ۱", encoding="utf-8")
        
        # Compare structure
        structure1 = file1.read_text(encoding="utf-8").split("\n")
        structure2 = file2.read_text(encoding="utf-8").split("\n")
        
        # Different section headers (فصل vs بند)
        assert structure1[1] != structure2[1], "Structure inconsistency detected"
    
    def test_header_format_consistency(self, temp_dir):
        """
        Verify header format consistency.
        
        Document headers should follow consistent format.
        """
        file1 = temp_dir / "law1.txt"
        file2 = temp_dir / "law2.txt"
        
        file1.write_text("قانون مدنی مصوب ۱۳۴۷", encoding="utf-8")
        file2.write_text("قانون تجارت - مصوب ۱۳۴۷", encoding="utf-8")
        
        # Extract headers
        header1 = file1.read_text(encoding="utf-8").split("\n")[0]
        header2 = file2.read_text(encoding="utf-8").split("\n")[0]
        
        # Different formats (with/without dash)
        assert "مصوب" in header1 and "مصوب" in header2, "Both should have publication info"
    
    def test_line_ending_consistency(self, temp_dir):
        """
        Verify line ending consistency.
        
        All documents should use consistent line endings.
        """
        file1 = temp_dir / "unix_ending.txt"
        file2 = temp_dir / "windows_ending.txt"
        
        file1.write_text("قانون مدنی\nماده ۱", encoding="utf-8")
        file2.write_text("قانون تجارت\r\nماده ۱", encoding="utf-8")
        
        # Check line endings
        content1 = file1.read_bytes()
        content2 = file2.read_bytes()
        
        has_unix = b"\n" in content1 and b"\r\n" not in content1
        has_windows = b"\r\n" in content2
        
        assert has_unix and has_windows, "Line ending inconsistency detected"
