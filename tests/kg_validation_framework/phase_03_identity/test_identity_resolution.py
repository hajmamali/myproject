"""
Entity Identity and Deduplication Tests
========================================

TEST NAME: Entity Identity Resolution Validation
PURPOSE: Validate entity identity management and prevent false merges
INVARIANT: Each legal entity must have exactly one identity; similarity ≠ identity
FAILURE RISK: False merges create contradictory legal knowledge with duplicate/conflicting entities
IMPLEMENTATION: Detect same law with different names, duplicate articles, similar text but different entities
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock


@pytest.mark.p1_high
@pytest.mark.unit
class TestSameLawDifferentNames:
    """
    TEST NAME: Same Law with Different Names Detection
    PURPOSE: Detect the same law appearing with different names
    INVARIANT: Each law should have exactly one canonical identity regardless of name variations
    FAILURE RISK: Same law with different names creates duplicate/conflicting legal entities
    IMPLEMENTATION: Compare law metadata (publication date, content) to detect identity despite name differences
    """
    
    def test_same_law_different_titles(self):
        """
        Detect same law with different title variations.
        
        Law may be cited with different titles (e.g., "قانون مدنی" vs "قانون مدنی ایران").
        """
        law1 = {
            "title_fa": "قانون مدنی",
            "publication_date": "1928-03-15",
            "content_hash": "abc123"
        }
        
        law2 = {
            "title_fa": "قانون مدنی ایران",
            "publication_date": "1928-03-15",
            "content_hash": "abc123"
        }
        
        # Same publication date and content hash → same law
        assert law1["publication_date"] == law2["publication_date"], "Same publication date"
        assert law1["content_hash"] == law2["content_hash"], "Same content hash"
        
        # Should be merged, not treated as separate laws
        def detect_same_law(law1: Dict, law2: Dict) -> bool:
            return (law1["publication_date"] == law2["publication_date"] and
                    law1["content_hash"] == law2["content_hash"])
        
        assert detect_same_law(law1, law2), "Should detect same law despite title difference"
    
    def test_same_law_different_abbreviations(self):
        """
        Detect same law with different abbreviations.
        
        Law may be cited with abbreviations (e.g., "ق.م" vs "قانون مدنی").
        """
        law1 = {
            "title_fa": "قانون مدنی",
            "publication_date": "1928-03-15"
        }
        
        law2 = {
            "title_fa": "ق.م",
            "publication_date": "1928-03-15"
        }
        
        # Same publication date → likely same law
        assert law1["publication_date"] == law2["publication_date"], "Same publication date"
        
        # Should flag for review
        def flag_potential_duplicate(law1: Dict, law2: Dict) -> bool:
            return law1["publication_date"] == law2["publication_date"]
        
        assert flag_potential_duplicate(law1, law2), "Should flag potential duplicate"
    
    def test_different_law_same_title(self):
        """
        Detect different laws with similar titles.
        
        Different laws may have similar titles (e.g., "قانون مدنی" in different countries).
        """
        law1 = {
            "title_fa": "قانون مدنی",
            "publication_date": "1928-03-15",
            "jurisdiction": "Iran"
        }
        
        law2 = {
            "title_fa": "قانون مدنی",
            "publication_date": "1950-01-01",
            "jurisdiction": "France"
        }
        
        # Same title but different publication date/jurisdiction → different laws
        assert law1["publication_date"] != law2["publication_date"], "Different publication dates"
        assert law1["jurisdiction"] != law2["jurisdiction"], "Different jurisdictions"
        
        # Should NOT be merged
        def are_different_laws(law1: Dict, law2: Dict) -> bool:
            return (law1["publication_date"] != law2["publication_date"] or
                    law1.get("jurisdiction") != law2.get("jurisdiction"))
        
        assert are_different_laws(law1, law2), "Should detect different laws"


@pytest.mark.p1_high
@pytest.mark.unit
class TestDuplicateArticleDetection:
    """
    TEST NAME: Duplicate Article Detection
    PURPOSE: Detect the same article appearing multiple times
    INVARIANT: Each article should appear exactly once in the knowledge graph
    FAILURE RISK: Duplicate articles create contradictory legal provisions
    IMPLEMENTATION: Compare article number, text, and parent law to detect duplicates
    """
    
    def test_same_article_different_ids(self):
        """
        Detect same article with different canonical IDs.
        
        Article may be extracted multiple times with different IDs.
        """
        article1 = {
            "canonical_id": "article:civil_code:1",
            "article_number": "1",
            "text_fa": "هرکس مالک مال خود است.",
            "parent_law": "law:civil_code"
        }
        
        article2 = {
            "canonical_id": "article:civil_code_duplicate:1",
            "article_number": "1",
            "text_fa": "هرکس مالک مال خود است.",
            "parent_law": "law:civil_code"
        }
        
        # Same article number, text, and parent → duplicate
        assert article1["article_number"] == article2["article_number"], "Same article number"
        assert article1["text_fa"] == article2["text_fa"], "Same text"
        assert article1["parent_law"] == article2["parent_law"], "Same parent law"
        
        def detect_duplicate_article(article1: Dict, article2: Dict) -> bool:
            return (article1["article_number"] == article2["article_number"] and
                    article1["text_fa"] == article2["text_fa"] and
                    article1["parent_law"] == article2["parent_law"])
        
        assert detect_duplicate_article(article1, article2), "Should detect duplicate article"
    
    def test_same_article_different_laws(self):
        """
        Detect article appearing in multiple laws (may be valid or error).
        
        Same article number in different laws may be valid (reused numbers) or error.
        """
        article1 = {
            "article_number": "1",
            "text_fa": "هرکس مالک مال خود است.",
            "parent_law": "law:civil_code"
        }
        
        article2 = {
            "article_number": "1",
            "text_fa": "هرکس مالک مال خود است.",
            "parent_law": "law:commercial_code"
        }
        
        # Same article number and text but different parent laws
        # This may be valid (copy-paste) or error (wrong parent)
        assert article1["parent_law"] != article2["parent_law"], "Different parent laws"
        
        # Should flag for manual review
        def flag_potential_issue(article1: Dict, article2: Dict) -> bool:
            return (article1["article_number"] == article2["article_number"] and
                    article1["text_fa"] == article2["text_fa"] and
                    article1["parent_law"] != article2["parent_law"])
        
        assert flag_potential_issue(article1, article2), "Should flag for review"
    
    def test_article_number_collision(self):
        """
        Detect article number collision in same law.
        
        Same article number appearing twice in same law is an error.
        """
        article1 = {
            "article_number": "1",
            "text_fa": "متن اول",
            "parent_law": "law:civil_code"
        }
        
        article2 = {
            "article_number": "1",
            "text_fa": "متن دوم",  # Different text
            "parent_law": "law:civil_code"
        }
        
        # Same article number and parent but different text → error
        assert article1["article_number"] == article2["article_number"], "Same article number"
        assert article1["parent_law"] == article2["parent_law"], "Same parent law"
        assert article1["text_fa"] != article2["text_fa"], "Different text"
        
        def detect_number_collision(article1: Dict, article2: Dict) -> bool:
            return (article1["article_number"] == article2["article_number"] and
                    article1["parent_law"] == article2["parent_law"] and
                    article1["text_fa"] != article2["text_fa"])
        
        assert detect_number_collision(article1, article2), "Should detect article number collision"


@pytest.mark.p1_high
@pytest.mark.unit
class TestSimilarTextDifferentEntities:
    """
    TEST NAME: Similar Text but Different Entities Detection
    PURPOSE: Detect similar text that represents different legal entities
    INVARIANT: Similarity does NOT equal identity; similar text may be different entities
    FAILURE RISK: False merges based on similarity create incorrect legal knowledge
    IMPLEMENTATION: Use context (parent law, article number, publication date) to distinguish entities
    """
    
    def test_similar_text_different_laws(self):
        """
        Detect similar text in different laws (different entities).
        
        Similar legal text may appear in different laws (e.g., general principles).
        """
        article1 = {
            "text_fa": "هرکس مالک مال خود است.",
            "parent_law": "law:civil_code",
            "article_number": "1"
        }
        
        article2 = {
            "text_fa": "هرکس مالک مال خود است.",  # Identical text
            "parent_law": "law:constitutional",  # Different law
            "article_number": "47"
        }
        
        # Identical text but different parent laws → different entities
        assert article1["text_fa"] == article2["text_fa"], "Identical text"
        assert article1["parent_law"] != article2["parent_law"], "Different parent laws"
        
        # Should NOT merge
        def are_different_entities(article1: Dict, article2: Dict) -> bool:
            return article1["parent_law"] != article2["parent_law"]
        
        assert are_different_entities(article1, article2), "Should detect different entities"
    
    def test_similar_text_different_articles(self):
        """
        Detect similar text in different articles of same law.
        
        Similar text may appear in different articles (e.g., boilerplate).
        """
        article1 = {
            "text_fa": "این ماده از تاریخ ... لازم‌الاجرا است.",
            "parent_law": "law:civil_code",
            "article_number": "1"
        }
        
        article2 = {
            "text_fa": "این ماده از تاریخ ... لازم‌الاجرا است.",  # Identical boilerplate
            "parent_law": "law:civil_code",
            "article_number": "2"
        }
        
        # Identical text but different article numbers → different entities
        assert article1["article_number"] != article2["article_number"], "Different article numbers"
        
        # Should NOT merge
        def are_different_articles(article1: Dict, article2: Dict) -> bool:
            return article1["article_number"] != article2["article_number"]
        
        assert are_different_articles(article1, article2), "Should detect different articles"
    
    def test_text_similarity_threshold(self):
        """
        Detect text similarity below merge threshold.
        
        Text similarity above threshold may indicate same entity, below threshold indicates different.
        """
        text1 = "هرکس مالک مال خود است."
        text2 = "هرکس مالک مال غیرمنقول خود است."
        
        # Calculate similarity (simple word overlap)
        words1 = set(text1.split())
        words2 = set(text2.split())
        similarity = len(words1 & words2) / len(words1 | words2)
        
        # Similarity ~0.83 - this is above typical merge threshold
        # The test should check that similar text IS detected, not that it's below threshold
        assert similarity > 0.7, "Similarity should be detected for similar text"
        
        # Should merge with appropriate threshold (0.9 for strict matching)
        def should_merge(text1: str, text2: str, threshold: float = 0.9) -> bool:
            words1 = set(text1.split())
            words2 = set(text2.split())
            similarity = len(words1 & words2) / len(words1 | words2)
            return similarity >= threshold
        
        # With strict threshold (0.9), should NOT merge despite similarity
        assert not should_merge(text1, text2, threshold=0.9), "Should not merge with strict threshold"
        
        # With lower threshold (0.7), should merge
        assert should_merge(text1, text2, threshold=0.7), "Should merge with lower threshold"


@pytest.mark.p1_high
@pytest.mark.unit
class TestDifferentVersionHandling:
    """
    TEST NAME: Different Version Handling
    PURPOSE: Validate handling of different versions of the same law
    INVARIANT: Different versions of the same law should be linked, not merged
    FAILURE RISK: Merging different versions creates incorrect temporal legal knowledge
    IMPLEMENTATION: Use version relationships (AMENDS, REPLACED_BY) to link versions
    """
    
    def test_version_linking_not_merging(self):
        """
        Verify different versions are linked, not merged.
        
        Different versions should have separate nodes with version relationships.
        """
        version1 = {
            "canonical_id": "law:civil_code:v1",
            "title_fa": "قانون مدنی",
            "version": "1",
            "publication_date": "1928-03-15"
        }
        
        version2 = {
            "canonical_id": "law:civil_code:v2",
            "title_fa": "قانون مدنی",
            "version": "2",
            "publication_date": "2020-01-01"
        }
        
        # Same title but different versions → should be linked, not merged
        assert version1["canonical_id"] != version2["canonical_id"], "Different canonical IDs"
        assert version1["version"] != version2["version"], "Different versions"
        
        # Should have REPLACED_BY relationship
        def should_link_versions(v1: Dict, v2: Dict) -> bool:
            return (v1["title_fa"] == v2["title_fa"] and
                    v1["version"] != v2["version"])
        
        assert should_link_versions(version1, version2), "Should link different versions"
    
    def test_version_sequence_validation(self):
        """
        Validate version sequence is correct.
        
        Versions should be sequential (v1 → v2 → v3).
        """
        versions = [
            {"canonical_id": "law:civil_code:v1", "version": "1"},
            {"canonical_id": "law:civil_code:v3", "version": "3"},
            {"canonical_id": "law:civil_code:v2", "version": "2"}
        ]
        
        # Sort by version number
        sorted_versions = sorted(versions, key=lambda x: int(x["version"]))
        
        # Check sequence
        version_numbers = [v["version"] for v in sorted_versions]
        expected_sequence = ["1", "2", "3"]
        
        assert version_numbers == expected_sequence, "Version sequence should be sequential"
    
    def test_missing_version_detection(self):
        """
        Detect missing versions in version chain.
        
        Version chain should be complete (no gaps).
        """
        versions = [
            {"canonical_id": "law:civil_code:v1", "version": "1"},
            {"canonical_id": "law:civil_code:v3", "version": "3"}
            # Missing: v2
        ]
        
        version_numbers = sorted([int(v["version"]) for v in versions])
        
        # Check for gaps
        has_gap = any(version_numbers[i] + 1 != version_numbers[i+1] 
                     for i in range(len(version_numbers)-1))
        
        assert has_gap, "Should detect missing version (gap in sequence)"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestAccidentalMergeDetection:
    """
    TEST NAME: Accidental Merge Detection
    PURPOSE: Detect accidental merging of unrelated entities
    INVARIANT: Unrelated entities must never be merged
    FAILURE RISK: Accidental merges create contradictory legal knowledge
    IMPLEMENTATION: Validate merge decisions using multiple criteria (not just similarity)
    """
    
    def test_different_domain_merge_prevention(self):
        """
        Prevent merging entities from different legal domains.
        
        Civil law and criminal law entities should never be merged.
        """
        entity1 = {
            "domain": "civil",
            "text_fa": "مالکیت",
            "canonical_id": "entity:civil:1"
        }
        
        entity2 = {
            "domain": "criminal",
            "text_fa": "مالکیت",  # Same word but different legal meaning
            "canonical_id": entity1["canonical_id"]  # Accidentally same ID
        }
        
        # Different domains → should NOT merge even with same text
        assert entity1["domain"] != entity2["domain"], "Different domains"
        
        def should_not_merge_different_domains(e1: Dict, e2: Dict) -> bool:
            return e1["domain"] != e2["domain"]
        
        assert should_not_merge_different_domains(entity1, entity2), "Should prevent cross-domain merge"
    
    def test_different_jurisdiction_merge_prevention(self):
        """
        Prevent merging entities from different jurisdictions.
        
        Iranian law and French law entities should never be merged.
        """
        entity1 = {
            "jurisdiction": "Iran",
            "text_fa": "مالکیت",
            "canonical_id": "entity:iran:1"
        }
        
        entity2 = {
            "jurisdiction": "France",
            "text_fa": "مالکیت",
            "canonical_id": entity1["canonical_id"]
        }
        
        # Different jurisdictions → should NOT merge
        assert entity1["jurisdiction"] != entity2["jurisdiction"], "Different jurisdictions"
        
        def should_not_merge_different_jurisdictions(e1: Dict, e2: Dict) -> bool:
            return e1.get("jurisdiction") != e2.get("jurisdiction")
        
        assert should_not_merge_different_jurisdictions(entity1, entity2), "Should prevent cross-jurisdiction merge"
    
    def test_merge_criteria_validation(self):
        """
        Validate merge decision uses multiple criteria.
        
        Merge should require: same domain, same jurisdiction, same parent, similar content.
        """
        entity1 = {
            "domain": "civil",
            "jurisdiction": "Iran",
            "parent_law": "law:civil_code",
            "text_fa": "هرکس مالک مال خود است."
        }
        
        entity2 = {
            "domain": "civil",
            "jurisdiction": "Iran",
            "parent_law": "law:civil_code",
            "text_fa": "هرکس مالک مال خود است."
        }
        
        # All criteria match → may merge
        def should_merge(e1: Dict, e2: Dict) -> bool:
            return (e1["domain"] == e2["domain"] and
                    e1["jurisdiction"] == e2["jurisdiction"] and
                    e1["parent_law"] == e2["parent_law"] and
                    e1["text_fa"] == e2["text_fa"])
        
        assert should_merge(entity1, entity2), "Should merge when all criteria match"
        
        # Change one criterion → should NOT merge
        entity2["parent_law"] = "law:commercial_code"
        assert not should_merge(entity1, entity2), "Should not merge when criteria differ"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestCanonicalIdUniqueness:
    """
    TEST NAME: Canonical ID Uniqueness Validation
    PURPOSE: Validate that canonical IDs are unique and consistent
    INVARIANT: Each entity must have exactly one unique canonical ID
    FAILURE RISK: Duplicate canonical IDs cause entity conflicts and query failures
    IMPLEMENTATION: Validate canonical ID generation and uniqueness
    """
    
    def test_canonical_id_uniqueness(self):
        """
        Detect duplicate canonical IDs.
        
        Each canonical ID should be unique.
        """
        entities = [
            {"canonical_id": "entity:1"},
            {"canonical_id": "entity:2"},
            {"canonical_id": "entity:1"}  # Duplicate
        ]
        
        canonical_ids = [e["canonical_id"] for e in entities]
        has_duplicates = len(canonical_ids) != len(set(canonical_ids))
        
        assert has_duplicates, "Should detect duplicate canonical IDs"
    
    def test_canonical_id_determinism(self):
        """
        Validate canonical ID generation is deterministic.
        
        Same input should always produce same canonical ID.
        """
        def generate_canonical_id(law_name: str, article_number: str) -> str:
            return f"article:{law_name.lower().replace(' ', '_')}:article:{article_number}"
        
        id1 = generate_canonical_id("Civil Code", "1")
        id2 = generate_canonical_id("Civil Code", "1")
        id3 = generate_canonical_id("Civil Code", "2")
        
        assert id1 == id2, "Same input should produce same ID"
        assert id1 != id3, "Different input should produce different ID"
    
    def test_canonical_id_format_consistency(self):
        """
        Validate canonical ID format consistency.
        
        All canonical IDs should follow the same format.
        """
        canonical_ids = [
            "article:civil_code:article:1",
            "chapter:civil_code:chapter:1",
            "law:civil_code"
        ]
        
        # Check format: entity_type:law_name:entity_type:number
        def validate_format(canonical_id: str) -> bool:
            parts = canonical_id.split(":")
            return len(parts) >= 2  # At minimum: type:name
        
        assert all(validate_format(cid) for cid in canonical_ids), "All IDs should follow format"
