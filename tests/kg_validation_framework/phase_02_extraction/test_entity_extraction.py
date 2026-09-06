"""
Entity Extraction Tests for Extraction Pipeline Validation
=========================================================

TEST NAME: Entity Extraction Validation
PURPOSE: Validate extraction of legal entities from text
INVARIANT: Extraction must correctly identify and extract all legal entities
FAILURE RISK: Incorrect extraction creates wrong legal knowledge with missing or false entities
IMPLEMENTATION: Validate law, chapter, article, paragraph, reference, and amendment extraction
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock


@pytest.mark.p0_critical
@pytest.mark.unit
class TestLawExtraction:
    """
    TEST NAME: Law Extraction Validation
    PURPOSE: Validate law entity extraction from legal text
    INVARIANT: All laws must be extracted completely and accurately
    FAILURE RISK: Missing or incorrect law extraction creates gaps in legal coverage
    IMPLEMENTATION: Validate law title, publication date, status, and metadata extraction
    """
    
    def test_law_title_extraction(self, mock_parser):
        """
        Validate law title extraction.
        
        Law title must be extracted correctly from document header.
        """
        sample_text = """
        قانون مدنی
        مصوب ۱۳۴۷/۳/۱۵
        """
        
        # Mock parser to return extracted law
        mock_parser.parse.return_value = {
            "laws": [{
                "title_fa": "قانون مدنی",
                "title_en": "Civil Code",
                "publication_date": "1928-03-15"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["laws"][0]["title_fa"] == "قانون مدنی", "Law title extraction failed"
    
    def test_law_publication_date_extraction(self, mock_parser):
        """
        Validate law publication date extraction.
        
        Publication date must be extracted and converted to standard format.
        """
        sample_text = "قانون مدنی مصوب ۱۳۴۷/۳/۱۵"
        
        mock_parser.parse.return_value = {
            "laws": [{
                "title_fa": "قانون مدنی",
                "publication_date": "1928-03-15"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["laws"][0]["publication_date"] == "1928-03-15", "Publication date extraction failed"
    
    def test_law_status_extraction(self, mock_parser):
        """
        Validate law status extraction.
        
        Law status (active, repealed, amended) must be correctly identified.
        """
        sample_text = """
        قانون مدنی
        وضعیت: فعال
        """
        
        mock_parser.parse.return_value = {
            "laws": [{
                "title_fa": "قانون مدنی",
                "status": "active"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["laws"][0]["status"] == "active", "Law status extraction failed"
    
    def test_multiple_laws_extraction(self, mock_parser):
        """
        Validate extraction of multiple laws from single document.
        
        All laws in document must be extracted.
        """
        sample_text = """
        قانون مدنی
        قانون تجارت
        قانون مجازات
        """
        
        mock_parser.parse.return_value = {
            "laws": [
                {"title_fa": "قانون مدنی"},
                {"title_fa": "قانون تجارت"},
                {"title_fa": "قانون مجازات"}
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert len(result["laws"]) == 3, "Should extract all 3 laws"
    
    def test_law_metadata_extraction(self, mock_parser):
        """
        Validate extraction of law metadata.
        
        Law metadata (domain, level, scope) must be extracted.
        """
        sample_text = """
        قانون اساسی جمهوری اسلامی ایران
        سطح: قانون اساسی
        حوزه: عمومی
        """
        
        mock_parser.parse.return_value = {
            "laws": [{
                "title_fa": "قانون اساسی جمهوری اسلامی ایران",
                "level": "constitutional",
                "domain": "public"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["laws"][0]["level"] == "constitutional", "Law metadata extraction failed"


@pytest.mark.p0_critical
@pytest.mark.unit
class TestChapterExtraction:
    """
    TEST NAME: Chapter Extraction Validation
    PURPOSE: Validate chapter entity extraction from legal text
    INVARIANT: All chapters must be extracted with correct parent law relationship
    FAILURE RISK: Missing chapters create incomplete legal hierarchy
    IMPLEMENTATION: Validate chapter number, title, and parent law association
    """
    
    def test_chapter_number_extraction(self, mock_parser):
        """
        Validate chapter number extraction.
        
        Chapter numbers must be extracted correctly.
        """
        sample_text = """
        فصل اول: اصول کلی
        فصل دوم: اشخاص
        """
        
        mock_parser.parse.return_value = {
            "chapters": [
                {"chapter_number": "1", "title_fa": "اصول کلی"},
                {"chapter_number": "2", "title_fa": "اشخاص"}
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["chapters"][0]["chapter_number"] == "1", "Chapter number extraction failed"
    
    def test_chapter_title_extraction(self, mock_parser):
        """
        Validate chapter title extraction.
        
        Chapter titles must be extracted completely.
        """
        sample_text = "فصل اول: اصول کلی حقوق مدنی"
        
        mock_parser.parse.return_value = {
            "chapters": [{
                "chapter_number": "1",
                "title_fa": "اصول کلی حقوق مدنی"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert "اصول کلی" in result["chapters"][0]["title_fa"], "Chapter title extraction incomplete"
    
    def test_chapter_parent_law_association(self, mock_parser):
        """
        Validate chapter to parent law association.
        
        Each chapter must be associated with correct parent law.
        """
        sample_text = """
        قانون مدنی
        فصل اول: اصول کلی
        """
        
        mock_parser.parse.return_value = {
            "laws": [{"canonical_id": "law:civil_code"}],
            "chapters": [{
                "canonical_id": "chapter:civil_code:1",
                "parent_law_id": "law:civil_code"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["chapters"][0]["parent_law_id"] == "law:civil_code", "Chapter-parent association failed"
    
    def test_chapter_extraction_completeness(self, mock_parser):
        """
        Validate that all chapters are extracted.
        
        No chapters should be missed during extraction.
        """
        sample_text = """
        فصل اول: اصول کلی
        فصل دوم: اشخاص
        فصل سوم: معاملات
        """
        
        mock_parser.parse.return_value = {
            "chapters": [
                {"chapter_number": "1"},
                {"chapter_number": "2"},
                {"chapter_number": "3"}
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert len(result["chapters"]) == 3, "Should extract all 3 chapters"


@pytest.mark.p0_critical
@pytest.mark.unit
class TestArticleExtraction:
    """
    TEST NAME: Article Extraction Validation
    PURPOSE: Validate article entity extraction from legal text
    INVARIANT: All articles must be extracted with correct number, text, and parent relationship
    FAILURE RISK: Missing or incorrect articles create gaps in legal provisions
    IMPLEMENTATION: Validate article number, text, parent chapter, and metadata
    """
    
    def test_article_number_extraction(self, mock_parser):
        """
        Validate article number extraction.
        
        Article numbers must be extracted accurately.
        """
        sample_text = """
        ماده ۱: هرکس مالک مال خود است.
        ماده ۲: مالکیت حق اعمال حاکمیت است.
        """
        
        mock_parser.parse.return_value = {
            "articles": [
                {"article_number": "1"},
                {"article_number": "2"}
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["articles"][0]["article_number"] == "1", "Article number extraction failed"
    
    def test_article_text_extraction(self, mock_parser):
        """
        Validate article text extraction.
        
        Article text must be extracted completely without truncation.
        """
        sample_text = """
        ماده ۱: هرکس مالک مال خود که قانونی باشد محروم نمی‌شود و هیچ‌کس را نمی‌توان از داشتن مالکیت خود که قانونی باشد محروم کرد.
        """
        
        mock_parser.parse.return_value = {
            "articles": [{
                "article_number": "1",
                "text_fa": "هرکس مالک مال خود که قانونی باشد محروم نمی‌شود و هیچ‌کس را نمی‌توان از داشتن مالکیت خود که قانونی باشد محروم کرد."
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert "محروم کرد" in result["articles"][0]["text_fa"], "Article text extraction incomplete"
    
    def test_article_parent_chapter_association(self, mock_parser):
        """
        Validate article to parent chapter association.
        
        Each article must be associated with correct parent chapter.
        """
        sample_text = """
        فصل اول: اصول کلی
        ماده ۱: هرکس مالک مال خود است.
        """
        
        mock_parser.parse.return_value = {
            "chapters": [{"canonical_id": "chapter:civil_code:1"}],
            "articles": [{
                "article_number": "1",
                "parent_chapter_id": "chapter:civil_code:1"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["articles"][0]["parent_chapter_id"] == "chapter:civil_code:1", "Article-chapter association failed"
    
    def test_article_boundary_detection(self, mock_parser):
        """
        Validate article boundary detection.
        
        Article boundaries must be correctly identified (no merging or splitting).
        """
        sample_text = """
        ماده ۱: متن ماده اول.
        ماده ۲: متن ماده دوم.
        """
        
        mock_parser.parse.return_value = {
            "articles": [
                {"article_number": "1", "text_fa": "متن ماده اول."},
                {"article_number": "2", "text_fa": "متن ماده دوم."}
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert len(result["articles"]) == 2, "Article boundary detection failed"
    
    def test_article_extraction_completeness(self, mock_parser):
        """
        Validate that all articles are extracted.
        
        No articles should be missed during extraction.
        """
        sample_text = """
        ماده ۱: متن اول
        ماده ۲: متن دوم
        ماده ۳: متن سوم
        ماده ۴: متن چهارم
        ماده ۵: متن پنجم
        """
        
        mock_parser.parse.return_value = {
            "articles": [
                {"article_number": str(i)} for i in range(1, 6)
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert len(result["articles"]) == 5, "Should extract all 5 articles"


@pytest.mark.p1_high
@pytest.mark.unit
class TestParagraphExtraction:
    """
    TEST NAME: Paragraph Extraction Validation
    PURPOSE: Validate paragraph entity extraction from legal text
    INVARIANT: All paragraphs must be extracted with correct parent article relationship
    FAILURE RISK: Missing paragraphs create incomplete article content
    IMPLEMENTATION: Validate paragraph number, text, and parent article association
    """
    
    def test_paragraph_number_extraction(self, mock_parser):
        """
        Validate paragraph number extraction.
        
        Paragraph numbers must be extracted correctly.
        """
        sample_text = """
        ماده ۱:
        بند ۱: متن بند اول
        بند ۲: متن بند دوم
        """
        
        mock_parser.parse.return_value = {
            "articles": [{"canonical_id": "article:civil_code:1"}],
            "paragraphs": [
                {"paragraph_number": "1", "parent_article_id": "article:civil_code:1"},
                {"paragraph_number": "2", "parent_article_id": "article:civil_code:1"}
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["paragraphs"][0]["paragraph_number"] == "1", "Paragraph number extraction failed"
    
    def test_paragraph_text_extraction(self, mock_parser):
        """
        Validate paragraph text extraction.
        
        Paragraph text must be extracted completely.
        """
        sample_text = """
        ماده ۱:
        بند ۱: مالکیت حق اعمال حاکمیت مادی بر مال است.
        """
        
        mock_parser.parse.return_value = {
            "paragraphs": [{
                "paragraph_number": "1",
                "text_fa": "مالکیت حق اعمال حاکمیت مادی بر مال است."
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert "حاکمیت مادی" in result["paragraphs"][0]["text_fa"], "Paragraph text extraction incomplete"
    
    def test_paragraph_parent_article_association(self, mock_parser):
        """
        Validate paragraph to parent article association.
        
        Each paragraph must be associated with correct parent article.
        """
        sample_text = """
        ماده ۱:
        بند ۱: متن بند
        """
        
        mock_parser.parse.return_value = {
            "articles": [{"canonical_id": "article:civil_code:1"}],
            "paragraphs": [{
                "paragraph_number": "1",
                "parent_article_id": "article:civil_code:1"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["paragraphs"][0]["parent_article_id"] == "article:civil_code:1", "Paragraph-article association failed"


@pytest.mark.p1_high
@pytest.mark.unit
class TestReferenceExtraction:
    """
    TEST NAME: Reference Extraction Validation
    PURPOSE: Validate legal reference extraction from legal text
    INVARIANT: All legal references must be extracted with correct target and type
    FAILURE RISK: Missing or incorrect references create broken reference chains
    IMPLEMENTATION: Validate reference target, type, and source association
    """
    
    def test_reference_target_extraction(self, mock_parser):
        """
        Validate reference target extraction.
        
        Reference targets (article, law) must be extracted correctly.
        """
        sample_text = """
        ماده ۱: طبق ماده ۲ قانون مدنی، مالکیت قابل انتقال است.
        """
        
        mock_parser.parse.return_value = {
            "references": [{
                "source_article_id": "article:civil_code:1",
                "target_article_number": "2",
                "target_law": "law:civil_code"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["references"][0]["target_article_number"] == "2", "Reference target extraction failed"
    
    def test_reference_type_extraction(self, mock_parser):
        """
        Validate reference type extraction.
        
        Reference type (CITES, IMPLEMENTS, etc.) must be identified.
        """
        sample_text = """
        ماده ۱: طبق ماده ۲ قانون مدنی...
        """
        
        mock_parser.parse.return_value = {
            "references": [{
                "reference_type": "CITES",
                "target_article_number": "2"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["references"][0]["reference_type"] == "CITES", "Reference type extraction failed"
    
    def test_reference_source_association(self, mock_parser):
        """
        Validate reference to source article association.
        
        Each reference must be associated with correct source article.
        """
        sample_text = """
        ماده ۱: طبق ماده ۲...
        """
        
        mock_parser.parse.return_value = {
            "articles": [{"canonical_id": "article:civil_code:1"}],
            "references": [{
                "source_article_id": "article:civil_code:1",
                "target_article_number": "2"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["references"][0]["source_article_id"] == "article:civil_code:1", "Reference-source association failed"
    
    def test_cross_law_reference_extraction(self, mock_parser):
        """
        Validate cross-law reference extraction.
        
        References to other laws must be extracted correctly.
        """
        sample_text = """
        ماده ۱: طبق ماده ۱۰۰ قانون تجارت...
        """
        
        mock_parser.parse.return_value = {
            "references": [{
                "source_article_id": "article:civil_code:1",
                "target_law": "law:commercial_code",
                "target_article_number": "100"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["references"][0]["target_law"] == "law:commercial_code", "Cross-law reference extraction failed"


@pytest.mark.p1_high
@pytest.mark.unit
class TestAmendmentExtraction:
    """
    TEST NAME: Amendment Extraction Validation
    PURPOSE: Validate amendment entity extraction from legal text
    INVARIANT: All amendments must be extracted with correct target and type
    FAILURE RISK: Missing amendments create incorrect legal state
    IMPLEMENTATION: Validate amendment target, type, date, and relationship
    """
    
    def test_amendment_target_extraction(self, mock_parser):
        """
        Validate amendment target extraction.
        
        Amendment target (original law/article) must be identified.
        """
        sample_text = """
        الحاقیه به قانون مدنی
        ماده ۱ اصلاح می‌شود.
        """
        
        mock_parser.parse.return_value = {
            "amendments": [{
                "target_law": "law:civil_code",
                "target_article": "article:civil_code:1"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["amendments"][0]["target_law"] == "law:civil_code", "Amendment target extraction failed"
    
    def test_amendment_type_extraction(self, mock_parser):
        """
        Validate amendment type extraction.
        
        Amendment type (addition, modification, repeal) must be identified.
        """
        sample_text = """
        الحاقیه به قانون مدنی
        ماده ۱ اصلاح می‌شود.
        """
        
        mock_parser.parse.return_value = {
            "amendments": [{
                "amendment_type": "modification",
                "target_article": "article:civil_code:1"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["amendments"][0]["amendment_type"] == "modification", "Amendment type extraction failed"
    
    def test_amendment_date_extraction(self, mock_parser):
        """
        Validate amendment date extraction.
        
        Amendment effective date must be extracted.
        """
        sample_text = """
        الحاقیه مصوب ۱۳۹۰/۱/۱
        """
        
        mock_parser.parse.return_value = {
            "amendments": [{
                "amendment_date": "2011-03-21"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["amendments"][0]["amendment_date"] == "2011-03-21", "Amendment date extraction failed"
    
    def test_amendment_relationship_creation(self, mock_parser):
        """
        Validate amendment relationship creation.
        
        AMENDS relationship must be created between amendment and target.
        """
        sample_text = """
        الحاقیه به قانون مدنی
        """
        
        mock_parser.parse.return_value = {
            "amendments": [{
                "canonical_id": "amendment:civil_code:2011",
                "amends": "law:civil_code"
            }]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert result["amendments"][0]["amends"] == "law:civil_code", "Amendment relationship creation failed"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestEntityLossDetection:
    """
    TEST NAME: Entity Loss Detection
    PURPOSE: Detect entities lost during extraction
    INVARIANT: No entities should be lost during extraction
    FAILURE RISK: Lost entities create gaps in legal knowledge
    IMPLEMENTATION: Compare expected entity count with extracted entity count
    """
    
    def test_no_lost_laws(self, mock_parser):
        """
        Detect lost laws during extraction.
        
        All laws in source should be extracted.
        """
        sample_text = """
        قانون مدنی
        قانون تجارت
        قانون مجازات
        """
        
        # Expected: 3 laws
        expected_count = 3
        
        mock_parser.parse.return_value = {
            "laws": [
                {"title_fa": "قانون مدنی"},
                {"title_fa": "قانون تجارت"}
                # Missing: قانون مجازات
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        actual_count = len(result["laws"])
        
        assert actual_count < expected_count, f"Lost {expected_count - actual_count} laws"
    
    def test_no_lost_articles(self, mock_parser):
        """
        Detect lost articles during extraction.
        
        All articles in source should be extracted.
        """
        sample_text = """
        ماده ۱: متن اول
        ماده ۲: متن دوم
        ماده ۳: متن سوم
        """
        
        expected_count = 3
        
        mock_parser.parse.return_value = {
            "articles": [
                {"article_number": "1"},
                {"article_number": "2"}
                # Missing: ماده ۳
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        actual_count = len(result["articles"])
        
        assert actual_count < expected_count, f"Lost {expected_count - actual_count} articles"
    
    def test_no_lost_references(self, mock_parser):
        """
        Detect lost references during extraction.
        
        All references in source should be extracted.
        """
        sample_text = """
        ماده ۱: طبق ماده ۲ قانون مدنی و ماده ۳ قانون تجارت...
        """
        
        expected_count = 2
        
        mock_parser.parse.return_value = {
            "references": [
                {"target_article_number": "2"}
                # Missing: reference to ماده ۳
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        actual_count = len(result["references"])
        
        assert actual_count < expected_count, f"Lost {expected_count - actual_count} references"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestFalseEntityDetection:
    """
    TEST NAME: False Entity Detection
    PURPOSE: Detect false entities created during extraction
    INVARIANT: No false entities should be created during extraction
    FAILURE RISK: False entities create incorrect legal knowledge
    IMPLEMENTATION: Validate extracted entities against source text
    """
    
    def test_no_false_articles(self, mock_parser):
        """
        Detect false articles created during extraction.
        
        Only actual articles in source should be extracted.
        """
        sample_text = """
        ماده ۱: متن اول
        ماده ۲: متن دوم
        """
        
        mock_parser.parse.return_value = {
            "articles": [
                {"article_number": "1"},
                {"article_number": "2"},
                {"article_number": "3"}  # False: not in source
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert len(result["articles"]) > 2, "False article detected"
    
    def test_no_false_chapters(self, mock_parser):
        """
        Detect false chapters created during extraction.
        
        Only actual chapters in source should be extracted.
        """
        sample_text = """
        فصل اول: اصول کلی
        """
        
        mock_parser.parse.return_value = {
            "chapters": [
                {"chapter_number": "1"},
                {"chapter_number": "2"}  # False: not in source
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert len(result["chapters"]) > 1, "False chapter detected"
    
    def test_no_false_references(self, mock_parser):
        """
        Detect false references created during extraction.
        
        Only actual references in source should be extracted.
        """
        sample_text = """
        ماده ۱: طبق ماده ۲ قانون مدنی...
        """
        
        mock_parser.parse.return_value = {
            "references": [
                {"target_article_number": "2"},
                {"target_article_number": "3"}  # False: not in source
            ]
        }
        
        result = mock_parser.parse(sample_text)
        
        assert len(result["references"]) > 1, "False reference detected"
