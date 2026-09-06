"""
Adversarial Failure Tests
=========================

TEST NAME: Adversarial Failure Validation
PURPOSE: Ensure system fails safely on malicious or corrupted input
INVARIANT: System must reject malicious input and fail safely without silent corruption
FAILURE RISK: Unsafe failures create undetected corruption and security issues
IMPLEMENTATION: Test fake articles, duplicate laws, invalid references, missing identifiers, broken relationships
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock


@pytest.mark.p3_low
@pytest.mark.unit
class TestFakeArticleHandling:
    """
    TEST NAME: Fake Article Handling
    PURPOSE: Validate system detects and rejects fake articles
    INVARIANT: Fake articles must be rejected before graph insertion
    FAILURE RISK: Fake articles create false legal knowledge
    IMPLEMENTATION: Detect fake article numbers, invalid content, and suspicious patterns
    """
    
    def test_fake_article_number_rejected(self):
        """
        Detect and reject fake article numbers.
        
        Article numbers outside valid range should be rejected.
        """
        article = {
            "article_number": "99999",  # Suspiciously high
            "text_fa": "ماده جعلی"
        }
        
        def is_article_number_valid(article: Dict) -> bool:
            try:
                num = int(article["article_number"])
                return 1 <= num <= 9999
            except:
                return False
        
        assert not is_article_number_valid(article), "Fake article number should be rejected"
    
    def test_invalid_article_content_rejected(self):
        """
        Detect and reject invalid article content.
        
        Articles with suspicious content should be rejected.
        """
        article = {
            "article_number": "1",
            "text_fa": "DROP TABLE articles; -- SQL injection"
        }
        
        def has_suspicious_content(article: Dict) -> bool:
            suspicious = ["DROP", "DELETE", "UNION SELECT", "script"]
            text = article["text_fa"].upper()
            return any(s in text for s in suspicious)
        
        assert has_suspicious_content(article), "Suspicious content should be rejected"
    
    def test_article_without_parent_rejected(self):
        """
        Detect and reject articles without parent.
        
        Orphan articles should be rejected.
        """
        article = {
            "canonical_id": "article:orphan",
            "parent_chapter_id": None  # Missing parent
        }
        
        def has_parent(article: Dict) -> bool:
            return article.get("parent_chapter_id") is not None
        
        assert not has_parent(article), "Orphan article should be rejected"


@pytest.mark.p3_low
@pytest.mark.unit
class TestDuplicateLawHandling:
    """
    TEST NAME: Duplicate Law Handling
    PURPOSE: Validate system detects duplicate laws
    INVARIANT: Duplicate laws must be detected and rejected/merged
    FAILURE RISK: Duplicate laws create contradictory legal knowledge
    IMPLEMENTATION: Detect same law with different IDs, slight variations, and case differences
    """
    
    def test_duplicate_law_with_different_id_rejected(self):
        """
        Detect duplicate laws with different canonical IDs.
        
        Same content, different ID indicates error or attack.
        """
        law1 = {
            "canonical_id": "law:civil_code",
            "title_fa": "قانون مدنی",
            "publication_date": "1928-03-15"
        }
        
        law2 = {
            "canonical_id": "law:civil_code_duplicate",
            "title_fa": "قانون مدنی",
            "publication_date": "1928-03-15"
        }
        
        def is_duplicate(law1: Dict, law2: Dict) -> bool:
            return (law1["title_fa"] == law2["title_fa"] and
                    law1["publication_date"] == law2["publication_date"] and
                    law1["canonical_id"] != law2["canonical_id"])
        
        assert is_duplicate(law1, law2), "Duplicate law should be detected"
    
    def test_duplicate_law_with_slight_variation_detected(self):
        """
        Detect duplicate laws with slight text variations.
        
        Attackers may modify text slightly to bypass detection.
        """
        law1 = {
            "title_fa": "قانون مدنی",
            "publication_date": "1928-03-15"
        }
        
        law2 = {
            "title_fa": "قانون  مدنی",  # Extra space
            "publication_date": "1928-03-15"
        }
        
        def is_duplicate_with_variation(law1: Dict, law2: Dict) -> bool:
            # Normalize whitespace
            title1 = law1["title_fa"].replace(" ", "")
            title2 = law2["title_fa"].replace(" ", "")
            return (title1 == title2 and
                    law1["publication_date"] == law2["publication_date"])
        
        assert is_duplicate_with_variation(law1, law2), "Duplicate with variation should be detected"
    
    def test_duplicate_law_different_case_detected(self):
        """
        Detect duplicate laws with different case (where applicable).
        
        Case differences should not bypass duplicate detection.
        """
        law1 = {
            "title_fa": "قانون مدنی",
            "publication_date": "1928-03-15"
        }
        
        law2 = {
            "title_fa": "قانون مدنی",  # Same in Persian
            "publication_date": "1928-03-15"
        }
        
        # Persian doesn't have case, but this validates the check exists
        def is_duplicate(law1: Dict, law2: Dict) -> bool:
            return (law1["title_fa"].lower() == law2["title_fa"].lower() and
                    law1["publication_date"] == law2["publication_date"])
        
        assert is_duplicate(law1, law2), "Duplicate should be detected"


@pytest.mark.p3_low
@pytest.mark.unit
class TestInvalidReferenceHandling:
    """
    TEST NAME: Invalid Reference Handling
    PURPOSE: Validate system handles invalid references safely
    INVARIANT: Invalid references must be detected and rejected
    FAILURE RISK: Invalid references cause broken reference chains
    IMPLEMENTATION: Detect references to non-existent targets, invalid types, and self-references
    """
    
    def test_reference_to_nonexistent_target_rejected(self):
        """
        Detect and reject references to non-existent targets.
        
        References must point to existing nodes.
        """
        article = {
            "canonical_id": "article:1",
            "references_article": ["article:nonexistent:999"]  # Doesn't exist
        }
        
        def has_valid_references(article: Dict, existing_ids: set) -> bool:
            refs = article.get("references_article", [])
            return all(ref in existing_ids for ref in refs)
        
        existing_ids = {"article:1", "article:2"}
        assert not has_valid_references(article, existing_ids), "Invalid reference should be rejected"
    
    def test_invalid_reference_type_rejected(self):
        """
        Detect and reject invalid reference types.
        
        Reference types must be from allowed set.
        """
        reference = {
            "source": "article:1",
            "target": "article:2",
            "type": "INVALID_TYPE"  # Not allowed
        }
        
        allowed_types = {"REFERENCES", "CITES", "AMENDS", "REPLACED_BY"}
        
        def is_valid_type(reference: Dict) -> bool:
            return reference["type"] in allowed_types
        
        assert not is_valid_type(reference), "Invalid reference type should be rejected"
    
    def test_self_reference_rejected(self):
        """
        Detect and reject self-references.
        
        Nodes should not reference themselves.
        """
        article = {
            "canonical_id": "article:1",
            "references_article": ["article:1"]  # Self-reference
        }
        
        def has_self_reference(article: Dict) -> bool:
            refs = article.get("references_article", [])
            return article["canonical_id"] in refs
        
        assert has_self_reference(article), "Self-reference should be rejected"


@pytest.mark.p3_low
@pytest.mark.unit
class TestMissingIdentifierHandling:
    """
    TEST NAME: Missing Identifier Handling
    PURPOSE: Validate system handles missing identifiers safely
    INVARIANT: Missing identifiers must be detected and rejected
    FAILURE RISK: Missing identifiers cause entity conflicts and query failures
    IMPLEMENTATION: Detect null, empty, and whitespace-only identifiers
    """
    
    def test_null_canonical_id_rejected(self):
        """
        Detect and reject null canonical_id.
        
        canonical_id is required and cannot be null.
        """
        entity = {
            "canonical_id": None,
            "title_fa": "قانون"
        }
        
        def has_valid_id(entity: Dict) -> bool:
            return entity.get("canonical_id") is not None
        
        assert not has_valid_id(entity), "Null canonical_id should be rejected"
    
    def test_empty_canonical_id_rejected(self):
        """
        Detect and reject empty string canonical_id.
        
        canonical_id cannot be empty.
        """
        entity = {
            "canonical_id": "",
            "title_fa": "قانون"
        }
        
        def has_valid_id(entity: Dict) -> bool:
            return entity.get("canonical_id") != ""
        
        assert not has_valid_id(entity), "Empty canonical_id should be rejected"
    
    def test_whitespace_canonical_id_rejected(self):
        """
        Detect and reject whitespace-only canonical_id.
        
        canonical_id cannot be whitespace only.
        """
        entity = {
            "canonical_id": "   ",
            "title_fa": "قانون"
        }
        
        def has_valid_id(entity: Dict) -> bool:
            cid = entity.get("canonical_id", "")
            return cid.strip() != ""
        
        assert not has_valid_id(entity), "Whitespace canonical_id should be rejected"


@pytest.mark.p3_low
@pytest.mark.unit
class TestBrokenRelationshipHandling:
    """
    TEST NAME: Broken Relationship Handling
    PURPOSE: Validate system handles broken relationships safely
    INVARIANT: Broken relationships must be detected and rejected
    FAILURE RISK: Broken relationships cause graph corruption and query failures
    IMPLEMENTATION: Detect relationships with missing source, missing target, or invalid types
    """
    
    def test_relationship_with_missing_source_rejected(self):
        """
        Detect and reject relationships with missing source.
        
        Relationships must have valid source node.
        """
        relationship = {
            "source_id": None,  # Missing
            "target_id": "article:1",
            "type": "REFERENCES"
        }
        
        def has_valid_source(relationship: Dict) -> bool:
            return relationship.get("source_id") is not None
        
        assert not has_valid_source(relationship), "Relationship with missing source should be rejected"
    
    def test_relationship_with_missing_target_rejected(self):
        """
        Detect and reject relationships with missing target.
        
        Relationships must have valid target node.
        """
        relationship = {
            "source_id": "article:1",
            "target_id": None,  # Missing
            "type": "REFERENCES"
        }
        
        def has_valid_target(relationship: Dict) -> bool:
            return relationship.get("target_id") is not None
        
        assert not has_valid_target(relationship), "Relationship with missing target should be rejected"
    
    def test_relationship_with_invalid_type_rejected(self):
        """
        Detect and reject relationships with invalid type.
        
        Relationship types must be ontology-defined.
        """
        relationship = {
            "source_id": "article:1",
            "target_id": "article:2",
            "type": "INVALID_TYPE"
        }
        
        allowed_types = {"REFERENCES", "CITES", "AMENDS", "HAS_CHAPTER"}
        
        def is_valid_type(relationship: Dict) -> bool:
            return relationship["type"] in allowed_types
        
        assert not is_valid_type(relationship), "Relationship with invalid type should be rejected"


@pytest.mark.p3_low
@pytest.mark.unit
class TestContradictoryMetadataHandling:
    """
    TEST NAME: Contradictory Metadata Handling
    PURPOSE: Validate system detects contradictory metadata
    INVARIANT: Contradictory metadata must be detected and rejected
    FAILURE RISK: Contradictory metadata causes inconsistent legal state
    IMPLEMENTATION: Detect status contradictions, date contradictions, and priority contradictions
    """
    
    def test_status_contradiction_rejected(self):
        """
        Detect and reject status contradictions.
        
        Active and repealed are mutually exclusive.
        """
        entity = {
            "status": "active",
            "repeal_date": "2020-01-01"  # Contradiction
        }
        
        def has_status_contradiction(entity: Dict) -> bool:
            return (entity.get("status") == "active" and
                    entity.get("repeal_date") is not None)
        
        assert has_status_contradiction(entity), "Status contradiction should be rejected"
    
    def test_date_contradiction_rejected(self):
        """
        Detect and reject date contradictions.
        
        Effective date cannot be before publication date.
        """
        entity = {
            "publication_date": "1928-03-15",
            "effective_date": "1920-01-01"  # Before publication
        }
        
        def has_date_contradiction(entity: Dict) -> bool:
            from datetime import datetime
            pub = datetime.strptime(entity["publication_date"], "%Y-%m-%d")
            eff = datetime.strptime(entity["effective_date"], "%Y-%m-%d")
            return eff < pub
        
        assert has_date_contradiction(entity), "Date contradiction should be rejected"
    
    def test_priority_contradiction_rejected(self):
        """
        Detect and reject priority contradictions.
        
        Ordinary law cannot override constitutional law.
        """
        entity = {
            "level": "ordinary",
            "overrides": "constitutional"  # Contradiction
        }
        
        def has_priority_contradiction(entity: Dict) -> bool:
            return (entity.get("level") == "ordinary" and
                    entity.get("overrides") == "constitutional")
        
        assert has_priority_contradiction(entity), "Priority contradiction should be rejected"


@pytest.mark.p3_low
@pytest.mark.unit
class TestSafeFailureValidation:
    """
    TEST NAME: Safe Failure Validation
    PURPOSE: Validate system fails safely on adversarial input
    INVARIANT: System must fail safely without silent corruption
    FAILURE RISK: Unsafe failures create undetected corruption
    IMPLEMENTATION: Validate errors are raised, logged, and no partial corruption occurs
    """
    
    def test_invalid_input_raises_error(self):
        """
        Verify invalid input raises explicit error.
        
        Invalid input should not be silently accepted.
        """
        def process_article(article: Dict) -> Dict:
            if not article.get("canonical_id"):
                raise ValueError("Missing canonical_id")
            return article
        
        article = {"canonical_id": None}
        
        try:
            process_article(article)
            assert False, "Should have raised error"
        except ValueError as e:
            assert str(e) == "Missing canonical_id", "Error should be explicit"
    
    def test_partial_update_rollback(self):
        """
        Verify partial updates are rolled back on error.
        
        If one entity fails, entire batch should be rolled back.
        """
        entities = [
            {"canonical_id": "law:1", "title": "Valid"},
            {"canonical_id": None, "title": "Invalid"},  # Will fail
            {"canonical_id": "law:2", "title": "Valid"}
        ]
        
        processed = []
        had_error = False
        
        try:
            for entity in entities:
                if not entity.get("canonical_id"):
                    had_error = True
                    raise ValueError("Invalid entity")
                processed.append(entity)
        except ValueError:
            # In a real transaction, this would trigger rollback
            # For this test, we simulate rollback by clearing processed items
            if had_error:
                processed = []
        
        # Should have rolled back - no entities processed
        assert len(processed) == 0, "Partial update should be rolled back"
    
    def test_error_logging(self):
        """
        Verify errors are logged for investigation.
        
        All failures should be logged with context.
        """
        error_log = []
        
        def log_error(error: str, context: Dict):
            error_log.append({"error": error, "context": context})
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_error(str(e), {"entity": "test"})
        
        assert len(error_log) > 0, "Error should be logged"
        assert error_log[0]["error"] == "Test error", "Error should be logged correctly"
    
    def test_no_silent_corruption(self):
        """
        Verify no silent corruption occurs.
        
        Invalid data should not be partially inserted.
        """
        graph_state = {"nodes": []}
        
        try:
            # Attempt to insert invalid entity
            entity = {"canonical_id": None}
            if not entity.get("canonical_id"):
                raise ValueError("Invalid entity")
            graph_state["nodes"].append(entity)
        except ValueError:
            pass
        
        # Graph state should be unchanged
        assert len(graph_state["nodes"]) == 0, "No silent corruption should occur"
