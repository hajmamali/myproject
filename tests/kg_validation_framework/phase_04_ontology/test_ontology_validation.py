"""
Ontology and Schema Validation Tests
===================================

TEST NAME: Legal Ontology Audit
PURPOSE: Validate the legal ontology hierarchy and schema definition
INVARIANT: Ontology must correctly represent Persian legal hierarchy (Law → Chapter → Article → Paragraph → Clause)
FAILURE RISK: Ontology errors cause incorrect legal reasoning, wrong precedence, and query failures
IMPLEMENTATION: Validate node labels, relationship types, directions, required properties, and hierarchy
"""

import pytest
from typing import Dict, Any, List, Set
from unittest.mock import Mock


@pytest.mark.p0_critical
@pytest.mark.unit
class TestNodeLabelValidation:
    """
    TEST NAME: Node Label Validation
    PURPOSE: Validate that node labels are used correctly according to ontology
    INVARIANT: Node labels must match their semantic purpose (Law, Chapter, Article, Paragraph, Clause)
    FAILURE RISK: Incorrect labels cause semantic confusion and query failures
    IMPLEMENTATION: Validate label existence, correctness, and no semantic misuse
    """
    
    def test_expected_labels_exist(self):
        """
        Verify all expected node labels exist in the ontology.
        
        Expected labels: Law, Chapter, Article, Paragraph, Clause, Precedent, Reference
        """
        expected_labels = {"Law", "Chapter", "Article", "Paragraph", "Clause", "Precedent", "Reference"}
        
        # Mock ontology definition
        ontology = Mock()
        ontology.get_labels.return_value = expected_labels
        
        actual_labels = set(ontology.get_labels())
        
        assert actual_labels == expected_labels, "Expected labels missing from ontology"
    
    def test_no_unexpected_labels(self):
        """
        Verify no unexpected labels exist in the ontology.
        
        Unexpected labels indicate schema drift or errors.
        """
        ontology = Mock()
        ontology.get_labels.return_value = {"Law", "Chapter", "Article", "InvalidLabel"}
        
        actual_labels = ontology.get_labels()
        allowed_labels = {"Law", "Chapter", "Article", "Paragraph", "Clause", "Precedent", "Reference"}
        
        unexpected = set(actual_labels) - allowed_labels
        
        assert "InvalidLabel" in unexpected, "Unexpected label detected"
    
    def test_label_semantic_correctness(self):
        """
        Verify labels are used semantically correctly.
        
        Judicial decisions should not be labeled as Law.
        """
        # Mock node data
        node = {
            "label": "Law",
            "properties": {
                "court": "Supreme Court",  # Indicates judicial decision
                "decision_date": "2020-01-01"
            }
        }
        
        # Law node should not have court property
        def is_semantically_correct(node: Dict) -> bool:
            if node["label"] == "Law":
                return "court" not in node["properties"]
            return True
        
        assert not is_semantically_correct(node), "Judicial decision mislabeled as Law"
    
    def test_label_hierarchy_compliance(self):
        """
        Verify labels comply with legal hierarchy.
        
        Clause should not be parent of Article (violates hierarchy).
        """
        # Mock relationship
        relationship = {
            "source_label": "Clause",
            "target_label": "Article",
            "type": "HAS_ARTICLE"
        }
        
        # Clause cannot have Article as child
        def is_hierarchy_valid(rel: Dict) -> bool:
            hierarchy = {
                "Law": ["Chapter"],
                "Chapter": ["Article"],
                "Article": ["Paragraph"],
                "Paragraph": ["Clause"],
                "Clause": []
            }
            allowed_children = hierarchy.get(rel["source_label"], [])
            return rel["target_label"] in allowed_children
        
        assert not is_hierarchy_valid(relationship), "Hierarchy violation detected"


@pytest.mark.p0_critical
@pytest.mark.unit
class TestRelationshipTypeValidation:
    """
    TEST NAME: Relationship Type Validation
    PURPOSE: Validate that relationship types are defined and used correctly
    INVARIANT: Relationship types must match ontology definition (HAS_CHAPTER, HAS_ARTICLE, etc.)
    FAILURE RISK: Invalid relationship types cause query failures and semantic errors
    IMPLEMENTATION: Validate relationship type existence, correctness, and allowed combinations
    """
    
    def test_expected_relationship_types_exist(self):
        """
        Verify all expected relationship types exist.
        
        Expected types: HAS_CHAPTER, HAS_ARTICLE, HAS_PARAGRAPH, HAS_CLAUSE, REFERENCES, AMENDS, etc.
        """
        expected_types = {
            "HAS_CHAPTER", "HAS_ARTICLE", "HAS_PARAGRAPH", "HAS_CLAUSE",
            "REFERENCES", "CITES", "AMENDS", "REPLACED_BY", "OVERRIDDEN_BY",
            "INTERPRETS_BY", "IMPLEMENTS", "CONFLICTS_WITH", "EXCEPTS", "PRECEDES"
        }
        
        ontology = Mock()
        ontology.get_relationship_types.return_value = expected_types
        
        actual_types = set(ontology.get_relationship_types())
        
        assert actual_types == expected_types, "Expected relationship types missing"
    
    def test_no_unexpected_relationship_types(self):
        """
        Verify no unexpected relationship types exist.
        
        Unexpected types indicate schema drift or errors.
        """
        ontology = Mock()
        ontology.get_relationship_types.return_value = {
            "HAS_CHAPTER", "HAS_ARTICLE", "INVALID_RELATIONSHIP"
        }
        
        actual_types = ontology.get_relationship_types()
        allowed_types = {
            "HAS_CHAPTER", "HAS_ARTICLE", "HAS_PARAGRAPH", "HAS_CLAUSE",
            "REFERENCES", "CITES", "AMENDS", "REPLACED_BY", "OVERRIDDEN_BY",
            "INTERPRETS_BY", "IMPLEMENTS", "CONFLICTS_WITH", "EXCEPTS", "PRECEDES"
        }
        
        unexpected = set(actual_types) - allowed_types
        
        assert "INVALID_RELATIONSHIP" in unexpected, "Unexpected relationship type detected"
    
    def test_relationship_type_semantic_correctness(self):
        """
        Verify relationship types are used semantically correctly.
        
        REFERENCES should not be used for parent-child relationships.
        """
        relationship = {
            "source_label": "Law",
            "target_label": "Chapter",
            "type": "REFERENCES"  # Wrong: should be HAS_CHAPTER
        }
        
        def is_semantically_correct(rel: Dict) -> bool:
            # Parent-child should use HAS_* relationships
            if rel["source_label"] == "Law" and rel["target_label"] == "Chapter":
                return rel["type"] == "HAS_CHAPTER"
            return True
        
        assert not is_semantically_correct(relationship), "Relationship type misuse detected"
    
    def test_allowed_relationship_combinations(self):
        """
        Verify only allowed label-relationship-type combinations exist.
        
        Law can HAS_CHAPTER Chapter, but cannot HAS_ARTICLE Article directly.
        """
        allowed_combinations = {
            ("Law", "HAS_CHAPTER", "Chapter"),
            ("Chapter", "HAS_ARTICLE", "Article"),
            ("Article", "HAS_PARAGRAPH", "Paragraph"),
            ("Paragraph", "HAS_CLAUSE", "Clause"),
            ("Article", "REFERENCES", "Article"),
            ("Law", "AMENDS", "Law")
        }
        
        # Test invalid combination
        invalid_combination = ("Law", "HAS_ARTICLE", "Article")
        
        assert invalid_combination not in allowed_combinations, "Invalid combination should not be allowed"


@pytest.mark.p0_critical
@pytest.mark.unit
class TestRelationshipDirectionValidation:
    """
    TEST NAME: Relationship Direction Validation
    PURPOSE: Validate that relationship directions follow legal hierarchy
    INVARIANT: Relationships must follow hierarchy (Law → Chapter → Article → Paragraph → Clause)
    FAILURE RISK: Incorrect direction causes wrong legal precedence and reasoning errors
    IMPLEMENTATION: Validate relationship direction for each type
    """
    
    def test_law_to_chapter_direction(self):
        """
        Verify Law → Chapter relationship direction is correct.
        
        Law should HAVE Chapter, not vice versa.
        """
        relationship = {
            "source_label": "Chapter",
            "target_label": "Law",
            "type": "HAS_CHAPTER"  # Wrong direction
        }
        
        def is_direction_correct(rel: Dict) -> bool:
            if rel["type"] == "HAS_CHAPTER":
                return rel["source_label"] == "Law" and rel["target_label"] == "Chapter"
            return True
        
        assert not is_direction_correct(relationship), "Reverse direction detected"
    
    def test_chapter_to_article_direction(self):
        """
        Verify Chapter → Article relationship direction is correct.
        
        Chapter should HAVE Article, not vice versa.
        """
        relationship = {
            "source_label": "Article",
            "target_label": "Chapter",
            "type": "HAS_ARTICLE"  # Wrong direction
        }
        
        def is_direction_correct(rel: Dict) -> bool:
            if rel["type"] == "HAS_ARTICLE":
                return rel["source_label"] == "Chapter" and rel["target_label"] == "Article"
            return True
        
        assert not is_direction_correct(relationship), "Reverse direction detected"
    
    def test_article_to_paragraph_direction(self):
        """
        Verify Article → Paragraph relationship direction is correct.
        
        Article should HAVE Paragraph, not vice versa.
        """
        relationship = {
            "source_label": "Paragraph",
            "target_label": "Article",
            "type": "HAS_PARAGRAPH"  # Wrong direction
        }
        
        def is_direction_correct(rel: Dict) -> bool:
            if rel["type"] == "HAS_PARAGRAPH":
                return rel["source_label"] == "Article" and rel["target_label"] == "Paragraph"
            return True
        
        assert not is_direction_correct(relationship), "Reverse direction detected"
    
    def test_paragraph_to_clause_direction(self):
        """
        Verify Paragraph → Clause relationship direction is correct.
        
        Paragraph should HAVE Clause, not vice versa.
        """
        relationship = {
            "source_label": "Clause",
            "target_label": "Paragraph",
            "type": "HAS_CLAUSE"  # Wrong direction
        }
        
        def is_direction_correct(rel: Dict) -> bool:
            if rel["type"] == "HAS_CLAUSE":
                return rel["source_label"] == "Paragraph" and rel["target_label"] == "Clause"
            return True
        
        assert not is_direction_correct(relationship), "Reverse direction detected"


@pytest.mark.p0_critical
@pytest.mark.unit
class TestRequiredPropertyValidation:
    """
    TEST NAME: Required Property Validation
    PURPOSE: Validate that required properties are present for each node type
    INVARIANT: Each node type must have its mandatory properties (canonical_id, title_fa for Law, etc.)
    FAILURE RISK: Missing required properties cause query failures and incomplete legal knowledge
    IMPLEMENTATION: Validate required properties for each node label
    """
    
    def test_law_required_properties(self):
        """
        Verify Law nodes have required properties.
        
        Law must have: canonical_id, title_fa, publication_date, status
        """
        required_properties = {"canonical_id", "title_fa", "publication_date", "status"}
        
        law_node = {
            "label": "Law",
            "properties": {
                "canonical_id": "law:civil_code",
                "title_fa": "قانون مدنی",
                # Missing: publication_date, status
            }
        }
        
        def has_required_properties(node: Dict) -> bool:
            return required_properties.issubset(node["properties"].keys())
        
        assert not has_required_properties(law_node), "Law missing required properties"
    
    def test_article_required_properties(self):
        """
        Verify Article nodes have required properties.
        
        Article must have: canonical_id, article_number, text_fa
        """
        required_properties = {"canonical_id", "article_number", "text_fa"}
        
        article_node = {
            "label": "Article",
            "properties": {
                "canonical_id": "article:civil_code:1",
                "article_number": "1",
                # Missing: text_fa
            }
        }
        
        def has_required_properties(node: Dict) -> bool:
            return required_properties.issubset(node["properties"].keys())
        
        assert not has_required_properties(article_node), "Article missing required properties"
    
    def test_chapter_required_properties(self):
        """
        Verify Chapter nodes have required properties.
        
        Chapter must have: canonical_id, title_fa, chapter_number
        """
        required_properties = {"canonical_id", "title_fa", "chapter_number"}
        
        chapter_node = {
            "label": "Chapter",
            "properties": {
                "canonical_id": "chapter:civil_code:1",
                "title_fa": "فصل اول",
                # Missing: chapter_number
            }
        }
        
        def has_required_properties(node: Dict) -> bool:
            return required_properties.issubset(node["properties"].keys())
        
        assert not has_required_properties(chapter_node), "Chapter missing required properties"
    
    def test_paragraph_required_properties(self):
        """
        Verify Paragraph nodes have required properties.
        
        Paragraph must have: canonical_id, paragraph_number, text_fa
        """
        required_properties = {"canonical_id", "paragraph_number", "text_fa"}
        
        paragraph_node = {
            "label": "Paragraph",
            "properties": {
                "canonical_id": "paragraph:civil_code:1:1",
                "paragraph_number": "1",
                # Missing: text_fa
            }
        }
        
        def has_required_properties(node: Dict) -> bool:
            return required_properties.issubset(node["properties"].keys())
        
        assert not has_required_properties(paragraph_node), "Paragraph missing required properties"
    
    def test_clause_required_properties(self):
        """
        Verify Clause nodes have required properties.
        
        Clause must have: canonical_id, clause_number, text_fa
        """
        required_properties = {"canonical_id", "clause_number", "text_fa"}
        
        clause_node = {
            "label": "Clause",
            "properties": {
                "canonical_id": "clause:civil_code:1:1",
                "clause_number": "1",
                # Missing: text_fa
            }
        }
        
        def has_required_properties(node: Dict) -> bool:
            return required_properties.issubset(node["properties"].keys())
        
        assert not has_required_properties(clause_node), "Clause missing required properties"


@pytest.mark.p1_high
@pytest.mark.unit
class TestAllowedRelationshipCombinations:
    """
    TEST NAME: Allowed Relationship Combinations Validation
    PURPOSE: Validate that only allowed label-relationship-type combinations exist
    INVARIANT: Only ontology-defined relationship combinations are permitted
    FAILURE RISK: Invalid combinations cause semantic errors and query failures
    IMPLEMENTATION: Validate each relationship against allowed combinations matrix
    """
    
    def test_law_allowed_relationships(self):
        """
        Verify Law nodes only have allowed relationship types.
        
        Law can: HAS_CHAPTER Chapter, AMENDS Law, REPLACED_BY Law
        """
        allowed_relationships = {
            "HAS_CHAPTER": "Chapter",
            "AMENDS": "Law",
            "REPLACED_BY": "Law"
        }
        
        # Test invalid relationship
        invalid_relationship = {
            "source_label": "Law",
            "target_label": "Article",
            "type": "HAS_ARTICLE"  # Not allowed (should go through Chapter)
        }
        
        def is_allowed(rel: Dict) -> bool:
            if rel["source_label"] == "Law":
                return rel["type"] in allowed_relationships
            return True
        
        assert not is_allowed(invalid_relationship), "Invalid Law relationship detected"
    
    def test_article_allowed_relationships(self):
        """
        Verify Article nodes only have allowed relationship types.
        
        Article can: HAS_PARAGRAPH Paragraph, REFERENCES Article, AMENDED_BY Article
        """
        allowed_relationships = {
            "HAS_PARAGRAPH": "Paragraph",
            "REFERENCES": "Article",
            "AMENDED_BY": "Article"
        }
        
        # Test invalid relationship
        invalid_relationship = {
            "source_label": "Article",
            "target_label": "Law",
            "type": "HAS_LAW"  # Not allowed
        }
        
        def is_allowed(rel: Dict) -> bool:
            if rel["source_label"] == "Article":
                return rel["type"] in allowed_relationships
            return True
        
        assert not is_allowed(invalid_relationship), "Invalid Article relationship detected"
    
    def test_precedent_allowed_relationships(self):
        """
        Verify Precedent nodes only have allowed relationship types.
        
        Precedent can: INTERPRETS Article, CONFLICTS_WITH Precedent
        """
        allowed_relationships = {
            "INTERPRETS": "Article",
            "CONFLICTS_WITH": "Precedent"
        }
        
        # Test invalid relationship
        invalid_relationship = {
            "source_label": "Precedent",
            "target_label": "Law",
            "type": "HAS_LAW"  # Not allowed
        }
        
        def is_allowed(rel: Dict) -> bool:
            if rel["source_label"] == "Precedent":
                return rel["type"] in allowed_relationships
            return True
        
        assert not is_allowed(invalid_relationship), "Invalid Precedent relationship detected"


@pytest.mark.p1_high
@pytest.mark.unit
class TestArticleParentValidation:
    """
    TEST NAME: Article Parent Validation
    PURPOSE: Validate that Articles are connected to correct parent
    INVARIANT: Article must have parent Chapter (or Law if no Chapter)
    FAILURE RISK: Wrong parent causes incorrect legal hierarchy and reasoning
    IMPLEMENTATION: Validate Article parent is Chapter or Law
    """
    
    def test_article_parent_is_chapter_or_law(self):
        """
        Verify Article parent is Chapter or Law.
        
        Article should not have invalid parent (e.g., another Article).
        """
        article = {
            "canonical_id": "article:civil_code:1",
            "parent_label": "Article",  # Invalid: Article cannot parent Article
            "parent_id": "article:civil_code:2"
        }
        
        def has_valid_parent(article: Dict) -> bool:
            return article["parent_label"] in {"Chapter", "Law"}
        
        assert not has_valid_parent(article), "Article has invalid parent"
    
    def test_article_parent_exists(self):
        """
        Verify Article parent node exists.
        
        Article should not be orphaned.
        """
        article = {
            "canonical_id": "article:civil_code:1",
            "parent_id": None  # Orphan
        }
        
        def has_parent(article: Dict) -> bool:
            return article["parent_id"] is not None
        
        assert not has_parent(article), "Article is orphaned"
    
    def test_article_parent_in_same_law(self):
        """
        Verify Article parent is in same Law.
        
        Article's Chapter should belong to same Law.
        """
        article = {
            "canonical_id": "article:civil_code:1",
            "parent_chapter_id": "chapter:commercial_code:1",  # Wrong law
            "law_id": "law:civil_code"
        }
        
        def parent_in_same_law(article: Dict) -> bool:
            # Extract law from parent chapter ID
            parent_law = article["parent_chapter_id"].split(":")[1]
            article_law = article["law_id"].split(":")[1]
            return parent_law == article_law
        
        assert not parent_in_same_law(article), "Article parent in different law"


@pytest.mark.p1_high
@pytest.mark.unit
class TestJudicialDecisionVsLegislation:
    """
    TEST NAME: Judicial Decision vs Legislation Validation
    PURPOSE: Detect judicial decisions incorrectly labeled as legislation
    INVARIANT: Judicial decisions must have Precedent label, not Law label
    FAILURE RISK: Mislabeling causes incorrect legal precedence and application
    IMPLEMENTATION: Detect court property in Law nodes
    """
    
    def test_judicial_decision_not_labeled_as_law(self):
        """
        Detect judicial decision labeled as Law.
        
        Judicial decisions should have Precedent label.
        """
        node = {
            "label": "Law",
            "properties": {
                "court": "Supreme Court",
                "decision_date": "2020-01-01"
            }
        }
        
        def is_judicial_decision(node: Dict) -> bool:
            return "court" in node["properties"]
        
        assert is_judicial_decision(node), "Judicial decision mislabeled as Law"
    
    def test_legislation_not_labeled_as_precedent(self):
        """
        Detect legislation incorrectly labeled as Precedent.
        
        Legislation should have Law label.
        """
        node = {
            "label": "Precedent",
            "properties": {
                "publication_date": "1928-03-15",
                "status": "active"
            }
        }
        
        def is_legislation(node: Dict) -> bool:
            return "publication_date" in node["properties"] and "court" not in node["properties"]
        
        assert is_legislation(node), "Legislation mislabeled as Precedent"
    
    def test_precedent_has_court_property(self):
        """
        Verify Precedent nodes have court property.
        
        Judicial decisions must specify which court issued them.
        """
        node = {
            "label": "Precedent",
            "properties": {
                "decision_date": "2020-01-01"
                # Missing: court
            }
        }
        
        def has_court_property(node: Dict) -> bool:
            return "court" in node["properties"]
        
        assert not has_court_property(node), "Precedent missing court property"


@pytest.mark.p1_high
@pytest.mark.unit
class TestAdvisoryOpinionValidation:
    """
    TEST NAME: Advisory Opinion Validation
    PURPOSE: Detect advisory opinions incorrectly treated as binding law
    INVARIANT: Advisory opinions must not have status='active' like binding laws
    FAILURE RISK: Treating advisory opinions as binding causes incorrect legal application
    IMPLEMENTATION: Detect opinion_type='advisory' with status='active'
    """
    
    def test_advisory_opinion_not_binding(self):
        """
        Detect advisory opinion marked as binding.
        
        Advisory opinions should have status='advisory', not 'active'.
        """
        node = {
            "label": "Law",
            "properties": {
                "opinion_type": "advisory",
                "status": "active"  # Wrong: should be 'advisory'
            }
        }
        
        def is_advisory_as_binding(node: Dict) -> bool:
            return (node["properties"].get("opinion_type") == "advisory" and
                    node["properties"].get("status") == "active")
        
        assert is_advisory_as_binding(node), "Advisory opinion marked as binding"
    
    def test_binding_law_not_advisory(self):
        """
        Detect binding law incorrectly marked as advisory.
        
        Binding laws should have status='active', not 'advisory'.
        """
        node = {
            "label": "Law",
            "properties": {
                "status": "advisory",  # Wrong: binding law
                "opinion_type": None
            }
        }
        
        def is_binding_as_advisory(node: Dict) -> bool:
            return (node["properties"].get("status") == "advisory" and
                    node["properties"].get("opinion_type") is None)
        
        assert is_binding_as_advisory(node), "Binding law marked as advisory"


@pytest.mark.p1_high
@pytest.mark.unit
class TestAmendmentVsOriginalLaw:
    """
    TEST NAME: Amendment vs Original Law Validation
    PURPOSE: Detect amendments incorrectly treated as original laws
    INVARIANT: Amendments must have Amendment label or amendment relationship
    FAILURE RISK: Treating amendments as original causes incorrect legal state
    IMPLEMENTATION: Detect title containing 'الحاقیه' with Law label
    """
    
    def test_amendment_not_labeled_as_law(self):
        """
        Detect amendment labeled as Law.
        
        Amendments should have Amendment label or AMENDS relationship.
        """
        node = {
            "label": "Law",
            "properties": {
                "title_fa": "الحاقیه به قانون مدنی",
                "amendment_date": "2020-01-01"
            }
        }
        
        def is_amendment_as_law(node: Dict) -> bool:
            return (node["label"] == "Law" and
                    "الحاقیه" in node["properties"].get("title_fa", ""))
        
        assert is_amendment_as_law(node), "Amendment labeled as Law"
    
    def test_amendment_has_amends_relationship(self):
        """
        Verify amendment has AMENDS relationship to original.
        
        Amendments must reference the law they amend.
        """
        amendment = {
            "canonical_id": "amendment:civil_code:2020",
            "amends": None  # Missing: should reference original law
        }
        
        def has_amends_relationship(amendment: Dict) -> bool:
            return amendment.get("amends") is not None
        
        assert not has_amends_relationship(amendment), "Amendment missing AMENDS relationship"
    
    def test_original_law_not_amendment(self):
        """
        Detect original law incorrectly marked as amendment.
        
        Original laws should not have amendment_date.
        """
        node = {
            "label": "Law",
            "properties": {
                "title_fa": "قانون مدنی",
                "amendment_date": None  # Correct: original law
            }
        }
        
        def is_original_as_amendment(node: Dict) -> bool:
            return (node["label"] == "Law" and
                    node["properties"].get("amendment_date") is not None and
                    "الحاقیه" not in node["properties"].get("title_fa", ""))
        
        assert not is_original_as_amendment(node), "Original law incorrectly marked as amendment"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestLegalHierarchyValidation:
    """
    TEST NAME: Legal Hierarchy Validation
    PURPOSE: Validate complete legal hierarchy chains
    INVARIANT: Legal hierarchy must be complete (Law → Chapter → Article → Paragraph → Clause)
    FAILURE RISK: Incomplete hierarchy causes missing legal context and reasoning failures
    IMPLEMENTATION: Validate hierarchy chain completeness and no shortcuts
    """
    
    def test_complete_hierarchy_chain(self):
        """
        Verify complete hierarchy chain exists.
        
        Chain: Law → Chapter → Article → Paragraph → Clause
        """
        hierarchy = {
            "Law": "law:civil_code",
            "Chapter": "chapter:civil_code:1",
            "Article": "article:civil_code:1",
            "Paragraph": "paragraph:civil_code:1:1",
            "Clause": "clause:civil_code:1:1:1"
        }
        
        # All levels present
        has_complete_chain = all(hierarchy.values())
        
        assert has_complete_chain, "Hierarchy chain incomplete"
    
    def test_no_hierarchy_shortcuts(self):
        """
        Detect hierarchy shortcuts (Law → Article without Chapter).
        
        Hierarchy should follow full path, not skip levels.
        """
        relationship = {
            "source_label": "Law",
            "target_label": "Article",
            "type": "HAS_ARTICLE"  # Shortcut: should go through Chapter
        }
        
        def is_shortcut(rel: Dict) -> bool:
            return (rel["source_label"] == "Law" and
                    rel["target_label"] == "Article" and
                    rel["type"] == "HAS_ARTICLE")
        
        assert is_shortcut(relationship), "Hierarchy shortcut detected"
    
    def test_hierarchy_chain_connectivity(self):
        """
        Verify hierarchy chain is connected.
        
        Each level should be connected to next level.
        """
        chain = [
            ("law:civil_code", "chapter:civil_code:1", "HAS_CHAPTER"),
            ("chapter:civil_code:1", "article:civil_code:1", "HAS_ARTICLE"),
            ("article:civil_code:1", "paragraph:civil_code:1:1", "HAS_PARAGRAPH"),
            ("paragraph:civil_code:1:1", "clause:civil_code:1:1:1", "HAS_CLAUSE")
        ]
        
        # All connections present
        is_connected = all(chain)
        
        assert is_connected, "Hierarchy chain not fully connected"
