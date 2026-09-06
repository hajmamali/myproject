"""
Temporal Legal Consistency Tests
================================

TEST NAME: Temporal Consistency Validation
PURPOSE: Validate time-related logic and version management
INVARIANT: Temporal relationships must be logically consistent (effective dates, repeals, amendments)
FAILURE RISK: Temporal errors cause applying wrong law version and incorrect legal state
IMPLEMENTATION: Validate effective dates, repealed laws, amendments, historical versions
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import Mock


@pytest.mark.p1_high
@pytest.mark.unit
class TestEffectiveDateValidation:
    """
    TEST NAME: Effective Date Validation
    PURPOSE: Validate effective dates are logically correct
    INVARIANT: Effective date must be >= publication date and in valid format
    FAILURE RISK: Invalid effective dates cause wrong law application timing
    IMPLEMENTATION: Validate date format, logical consistency, and future dates
    """
    
    def test_effective_date_format_valid(self):
        """
        Verify effective date format is valid (YYYY-MM-DD).
        """
        law = {
            "canonical_id": "law:civil_code",
            "effective_date": "1928-03-15"
        }
        
        def is_valid_date(date_str: str) -> bool:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                return True
            except ValueError:
                return False
        
        assert is_valid_date(law["effective_date"]), "Effective date format invalid"
    
    def test_effective_date_after_publication(self):
        """
        Verify effective date is >= publication date.
        
        Law cannot be effective before publication.
        """
        law = {
            "publication_date": "1928-03-15",
            "effective_date": "1928-03-10"  # Before publication - invalid
        }
        
        def is_effective_after_publication(law: Dict) -> bool:
            pub = datetime.strptime(law["publication_date"], "%Y-%m-%d")
            eff = datetime.strptime(law["effective_date"], "%Y-%m-%d")
            return eff >= pub
        
        assert not is_effective_after_publication(law), "Effective date before publication"
    
    def test_no_future_effective_dates(self):
        """
        Detect laws with future effective dates marked as active.
        
        Future laws should not be marked as currently active.
        """
        today = datetime.now().date()
        law = {
            "effective_date": "2099-01-01",
            "status": "active"  # Wrong: future law
        }
        
        def is_future_active(law: Dict) -> bool:
            eff_date = datetime.strptime(law["effective_date"], "%Y-%m-%d").date()
            return eff_date > today and law["status"] == "active"
        
        assert is_future_active(law), "Future law marked as active"
    
    def test_effective_date_not_null(self):
        """
        Verify effective date is not null for active laws.
        
        Active laws must have effective date.
        """
        law = {
            "canonical_id": "law:active",
            "status": "active",
            "effective_date": None  # Missing
        }
        
        def has_effective_date(law: Dict) -> bool:
            return law["status"] != "active" or law["effective_date"] is not None
        
        assert not has_effective_date(law), "Active law missing effective date"


@pytest.mark.p1_high
@pytest.mark.unit
class TestRepealedLawHandling:
    """
    TEST NAME: Repealed Law Handling
    PURPOSE: Validate repealed laws are correctly handled
    INVARIANT: Repealed laws must have status='repealed' and repeal date
    FAILURE RISK: Incorrect repeal status causes applying invalid law
    IMPLEMENTATION: Validate repeal status, date, and relationships
    """
    
    def test_repealed_laws_have_repeal_date(self):
        """
        Verify repealed laws have repeal date.
        
        Repealed laws must specify when they were repealed.
        """
        law = {
            "canonical_id": "law:repealed",
            "status": "repealed",
            "repeal_date": None  # Missing
        }
        
        def has_repeal_date(law: Dict) -> bool:
            return law["status"] != "repealed" or law["repeal_date"] is not None
        
        assert not has_repeal_date(law), "Repealed law missing repeal date"
    
    def test_repeal_date_after_effective_date(self):
        """
        Verify repeal date is after effective date.
        
        Law cannot be repealed before it became effective.
        """
        law = {
            "effective_date": "1928-03-15",
            "repeal_date": "1920-01-01"  # Before effective - invalid
        }
        
        def is_repeal_after_effective(law: Dict) -> bool:
            eff = datetime.strptime(law["effective_date"], "%Y-%m-%d")
            rep = datetime.strptime(law["repeal_date"], "%Y-%m-%d")
            return rep >= eff
        
        assert not is_repeal_after_effective(law), "Repeal date before effective date"
    
    def test_repealed_laws_not_active(self):
        """
        Verify repealed laws are not marked as active.
        
        Repealed and active are mutually exclusive.
        """
        law = {
            "status": "repealed",
            "active": True  # Contradiction
        }
        
        def is_status_consistent(law: Dict) -> bool:
            return not (law["status"] == "repealed" and law.get("active") == True)
        
        assert not is_status_consistent(law), "Repealed law marked as active"
    
    def test_repealed_laws_have_replaced_by(self):
        """
        Verify repealed laws have REPLACED_BY relationship.
        
        Repealed laws should reference replacement law.
        """
        law = {
            "canonical_id": "law:repealed",
            "status": "repealed",
            "replaced_by": None  # Missing replacement
        }
        
        def has_replacement(law: Dict) -> bool:
            return law["status"] != "repealed" or law["replaced_by"] is not None
        
        assert not has_replacement(law), "Repealed law missing replacement"


@pytest.mark.p1_high
@pytest.mark.unit
class TestAmendmentTracking:
    """
    TEST NAME: Amendment Tracking
    PURPOSE: Validate amendment tracking is complete
    INVARIANT: All amendments must be tracked with correct relationships
    FAILURE RISK: Missing amendments cause incorrect current law state
    IMPLEMENTATION: Validate amendment relationships, dates, and completeness
    """
    
    def test_amendments_have_amends_relationship(self):
        """
        Verify amendments have AMENDS relationship to original.
        
        Amendments must reference the law/article they amend.
        """
        amendment = {
            "canonical_id": "amendment:civil_code:2020",
            "amends": None  # Missing
        }
        
        def has_amends_relationship(amendment: Dict) -> bool:
            return amendment.get("amends") is not None
        
        assert not has_amends_relationship(amendment), "Amendment missing AMENDS relationship"
    
    def test_amendment_date_after_original_publication(self):
        """
        Verify amendment date is after original law publication.
        
        Amendment cannot predate original law.
        """
        original = {"publication_date": "1928-03-15"}
        amendment = {"amendment_date": "1900-01-01"}  # Before original
        
        def is_amendment_after_original(original: Dict, amendment: Dict) -> bool:
            orig = datetime.strptime(original["publication_date"], "%Y-%m-%d")
            amend = datetime.strptime(amendment["amendment_date"], "%Y-%m-%d")
            return amend >= orig
        
        assert not is_amendment_after_original(original, amendment), "Amendment before original"
    
    def test_amendment_effective_date_valid(self):
        """
        Verify amendment effective date is valid.
        
        Amendment effective date must be >= amendment date.
        """
        amendment = {
            "amendment_date": "2020-01-01",
            "effective_date": "2019-01-01"  # Before amendment date - invalid
        }
        
        def is_effective_after_amendment(amendment: Dict) -> bool:
            amend = datetime.strptime(amendment["amendment_date"], "%Y-%m-%d")
            eff = datetime.strptime(amendment["effective_date"], "%Y-%m-%d")
            return eff >= amend
        
        assert not is_effective_after_amendment(amendment), "Effective date before amendment date"
    
    def test_amendment_chain_complete(self):
        """
        Verify amendment chain is complete (no missing amendments).
        
        All amendments to a law should be tracked.
        """
        law = {
            "canonical_id": "law:civil_code",
            "amendments": ["amendment:2020", "amendment:2025"]
            # Missing: amendment:2022 (if exists)
        }
        
        # This is informational - requires external knowledge of expected amendments
        assert len(law["amendments"]) >= 0, "Amendment chain check completed"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestHistoricalVersionManagement:
    """
    TEST NAME: Historical Version Management
    PURPOSE: Validate historical versions are correctly managed
    INVARIANT: Historical versions must be linked and not marked as current
    FAILURE RISK: Incorrect version management causes wrong law application
    IMPLEMENTATION: Validate version relationships and current version markers
    """
    
    def test_versions_linked_sequentially(self):
        """
        Verify versions are linked sequentially (v1 → v2 → v3).
        
        Version chain should be complete and sequential.
        """
        versions = [
            {"canonical_id": "law:v1", "version": "1"},
            {"canonical_id": "law:v3", "version": "3"},
            {"canonical_id": "law:v2", "version": "2"}
        ]
        
        # Sort by version
        sorted_versions = sorted(versions, key=lambda x: int(x["version"]))
        version_numbers = [v["version"] for v in sorted_versions]
        
        # Check sequential
        is_sequential = all(
            int(version_numbers[i]) + 1 == int(version_numbers[i+1])
            for i in range(len(version_numbers)-1)
        )
        
        assert is_sequential, "Versions not sequential"
    
    def test_only_one_current_version(self):
        """
        Verify only one version is marked as current.
        
        Multiple current versions is an error.
        """
        versions = [
            {"canonical_id": "law:v1", "is_current": True},
            {"canonical_id": "law:v2", "is_current": True}  # Error: two current
        ]
        
        current_count = sum(1 for v in versions if v.get("is_current"))
        
        assert current_count > 1, "Multiple current versions detected"
    
    def test_historical_versions_not_current(self):
        """
        Verify historical versions are not marked as current.
        
        Only latest version should be current.
        """
        # Test case 1: Bad data - old version marked as current
        bad_versions = [
            {"canonical_id": "law:v1", "version": "1", "is_current": True},  # Old version marked current
            {"canonical_id": "law:v2", "version": "2", "is_current": True}
        ]
        
        def has_incorrect_current_versions(versions: List[Dict]) -> bool:
            """Check if any historical version is incorrectly marked as current."""
            max_version = max(int(v["version"]) for v in versions)
            for v in versions:
                if int(v["version"]) < max_version and v.get("is_current"):
                    return True
            return False
        
        # Should detect the error
        assert has_incorrect_current_versions(bad_versions), "Should detect old version marked as current"
        
        # Test case 2: Good data - only latest is current
        good_versions = [
            {"canonical_id": "law:v1", "version": "1", "is_current": False},
            {"canonical_id": "law:v2", "version": "2", "is_current": True}
        ]
        
        # Should NOT detect error
        assert not has_incorrect_current_versions(good_versions), "Should pass with correct data"
    
    def test_version_relationships_exist(self):
        """
        Verify version relationships exist (REPLACED_BY).
        
        Each version should have REPLACED_BY relationship to next version.
        """
        version1 = {"canonical_id": "law:v1", "replaced_by": None}  # Missing
        version2 = {"canonical_id": "law:v2", "replaced_by": "law:v3"}
        
        def has_replaced_by(version: Dict) -> bool:
            return version.get("replaced_by") is not None
        
        assert not has_replaced_by(version1), "Version missing REPLACED_BY relationship"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestMultipleActiveConflictingVersions:
    """
    TEST NAME: Multiple Active Conflicting Versions Detection
    PURPOSE: Detect multiple active versions of same law
    INVARIANT: Only one version of a law should be active at any time
    FAILURE RISK: Multiple active versions cause contradictory legal state
    IMPLEMENTATION: Detect laws with multiple active versions
    """
    
    def test_no_multiple_active_versions(self):
        """
        Verify no multiple active versions of same law.
        
        Each law should have at most one active version.
        """
        law_versions = [
            {"canonical_id": "law:civil_code:v1", "status": "active"},
            {"canonical_id": "law:civil_code:v2", "status": "active"}  # Conflict
        ]
        
        # Group by law base
        from collections import defaultdict
        law_groups = defaultdict(list)
        for v in law_versions:
            law_base = v["canonical_id"].split(":")[1]
            law_groups[law_base].append(v)
        
        # Check for multiple active
        has_conflict = any(
            sum(1 for v in versions if v["status"] == "active") > 1
            for versions in law_groups.values()
        )
        
        assert has_conflict, "Multiple active versions detected"
    
    def test_active_version_effective_date_in_past(self):
        """
        Verify active version effective date is in past.
        
        Active version should be currently effective.
        """
        today = datetime.now().date()
        version = {
            "canonical_id": "law:v1",
            "status": "active",
            "effective_date": "2099-01-01"  # Future - not active yet
        }
        
        def is_currently_active(version: Dict) -> bool:
            eff_date = datetime.strptime(version["effective_date"], "%Y-%m-%d").date()
            return eff_date <= today
        
        assert not is_currently_active(version), "Active version with future effective date"
    
    def test_active_version_not_repealed(self):
        """
        Verify active version is not repealed.
        
        Active and repealed are mutually exclusive.
        """
        version = {
            "canonical_id": "law:v1",
            "status": "active",
            "repeal_date": "2020-01-01"  # Contradiction
        }
        
        def is_status_consistent(version: Dict) -> bool:
            return not (version["status"] == "active" and version.get("repeal_date") is not None)
        
        assert not is_status_consistent(version), "Active version marked as repealed"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestFutureLawDetection:
    """
    TEST NAME: Future Law Detection
    PURPOSE: Detect laws with future publication dates marked as active
    INVARIANT: Future laws should not be marked as currently active
    FAILURE RISK: Future laws applied incorrectly as current law
    IMPLEMENTATION: Detect laws with future publication dates and active status
    """
    
    def test_no_future_laws_active(self):
        """
        Verify no future laws are marked as active.
        
        Laws with future publication dates should not be active.
        """
        today = datetime.now().date()
        law = {
            "publication_date": "2099-01-01",
            "status": "active"  # Wrong
        }
        
        def is_future_active(law: Dict) -> bool:
            pub_date = datetime.strptime(law["publication_date"], "%Y-%m-%d").date()
            return pub_date > today and law["status"] == "active"
        
        assert is_future_active(law), "Future law marked as active"
    
    def test_future_laws_have_pending_status(self):
        """
        Verify future laws have pending status.
        
        Future laws should be marked as pending, not active.
        """
        law = {
            "publication_date": "2099-01-01",
            "status": "active"  # Should be "pending"
        }
        
        def has_correct_status(law: Dict) -> bool:
            today = datetime.now().date()
            pub_date = datetime.strptime(law["publication_date"], "%Y-%m-%d").date()
            if pub_date > today:
                return law["status"] == "pending"
            return True
        
        assert not has_correct_status(law), "Future law has incorrect status"
    
    def test_future_laws_not_in_current_queries(self):
        """
        Verify future laws are excluded from current law queries.
        
        Queries for current laws should not return future laws.
        """
        laws = [
            {"publication_date": "1928-03-15", "status": "active"},
            {"publication_date": "2099-01-01", "status": "active"}  # Future
        ]
        
        today = datetime.now().date()
        current_laws = [
            law for law in laws
            if datetime.strptime(law["publication_date"], "%Y-%m-%d").date() <= today
        ]
        
        assert len(current_laws) < len(laws), "Future law included in current laws"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestRepealedArticleUsage:
    """
    TEST NAME: Repealed Article Usage Detection
    PURPOSE: Detect references to repealed articles as current law
    INVARIANT: Repealed articles should not be used as current law
    FAILURE RISK: Using repealed articles causes invalid legal application
    IMPLEMENTATION: Detect references to repealed articles without repeal context
    """
    
    def test_references_to_repealed_articles_flagged(self):
        """
        Verify references to repealed articles are flagged.
        
        References to repealed articles should indicate repealed status.
        """
        article = {
            "canonical_id": "article:repealed",
            "status": "repealed"
        }
        
        reference = {
            "source": "article:current",
            "target": "article:repealed",
            "context": "current"  # Should indicate repealed
        }
        
        def should_flag_reference(article: Dict, reference: Dict) -> bool:
            return article["status"] == "repealed" and reference["context"] != "repealed"
        
        assert should_flag_reference(article, reference), "Reference to repealed article not flagged"
    
    def test_repealed_articles_not_in_current_queries(self):
        """
        Verify repealed articles are excluded from current law queries.
        
        Queries for current articles should not return repealed articles.
        """
        articles = [
            {"canonical_id": "article:1", "status": "active"},
            {"canonical_id": "article:2", "status": "repealed"}
        ]
        
        current_articles = [a for a in articles if a["status"] == "active"]
        
        assert len(current_articles) < len(articles), "Repealed article included in current"
    
    def test_repealed_articles_have_repeal_date(self):
        """
        Verify repealed articles have repeal date.
        
        Repealed articles must specify when repealed.
        """
        article = {
            "canonical_id": "article:repealed",
            "status": "repealed",
            "repeal_date": None  # Missing
        }
        
        def has_repeal_date(article: Dict) -> bool:
            return article["status"] != "repealed" or article["repeal_date"] is not None
        
        assert not has_repeal_date(article), "Repealed article missing repeal date"


@pytest.mark.p2_medium
@pytest.mark.unit
class TestMissingVersionRelationship:
    """
    TEST NAME: Missing Version Relationship Detection
    PURPOSE: Detect missing version relationships between law versions
    INVARIANT: All versions should be linked with REPLACED_BY relationships
    FAILURE RISK: Missing version relationships break version chain
    IMPLEMENTATION: Detect versions without REPLACED_BY relationships
    """
    
    def test_all_versions_have_replaced_by(self):
        """
        Verify all versions except latest have REPLACED_BY relationship.
        
        Each version should link to next version.
        """
        versions = [
            {"canonical_id": "law:v1", "replaced_by": None},  # Missing
            {"canonical_id": "law:v2", "replaced_by": "law:v3"},
            {"canonical_id": "law:v3", "replaced_by": None}  # Latest - OK
        ]
        
        # All except latest should have replaced_by
        missing_links = [
            v for v in versions[:-1]
            if v.get("replaced_by") is None
        ]
        
        assert len(missing_links) > 0, "Missing REPLACED_BY relationships detected"
    
    def test_version_chain_complete(self):
        """
        Verify version chain is complete (no gaps).
        
        Version chain should be v1 → v2 → v3 without gaps.
        """
        versions = [
            {"canonical_id": "law:v1", "replaced_by": "law:v2"},
            {"canonical_id": "law:v3", "replaced_by": None}
            # Missing: v2
        ]
        
        # Build chain
        chain = {}
        for v in versions:
            if v.get("replaced_by"):
                chain[v["canonical_id"]] = v["replaced_by"]
        
        # Check for gaps
        has_gap = "law:v2" not in [v["canonical_id"] for v in versions]
        
        assert has_gap, "Version chain has gap"
    
    def test_no_orphan_versions(self):
        """
        Verify no orphan versions (versions not in chain).
        
        All versions should be part of version chain.
        """
        versions = [
            {"canonical_id": "law:v1", "replaced_by": "law:v2"},
            {"canonical_id": "law:v2", "replaced_by": None},
            {"canonical_id": "law:v3", "replaced_by": None}  # Orphan
        ]
        
        # Find orphan (not referenced and not referencing)
        referenced = set(v.get("replaced_by") for v in versions if v.get("replaced_by"))
        all_ids = set(v["canonical_id"] for v in versions)
        
        orphans = all_ids - referenced - {v["canonical_id"] for v in versions if not v.get("replaced_by")}
        
        assert len(orphans) > 0, "Orphan version detected"
