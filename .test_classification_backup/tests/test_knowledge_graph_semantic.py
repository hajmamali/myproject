"""
Integration Tests for Knowledge Graph with Semantic Search
===========================================================

Test semantic search integration with legal knowledge graph.

Test Categories:
1. Semantic rule matching
2. Semantic precedent search
3. Hybrid search (semantic + keyword fallback)
4. Performance comparison
5. Persian legal text handling
"""

import pytest
from pathlib import Path
import tempfile
import shutil

# Skip if sentence-transformers not available
pytest.importorskip("sentence_transformers")

from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def kg_with_semantic(temp_storage):
    """Create knowledge graph with semantic search enabled"""
    kg = LegalKnowledgeGraph(storage_path=temp_storage)
    kg.enable_semantic_search()
    return kg


@pytest.fixture
def kg_without_semantic(temp_storage):
    """Create knowledge graph without semantic search"""
    return LegalKnowledgeGraph(storage_path=temp_storage)


@pytest.fixture
def persian_legal_rules(kg_with_semantic):
    """Add Persian legal rules to knowledge graph"""
    rules = [
        {
            "rule_id": "RULE_001",
            "condition": "قرارداد فسخ شد به دلیل عدم پرداخت",
            "conclusion": "طرف مقابل باید خسارت پرداخت کند",
            "confidence": 0.95
        },
        {
            "rule_id": "RULE_002",
            "condition": "تأخیر در اجرای قرارداد بیش از سه ماه",
            "conclusion": "امکان فسخ قرارداد وجود دارد",
            "confidence": 0.90
        },
        {
            "rule_id": "RULE_003",
            "condition": "نقض شرایط اساسی قرارداد",
            "conclusion": "قرارداد باطل است",
            "confidence": 0.98
        },
        {
            "rule_id": "RULE_004",
            "condition": "تمدید قرارداد با توافق طرفین",
            "conclusion": "قرارداد برای مدت جدید معتبر است",
            "confidence": 0.92
        },
        {
            "rule_id": "RULE_005",
            "condition": "عدم رعایت مهلت قانونی برای اعتراض",
            "conclusion": "حق اعتراض ساقط می‌شود",
            "confidence": 0.88
        }
    ]
    
    for rule in rules:
        kg_with_semantic.add_legal_rule(**rule)
    
    return kg_with_semantic


@pytest.fixture
def persian_precedents(kg_with_semantic):
    """Add Persian precedents to knowledge graph"""
    precedents = [
        {
            "case_id": "CASE_001",
            "facts": [
                "شرکت الف قرارداد را فسخ کرد",
                "شرکت ب پرداخت نکرده بود",
                "تأخیر شش ماهه در پرداخت"
            ],
            "decision": "فسخ قرارداد تأیید شد و خسارت تعیین گردید",
            "court": "دیوان عدالت اداری",
            "date": "1402/06/15"
        },
        {
            "case_id": "CASE_002",
            "facts": [
                "قرارداد ساخت ساختمان",
                "تأخیر دو ماهه در تحویل",
                "شرایط جوی نامساعد"
            ],
            "decision": "تأخیر موجه تشخیص داده شد",
            "court": "دادگاه عمومی",
            "date": "1402/08/20"
        },
        {
            "case_id": "CASE_003",
            "facts": [
                "نقض شرط عدم رقابت",
                "افشای اطلاعات محرمانه",
                "خسارت به شرکت"
            ],
            "decision": "محکومیت به پرداخت خسارت و جلوگیری از رقابت",
            "court": "دادگاه تجاری",
            "date": "1402/09/10"
        }
    ]
    
    for prec in precedents:
        kg_with_semantic.add_precedent(**prec)
    
    return kg_with_semantic


class TestSemanticRuleMatching:
    """Test semantic rule matching"""
    
    def test_semantic_rule_matching_enabled(self, persian_legal_rules):
        """Test rule matching with semantic search"""
        facts = [
            "شرکت قرارداد را فسخ کرد",
            "پرداخت انجام نشده بود"
        ]
        
        results = persian_legal_rules.find_applicable_rules(
            facts,
            use_semantic=True
        )
        
        assert len(results) > 0
        
        # Should find RULE_001 (about فسخ and عدم پرداخت)
        rule_ids = [r["rule_id"] for r in results]
        assert "RULE_001" in rule_ids
        
        # Should have match_type
        assert all("match_type" in r for r in results)
        assert results[0]["match_type"] == "semantic"
    
    def test_semantic_vs_keyword_accuracy(self, persian_legal_rules):
        """Test that semantic search is more accurate than keyword"""
        # Query with synonyms (not exact keywords)
        facts = [
            "شرکت پیمان را لغو کرد",  # "پیمان" instead of "قرارداد"
            "مبلغ پرداخت نشد"  # "مبلغ پرداخت نشد" instead of "عدم پرداخت"
        ]
        
        # Semantic search
        semantic_results = persian_legal_rules.find_applicable_rules(
            facts,
            use_semantic=True
        )
        
        # Keyword search
        keyword_results = persian_legal_rules.find_applicable_rules(
            facts,
            use_semantic=False
        )
        
        # Semantic should find more relevant rules
        assert len(semantic_results) >= len(keyword_results)
        
        # Semantic should have higher scores
        if semantic_results and keyword_results:
            assert semantic_results[0]["match_score"] >= keyword_results[0]["match_score"]
    
    def test_semantic_threshold(self, persian_legal_rules):
        """Test semantic threshold filtering"""
        facts = ["قرارداد"]
        
        # High threshold - fewer results
        high_threshold_results = persian_legal_rules.find_applicable_rules(
            facts,
            use_semantic=True,
            semantic_threshold=0.8
        )
        
        # Low threshold - more results
        low_threshold_results = persian_legal_rules.find_applicable_rules(
            facts,
            use_semantic=True,
            semantic_threshold=0.3
        )
        
        assert len(high_threshold_results) <= len(low_threshold_results)
    
    def test_semantic_with_complex_query(self, persian_legal_rules):
        """Test semantic search with complex query"""
        facts = [
            "طرف مقابل تعهدات خود را انجام نداد",
            "مهلت قانونی گذشته است",
            "خسارت وارد شده است"
        ]
        
        results = persian_legal_rules.find_applicable_rules(
            facts,
            use_semantic=True
        )
        
        assert len(results) > 0
        
        # Should find multiple relevant rules
        assert len(results) >= 2


class TestSemanticPrecedentSearch:
    """Test semantic precedent search"""
    
    def test_semantic_precedent_search(self, persian_precedents):
        """Test precedent search with semantic similarity"""
        current_facts = [
            "شرکت قرارداد را فسخ کرد",
            "عدم پرداخت توسط طرف مقابل",
            "تأخیر طولانی"
        ]
        
        results = persian_precedents.find_similar_precedents(
            current_facts,
            use_semantic=True,
            top_k=3
        )
        
        assert len(results) > 0
        assert len(results) <= 3
        
        # Should find CASE_001 (similar facts)
        case_ids = [r["case_id"] for r in results]
        assert "CASE_001" in case_ids
        
        # Should have match_type
        assert results[0]["match_type"] == "semantic"
    
    def test_semantic_precedent_ranking(self, persian_precedents):
        """Test that precedents are ranked by similarity"""
        current_facts = [
            "فسخ قرارداد",
            "عدم پرداخت",
            "تأخیر شش ماه"
        ]
        
        results = persian_precedents.find_similar_precedents(
            current_facts,
            use_semantic=True,
            top_k=3
        )
        
        # Results should be sorted by similarity
        similarities = [r["similarity"] for r in results]
        assert similarities == sorted(similarities, reverse=True)
        
        # Top result should have high similarity
        assert results[0]["similarity"] > 0.5
    
    def test_semantic_vs_jaccard_precedents(self, persian_precedents):
        """Test semantic vs Jaccard for precedent search"""
        current_facts = [
            "لغو پیمان به دلیل عدم پرداخت مبلغ"
        ]
        
        # Semantic
        semantic_results = persian_precedents.find_similar_precedents(
            current_facts,
            use_semantic=True,
            top_k=3
        )
        
        # Jaccard
        jaccard_results = persian_precedents.find_similar_precedents(
            current_facts,
            use_semantic=False,
            top_k=3
        )
        
        # Both should find results
        assert len(semantic_results) > 0
        assert len(jaccard_results) > 0


class TestHybridSearch:
    """Test hybrid search (semantic + keyword fallback)"""
    
    def test_fallback_to_keyword_on_error(self, kg_without_semantic):
        """Test fallback to keyword when semantic not available"""
        # Add rules without semantic search
        kg_without_semantic.add_legal_rule(
            rule_id="RULE_001",
            condition="قرارداد فسخ شد",
            conclusion="خسارت",
            confidence=0.9
        )
        
        facts = ["قرارداد فسخ شد"]
        
        # Should use keyword matching (no semantic available)
        results = kg_without_semantic.find_applicable_rules(
            facts,
            use_semantic=True  # Requested but not available
        )
        
        assert len(results) > 0
        # Should use keyword matching
        assert results[0]["match_type"] == "keyword"
    
    def test_semantic_disabled_explicitly(self, persian_legal_rules):
        """Test disabling semantic search explicitly"""
        facts = ["قرارداد فسخ شد"]
        
        results = persian_legal_rules.find_applicable_rules(
            facts,
            use_semantic=False
        )
        
        assert len(results) > 0
        assert results[0]["match_type"] == "keyword"


class TestPersianLanguageHandling:
    """Test Persian language specific features"""
    
    def test_persian_synonyms(self, persian_legal_rules):
        """Test handling of Persian synonyms"""
        # Different words for "contract"
        facts_1 = ["قرارداد فسخ شد"]
        facts_2 = ["پیمان لغو شد"]
        facts_3 = ["عقد باطل شد"]
        
        results_1 = persian_legal_rules.find_applicable_rules(facts_1, use_semantic=True)
        results_2 = persian_legal_rules.find_applicable_rules(facts_2, use_semantic=True)
        results_3 = persian_legal_rules.find_applicable_rules(facts_3, use_semantic=True)
        
        # All should find similar rules
        assert len(results_1) > 0
        assert len(results_2) > 0
        assert len(results_3) > 0
    
    def test_persian_arabic_variants(self, persian_legal_rules):
        """Test handling of Persian/Arabic character variants"""
        # Persian 'ی' vs Arabic 'ي'
        facts_persian = ["قرارداد فسخ می‌شود"]
        facts_arabic = ["قرارداد فسخ مي‌شود"]
        
        results_persian = persian_legal_rules.find_applicable_rules(
            facts_persian, use_semantic=True
        )
        results_arabic = persian_legal_rules.find_applicable_rules(
            facts_arabic, use_semantic=True
        )
        
        # Should find similar results
        assert len(results_persian) > 0
        assert len(results_arabic) > 0


class TestPerformance:
    """Test performance characteristics"""
    
    def test_semantic_search_performance(self, persian_legal_rules):
        """Test semantic search performance"""
        import time
        
        facts = ["قرارداد فسخ شد به دلیل عدم پرداخت"]
        
        # Warm up (load model)
        persian_legal_rules.find_applicable_rules(facts, use_semantic=True)
        
        # Measure
        start = time.time()
        for _ in range(10):
            persian_legal_rules.find_applicable_rules(facts, use_semantic=True)
        semantic_time = time.time() - start
        
        # Should be reasonably fast (<1 second for 10 queries)
        assert semantic_time < 1.0
    
    def test_caching_improves_performance(self, persian_legal_rules):
        """Test that caching improves performance"""
        import time
        
        facts = ["قرارداد فسخ شد"]
        
        # First call (no cache)
        start = time.time()
        persian_legal_rules.find_applicable_rules(facts, use_semantic=True)
        first_time = time.time() - start
        
        # Second call (with cache)
        start = time.time()
        persian_legal_rules.find_applicable_rules(facts, use_semantic=True)
        second_time = time.time() - start
        
        # Second call should be faster
        assert second_time < first_time


class TestStatistics:
    """Test statistics and monitoring"""
    
    def test_usage_count_incremented(self, persian_legal_rules):
        """Test that usage count is incremented"""
        facts = ["قرارداد فسخ شد"]
        
        # Get initial usage count
        rule = persian_legal_rules.get_rule("RULE_001")
        initial_count = rule.usage_count if rule else 0
        
        # Find applicable rules
        persian_legal_rules.find_applicable_rules(facts, use_semantic=True)
        
        # Usage count should increase
        rule = persian_legal_rules.get_rule("RULE_001")
        assert rule.usage_count > initial_count
    
    def test_relevance_score_updated(self, persian_precedents):
        """Test that relevance score is updated"""
        facts = ["فسخ قرارداد"]
        
        # Find similar precedents
        results = persian_precedents.find_similar_precedents(
            facts,
            use_semantic=True
        )
        
        # Relevance scores should be updated
        for result in results:
            precedent = result["precedent"]
            assert precedent.relevance_score > 0


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_facts(self, persian_legal_rules):
        """Test with empty facts"""
        results = persian_legal_rules.find_applicable_rules(
            [],
            use_semantic=True
        )
        
        # Should return empty or handle gracefully
        assert isinstance(results, list)
    
    def test_very_long_facts(self, persian_legal_rules):
        """Test with very long facts"""
        long_fact = " ".join(["قرارداد"] * 1000)
        
        results = persian_legal_rules.find_applicable_rules(
            [long_fact],
            use_semantic=True
        )
        
        # Should handle without error
        assert isinstance(results, list)
    
    def test_special_characters_in_facts(self, persian_legal_rules):
        """Test with special characters"""
        facts = [
            "قرارداد #123 @ شرکت ABC (فسخ شد) - 2024"
        ]
        
        results = persian_legal_rules.find_applicable_rules(
            facts,
            use_semantic=True
        )
        
        # Should handle without error
        assert isinstance(results, list)


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests"""
    
    def test_complete_legal_reasoning_workflow(self, persian_legal_rules, persian_precedents):
        """Test complete workflow: rules + precedents"""
        # Case facts
        case_facts = [
            "شرکت الف قرارداد را فسخ کرد",
            "شرکت ب پرداخت نکرده بود",
            "تأخیر پنج ماهه در پرداخت"
        ]
        
        # Find applicable rules
        applicable_rules = persian_legal_rules.find_applicable_rules(
            case_facts,
            use_semantic=True
        )
        
        # Find similar precedents
        similar_precedents = persian_precedents.find_similar_precedents(
            case_facts,
            use_semantic=True,
            top_k=3
        )
        
        # Should find both rules and precedents
        assert len(applicable_rules) > 0
        assert len(similar_precedents) > 0
        
        # Top rule should be relevant
        assert applicable_rules[0]["match_score"] > 0.5
        
        # Top precedent should be similar
        assert similar_precedents[0]["similarity"] > 0.5
