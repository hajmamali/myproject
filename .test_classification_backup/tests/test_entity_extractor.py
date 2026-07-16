"""
Unit Tests for Entity Extractor
================================

Tests for the EntityExtractor class covering:
- Entity extraction with different methods
- Entity normalization
- Duplicate merging
- Validation
- Accuracy requirements (>90%)
"""

import pytest
from mahoun.graph.builders.entity_extractor import (
    EntityExtractor,
    Entity,
    extract_entities_from_text,
)


class TestEntity:
    """Test Entity dataclass"""

    def test_entity_creation(self):
        """Test creating an entity"""
        entity = Entity(
            text="ماده 10", label="ARTICLE", start=0, end=7, score=0.95, source="regex"
        )

        assert entity.text == "ماده 10"
        assert entity.label == "ARTICLE"
        assert entity.score == 0.95
        assert entity.normalized_text is not None

    def test_entity_normalization(self):
        """Test entity text normalization"""
        entity = Entity(
            text="ماده  ۱۰",  # Extra space and Persian digits
            label="ARTICLE",
            start=0,
            end=9,
            score=0.95,
        )

        # Should normalize Persian digits and spaces
        assert "10" in entity.normalized_text or "۱۰" in entity.normalized_text

    def test_entity_equality(self):
        """Test entity equality for deduplication"""
        entity1 = Entity(text="ماده 10", label="ARTICLE", start=0, end=7, score=0.95)

        entity2 = Entity(
            text="ماده ۱۰",  # Same but with Persian digits
            label="ARTICLE",
            start=10,
            end=17,
            score=0.90,
        )

        # Should be equal after normalization
        assert entity1.normalized_text == entity2.normalized_text
        assert entity1.label == entity2.label


class TestEntityExtractor:
    """Test EntityExtractor class"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance"""
        return EntityExtractor(use_ner=False, min_score=0.7)

    @pytest.fixture
    def extractor_with_ner(self):
        """Create extractor with NER"""
        return EntityExtractor(use_ner=True, min_score=0.7)

    def test_extractor_initialization(self, extractor):
        """Test extractor initialization"""
        assert extractor.min_score == 0.7
        assert extractor.use_ner == False

    def test_extract_entities_empty_text(self, extractor):
        """Test extraction from empty text"""
        entities = extractor.extract_entities("")
        assert len(entities) == 0

        entities = extractor.extract_entities("   ")
        assert len(entities) == 0

    def test_extract_entities_with_articles(self, extractor):
        """Test extraction of article references"""
        text = "به استناد ماده 10 قانون مدنی و ماده 20 قانون مجازات"
        entities = extractor.extract_entities(text)

        # Should find at least article references
        article_entities = [e for e in entities if e.label == "ARTICLE"]
        assert len(article_entities) >= 2

        # Check article numbers
        article_texts = [e.text for e in article_entities]
        assert any("10" in text for text in article_texts)
        assert any("20" in text for text in article_texts)

    def test_extract_entities_with_case_numbers(self, extractor):
        """Test extraction of case numbers"""
        text = "پرونده شماره 1234/98 و پرونده 5678/99"
        entities = extractor.extract_entities(text)

        # Should find case numbers
        case_entities = [e for e in entities if e.label == "CASE_NO"]
        assert len(case_entities) >= 2

    def test_extract_entities_with_dates(self, extractor):
        """Test extraction of dates"""
        text = "دادنامه مورخ 1400/05/15 صادر شد"
        entities = extractor.extract_entities(text)

        # Should find date
        date_entities = [e for e in entities if e.label == "DATE"]
        assert len(date_entities) >= 1

    def test_extract_entities_complex_text(self, extractor):
        """Test extraction from complex legal text"""
        text = """
        رأی دادگاه بدوی در خصوص دعوی آقای احمد به طرفیت خانم فاطمه
        به خواسته الزام به پرداخت مهریه به استناد ماده 10 قانون مدنی
        و ماده 1082 قانون مدنی در پرونده شماره 9812345 مورخ 1400/05/15
        حکم به محکومیت خوانده صادر گردید.
        """

        entities = extractor.extract_entities(text)

        # Should extract multiple entity types
        assert len(entities) > 0

        # Check for different entity types
        labels = set(e.label for e in entities)
        assert "ARTICLE" in labels or "LAW_NAME" in labels or "CASE_NO" in labels

    def test_normalize_entity(self, extractor):
        """Test entity normalization"""
        entity = Entity(
            text="  ماده  ۱۰  ", label="ARTICLE", start=0, end=13, score=0.95
        )

        normalized = extractor.normalize_entity(entity)

        # Should remove extra spaces
        assert "  " not in normalized.normalized_text
        # Should be lowercase
        assert normalized.normalized_text == normalized.normalized_text.lower()

    def test_merge_duplicates_same_entity(self, extractor):
        """Test merging duplicate entities"""
        entities = [
            Entity(
                text="ماده 10",
                label="ARTICLE",
                start=0,
                end=7,
                score=0.95,
                source="regex",
            ),
            Entity(
                text="ماده ۱۰",
                label="ARTICLE",
                start=10,
                end=17,
                score=0.90,
                source="nlp",
            ),
            Entity(
                text="ماده 10",
                label="ARTICLE",
                start=20,
                end=27,
                score=0.85,
                source="ner",
            ),
        ]

        merged = extractor.merge_duplicates(entities)

        # Should merge to single entity
        assert len(merged) == 1
        # Should keep highest score
        assert merged[0].score == 0.95
        # Should combine sources
        assert "+" in merged[0].source or len(merged[0].source) > 5

    def test_merge_duplicates_different_labels(self, extractor):
        """Test that different labels are not merged"""
        entities = [
            Entity(text="ماده 10", label="ARTICLE", start=0, end=7, score=0.95),
            Entity(text="ماده 10", label="LAW_NAME", start=0, end=7, score=0.90),
        ]

        merged = extractor.merge_duplicates(entities)

        # Should NOT merge (different labels)
        assert len(merged) == 2

    def test_validate_entity_valid(self, extractor):
        """Test validation of valid entity"""
        entity = Entity(text="ماده 10", label="ARTICLE", start=0, end=7, score=0.95)

        assert extractor.validate_entity(entity) == True

    def test_validate_entity_low_score(self, extractor):
        """Test validation rejects low score"""
        entity = Entity(
            text="ماده 10",
            label="ARTICLE",
            start=0,
            end=7,
            score=0.5,  # Below threshold
        )

        assert extractor.validate_entity(entity) == False

    def test_validate_entity_short_text(self, extractor):
        """Test validation rejects short text"""
        entity = Entity(
            text="م",  # Too short
            label="ARTICLE",
            start=0,
            end=1,
            score=0.95,
        )

        assert extractor.validate_entity(entity) == False

    def test_validate_entity_empty_text(self, extractor):
        """Test validation rejects empty text"""
        entity = Entity(text="", label="ARTICLE", start=0, end=0, score=0.95)

        assert extractor.validate_entity(entity) == False

    def test_filter_entities(self, extractor):
        """Test filtering entities"""
        entities = [
            Entity(
                text="ماده 10", label="ARTICLE", start=0, end=7, score=0.95
            ),  # Valid
            Entity(
                text="م", label="ARTICLE", start=10, end=11, score=0.95
            ),  # Too short
            Entity(
                text="ماده 20", label="ARTICLE", start=20, end=27, score=0.5
            ),  # Low score
            Entity(
                text="ماده 30", label="ARTICLE", start=30, end=37, score=0.85
            ),  # Valid
        ]

        filtered = extractor.filter_entities(entities)

        # Should keep only 2 valid entities
        assert len(filtered) == 2
        assert all(e.score >= 0.7 for e in filtered)
        assert all(len(e.text) >= 2 for e in filtered)

    def test_get_entity_statistics(self, extractor):
        """Test entity statistics"""
        entities = [
            Entity(
                text="ماده 10",
                label="ARTICLE",
                start=0,
                end=7,
                score=0.95,
                source="regex",
            ),
            Entity(
                text="ماده 20",
                label="ARTICLE",
                start=10,
                end=17,
                score=0.90,
                source="nlp",
            ),
            Entity(
                text="دادگاه", label="COURT", start=20, end=26, score=0.85, source="nlp"
            ),
        ]

        stats = extractor.get_entity_statistics(entities)

        assert stats["total"] == 3
        assert stats["by_label"]["ARTICLE"] == 2
        assert stats["by_label"]["COURT"] == 1
        assert stats["by_source"]["regex"] == 1
        assert stats["by_source"]["nlp"] == 2
        assert 0.85 <= stats["avg_score"] <= 0.95

    def test_extract_and_validate(self, extractor):
        """Test combined extraction and validation"""
        text = "به استناد ماده 10 قانون مدنی"
        entities = extractor.extract_and_validate(text)

        # All returned entities should be valid
        assert all(extractor.validate_entity(e) for e in entities)
        assert all(e.score >= 0.7 for e in entities)


class TestAccuracy:
    """Test accuracy requirements (>90%)"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance"""
        return EntityExtractor(use_ner=False, min_score=0.7)

    def test_article_extraction_accuracy(self, extractor):
        """Test article extraction accuracy"""
        # Test cases with known articles
        test_cases = [
            ("به استناد ماده 10 قانون مدنی", ["10"]),
            ("مواد 10 و 20 و 30", ["10", "20", "30"]),
            ("ماده 1082 قانون مدنی", ["1082"]),
            ("تبصره 2 ماده 5", ["5"]),
            ("مواد 100 تا 110", ["100", "110"]),
        ]

        total_expected = 0
        total_found = 0

        for text, expected_numbers in test_cases:
            entities = extractor.extract_entities(text)
            article_entities = [e for e in entities if e.label == "ARTICLE"]

            # Count how many expected articles were found
            for num in expected_numbers:
                total_expected += 1
                if any(num in e.text for e in article_entities):
                    total_found += 1

        # Calculate accuracy
        accuracy = total_found / total_expected if total_expected > 0 else 0

        # Should be > 90% accuracy
        assert accuracy >= 0.9, (
            f"Article extraction accuracy {accuracy:.2%} is below 90%"
        )

    def test_case_number_extraction_accuracy(self, extractor):
        """Test case number extraction accuracy"""
        test_cases = [
            ("پرونده شماره 1234/98", ["1234/98"]),
            ("کلاسه 5678/99", ["5678/99"]),
            ("پرونده 123/456789", ["123/456789"]),
        ]

        total_expected = 0
        total_found = 0

        for text, expected_numbers in test_cases:
            entities = extractor.extract_entities(text)
            case_entities = [e for e in entities if e.label == "CASE_NO"]

            for num in expected_numbers:
                total_expected += 1
                if any(num in e.text for e in case_entities):
                    total_found += 1

        accuracy = total_found / total_expected if total_expected > 0 else 0

        # Should be > 90% accuracy
        assert accuracy >= 0.9, (
            f"Case number extraction accuracy {accuracy:.2%} is below 90%"
        )


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_extract_entities_from_text(self):
        """Test convenience function"""
        text = "به استناد ماده 10 قانون مدنی"
        entities = extract_entities_from_text(text, use_ner=False)

        assert isinstance(entities, list)
        assert len(entities) > 0
        assert all(isinstance(e, Entity) for e in entities)


# Integration test with real data
class TestRealData:
    """Test with real legal document data"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance"""
        return EntityExtractor(use_ner=False, min_score=0.7)

    def test_real_verdict_text(self, extractor):
        """Test extraction from real verdict text"""
        text = """
        رأی شعبه دیوان عالی کشور شماره پرونده : 9409981210900027 
        شماره دادنامه : 9509970910700480 شعبه : شعبه سی و چهارم دیوان عالی کشور 
        تاریخ : 1395/12/15 قاضی : حسن قاسمی قاضی : جواد اسلامی 
        خلاصه جریان پرونده دادرس شعبه 9 دادگاه عمومی حقوقی آمل 
        در خصوص دعوی به خواسته الزام به صدور مدرک مربیگری 
        پس از رسیدگی طبق دادنامه شماره 1131 دعوی خواهان را ثابت تشخیص داده 
        و حکم بر الزام خواندگان به صدور حکم مربیگری خواهان صادر کرده است.
        """

        entities = extractor.extract_entities(text)

        # Should extract multiple entities
        assert len(entities) > 0

        # Should have different entity types
        labels = set(e.label for e in entities)
        assert len(labels) > 1

        # Should extract case numbers
        case_entities = [e for e in entities if e.label == "CASE_NO"]
        assert len(case_entities) > 0

        # Should extract dates
        date_entities = [e for e in entities if e.label == "DATE"]
        assert len(date_entities) > 0
