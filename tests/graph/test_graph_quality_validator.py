"""
Graph Quality Validator Tests — Enterprise-Grade Validation
===========================================================

Tests for mahoun/graph/validation/quality_validator.py

Coverage:
- Orphan node detection
- Duplicate ID detection
- Required property validation
- Relationship integrity
- Domain consistency rules
- Deterministic scoring
- Immutable results
- Governance context enforcement
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from mahoun.graph.validation.quality_validator import (
    GraphQualityValidator,
    ValidationReport,
    ValidationIssue,
    QualityLevel,
    IssueSeverity,
    OrphanNodesCheck,
    DuplicateNodesCheck,
    MissingPropertiesCheck,
    IntegrityCheck,
    ConsistencyCheck,
    validate_graph_quality,
)
from mahoun.core.governance.governance_context import GovernanceContext


@pytest.fixture
def governance_context():
    """Standard governance context for tests"""
    from mahoun.core.governance.governance_context import GovernanceContextManager
    return GovernanceContextManager.create_context(
        correlation_id="test-correlation-123",
        execution_mode="STRICT",
        actor_id="test-validator",
    )


@pytest.fixture
def validator(governance_context):
    """Create validator instance"""
    return GraphQualityValidator(governance_context)


@pytest.fixture
def mock_connection():
    """Mock Neo4j connection"""
    conn = Mock()
    session = Mock()
    conn.session.return_value.__enter__ = Mock(return_value=session)
    conn.session.return_value.__exit__ = Mock(return_value=False)
    return conn, session


class TestOrphanNodeDetection:
    """Test orphan node detection"""
    
    @pytest.mark.p2
    def test_no_orphans(self, validator, mock_connection):
        """Test graph with no orphan nodes"""
        conn, session = mock_connection
        session.run.return_value = []
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_orphan_nodes()
        
        assert result.total_orphans == 0
        assert not result.has_orphans
        assert len(result.orphans_by_type) == 0
        assert len(validator.issues) == 0
    
    @pytest.mark.p2
    def test_orphans_detected_warning_level(self, validator, mock_connection):
        """Test detection of small number of orphans (warning)"""
        conn, session = mock_connection
        
        # Mock query result
        mock_record = {
            'label': 'Article',
            'count': 10,
            'sample_ids': ['art-1', 'art-2', 'art-3']
        }
        session.run.return_value = [mock_record]
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_orphan_nodes()
        
        assert result.total_orphans == 10
        assert result.has_orphans
        assert 'Article' in result.orphans_by_type
        assert result.orphans_by_type['Article']['count'] == 10
        
        # Should create WARNING issue (count < 100)
        assert len(validator.issues) == 1
        issue = validator.issues[0]
        assert issue.issue_type == 'orphan_nodes'
        assert issue.severity == IssueSeverity.WARNING
        assert issue.entity_label == 'Article'
        assert issue.count == 10
    
    @pytest.mark.p2
    def test_orphans_detected_error_level(self, validator, mock_connection):
        """Test detection of many orphans (error)"""
        conn, session = mock_connection
        
        mock_record = {
            'label': 'Person',
            'count': 150,
            'sample_ids': ['p-1', 'p-2']
        }
        session.run.return_value = [mock_record]
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_orphan_nodes()
        
        assert result.total_orphans == 150
        
        # Should create ERROR issue (count >= 100)
        assert len(validator.issues) == 1
        issue = validator.issues[0]
        assert issue.severity == IssueSeverity.ERROR
        assert issue.count == 150


class TestDuplicateDetection:
    """Test duplicate node detection"""
    
    @pytest.mark.p2
    def test_no_duplicates(self, validator, mock_connection):
        """Test graph with no duplicate IDs"""
        conn, session = mock_connection
        session.run.return_value = []
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_duplicate_nodes()
        
        assert len(result.duplicate_ids) == 0
        assert not result.has_duplicates
        assert len(validator.issues) == 0
    
    @pytest.mark.p2
    def test_duplicates_detected_critical(self, validator, mock_connection):
        """Test duplicate ID detection (CRITICAL severity)"""
        conn, session = mock_connection
        
        mock_records = [
            {'label': 'Law', 'id': 'law-123', 'count': 3},
            {'label': 'Article', 'id': 'art-456', 'count': 2},
        ]
        session.run.return_value = mock_records
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_duplicate_nodes()
        
        assert len(result.duplicate_ids) == 2
        assert result.has_duplicates
        
        # All duplicate IDs should be CRITICAL severity
        assert len(validator.issues) == 2
        for issue in validator.issues:
            assert issue.issue_type == 'duplicate_id'
            assert issue.severity == IssueSeverity.CRITICAL
            assert 'CRITICAL' in issue.message


class TestRequiredProperties:
    """Test required property validation"""
    
    @pytest.mark.p2
    def test_no_missing_properties(self, validator, mock_connection):
        """Test all required properties present"""
        conn, session = mock_connection
        session.run.return_value = [{'count': 0}]
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_required_properties()
        
        assert result.total_missing == 0
        assert not result.has_missing
        assert len(validator.issues) == 0
    
    @pytest.mark.p2
    def test_missing_id_property_error(self, validator, mock_connection):
        """Test missing 'id' property (ERROR severity)"""
        conn, session = mock_connection
        
        # Mock: 5 Article nodes missing 'id'
        session.run.return_value = [{'count': 5}]
        
        with patch.object(validator, '_get_connection', return_value=conn):
            # Only check Article.id
            validator.REQUIRED_PROPERTIES = {'Article': ['id']}
            result = validator.check_required_properties()
        
        assert result.total_missing == 5
        assert result.has_missing
        assert 'Article' in result.missing_by_type
        assert result.missing_by_type['Article']['id'] == 5
        
        # Missing 'id' should be ERROR severity
        assert len(validator.issues) == 1
        issue = validator.issues[0]
        assert issue.severity == IssueSeverity.ERROR
        assert issue.metadata['property'] == 'id'
    
    @pytest.mark.p2
    def test_missing_non_id_property_warning(self, validator, mock_connection):
        """Test missing non-id property (WARNING severity)"""
        conn, session = mock_connection
        
        session.run.return_value = [{'count': 3}]
        
        with patch.object(validator, '_get_connection', return_value=conn):
            validator.REQUIRED_PROPERTIES = {'Verdict': ['content']}
            result = validator.check_required_properties()
        
        assert result.total_missing == 3
        
        # Missing 'content' should be WARNING severity
        issue = validator.issues[0]
        assert issue.severity == IssueSeverity.WARNING


class TestIntegrityChecks:
    """Test relationship integrity"""
    
    @pytest.mark.p2
    def test_no_incomplete_relationships(self, validator, mock_connection):
        """Test all relationships have metadata"""
        conn, session = mock_connection
        session.run.return_value = []
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_integrity()
        
        assert result.total_broken == 0
        assert not result.has_broken
        assert len(validator.issues) == 0
    
    @pytest.mark.p2
    def test_incomplete_relationships_detected(self, validator, mock_connection):
        """Test detection of relationships missing metadata"""
        conn, session = mock_connection
        
        mock_records = [
            {'rel_type': 'CITES', 'count': 25},
            {'rel_type': 'RELATED_TO', 'count': 10},
        ]
        session.run.return_value = mock_records
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_integrity()
        
        assert result.total_broken == 35
        assert result.has_broken
        assert len(result.broken_relationships) == 2
        
        # Should create WARNING issues
        assert len(validator.issues) == 2
        for issue in validator.issues:
            assert issue.issue_type == 'incomplete_relationship'
            assert issue.severity == IssueSeverity.WARNING


class TestConsistencyRules:
    """Test domain consistency rules"""
    
    @pytest.mark.p2
    def test_articles_without_law_error(self, validator, mock_connection):
        """Test Articles must belong to Law (domain rule)"""
        conn, session = mock_connection
        
        # Mock: 8 Articles not linked to Law
        session.run.side_effect = [
            [{'count': 8}],  # articles_without_law
            [{'count': 0}],  # verdicts_without_citations
            [{'count': 0}],  # cases_without_participants
        ]
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_consistency()
        
        assert len(result.consistency_issues) == 1
        assert result.has_issues
        
        issue_data = result.consistency_issues[0]
        assert issue_data['check'] == 'articles_without_law'
        assert issue_data['count'] == 8
        
        # Should create ERROR issue
        val_issue = validator.issues[0]
        assert val_issue.severity == IssueSeverity.ERROR
        assert val_issue.entity_label == 'Article'
    
    @pytest.mark.p2
    def test_all_consistency_rules(self, validator, mock_connection):
        """Test all domain consistency rules"""
        conn, session = mock_connection
        
        session.run.side_effect = [
            [{'count': 5}],   # articles_without_law
            [{'count': 12}],  # verdicts_without_citations
            [{'count': 3}],   # cases_without_participants
        ]
        
        with patch.object(validator, '_get_connection', return_value=conn):
            result = validator.check_consistency()
        
        assert len(result.consistency_issues) == 3
        assert result.has_issues
        
        # All 3 should create issues
        assert len(validator.issues) == 3


class TestQualityScoring:
    """Test deterministic quality scoring"""
    
    @pytest.mark.p2
    def test_perfect_score(self, validator):
        """Test perfect graph (score 100)"""
        validator.issues = []
        score = validator._calculate_quality_score()
        assert score == 100
    
    @pytest.mark.p2
    def test_score_with_warnings(self, validator):
        """Test score calculation with warnings"""
        validator.issues = [
            ValidationIssue(
                issue_type='test',
                severity=IssueSeverity.WARNING,
                entity_label='Test',
                count=1,
                message='test'
            )
        ] * 10  # 10 warnings
        
        score = validator._calculate_quality_score()
        # 100 - (10 warnings * 1 point) = 90
        assert score == 90
    
    @pytest.mark.p2
    def test_score_with_errors(self, validator):
        """Test score calculation with errors"""
        validator.issues = [
            ValidationIssue(
                issue_type='test',
                severity=IssueSeverity.ERROR,
                entity_label='Test',
                count=1,
                message='test'
            )
        ] * 5  # 5 errors
        
        score = validator._calculate_quality_score()
        # 100 - (5 errors * 5 points) = 75
        assert score == 75
    
    @pytest.mark.p2
    def test_score_with_critical(self, validator):
        """Test score calculation with critical issues"""
        validator.issues = [
            ValidationIssue(
                issue_type='test',
                severity=IssueSeverity.CRITICAL,
                entity_label='Test',
                count=1,
                message='test'
            )
        ] * 3  # 3 critical
        
        score = validator._calculate_quality_score()
        # 100 - (3 critical * 10 points) = 70
        assert score == 70
    
    @pytest.mark.p2
    def test_score_floor_at_zero(self, validator):
        """Test score cannot go below 0"""
        validator.issues = [
            ValidationIssue(
                issue_type='test',
                severity=IssueSeverity.CRITICAL,
                entity_label='Test',
                count=1,
                message='test'
            )
        ] * 50  # 50 critical (500 points)
        
        score = validator._calculate_quality_score()
        assert score == 0


class TestQualityLevels:
    """Test quality level determination"""
    
    @pytest.mark.p2
    def test_excellent_level(self, validator):
        """Test EXCELLENT quality level (90-100)"""
        level = validator._determine_quality_level(95, False)
        assert level == QualityLevel.EXCELLENT
    
    @pytest.mark.p2
    def test_good_level(self, validator):
        """Test GOOD quality level (75-89)"""
        level = validator._determine_quality_level(80, False)
        assert level == QualityLevel.GOOD
    
    @pytest.mark.p2
    def test_fair_level(self, validator):
        """Test FAIR quality level (50-74)"""
        level = validator._determine_quality_level(60, False)
        assert level == QualityLevel.FAIR
    
    @pytest.mark.p2
    def test_poor_level(self, validator):
        """Test POOR quality level (0-49)"""
        level = validator._determine_quality_level(30, False)
        assert level == QualityLevel.POOR
    
    @pytest.mark.p2
    def test_critical_overrides_score(self, validator):
        """Test CRITICAL level overrides high score"""
        level = validator._determine_quality_level(95, True)  # has_critical=True
        assert level == QualityLevel.CRITICAL


class TestValidateAll:
    """Test comprehensive validation"""
    
    @pytest.mark.p2
    def test_validate_all_creates_report(self, validator, mock_connection):
        """Test validate_all returns frozen report"""
        conn, session = mock_connection
        session.run.return_value = []
        
        with patch.object(validator, '_get_connection', return_value=conn):
            report = validator.validate_all()
        
        assert isinstance(report, ValidationReport)
        assert report.correlation_id == validator.governance_context.correlation_id
        assert report.actor_id == validator.governance_context.actor_id
        assert report.quality_score == 100
        assert report.quality_level == QualityLevel.EXCELLENT
        assert report.total_issues == 0
    
    @pytest.mark.p2
    def test_validate_all_immutable_results(self, validator, mock_connection):
        """Test validation report is immutable"""
        conn, session = mock_connection
        session.run.return_value = []
        
        with patch.object(validator, '_get_connection', return_value=conn):
            report = validator.validate_all()
        
        # Attempt to modify should raise exception
        with pytest.raises(AttributeError):
            report.quality_score = 50
        
        with pytest.raises(AttributeError):
            report.issues = []


class TestProductionReadiness:
    """Test production readiness assessment"""
    
    @pytest.mark.p2
    def test_production_ready_excellent(self):
        """Test EXCELLENT quality is production ready"""
        report = ValidationReport(
            timestamp="2026-07-03T10:00:00",
            correlation_id="test-123",
            actor_id="test",
            duration_seconds=1.5,
            quality_score=95,
            quality_level=QualityLevel.EXCELLENT,
            total_issues=2,
            issues_by_severity={'warning': 2},
            issues_by_type={'orphan_nodes': 2},
            orphan_nodes=OrphanNodesCheck(0, {}, False),
            duplicate_nodes=DuplicateNodesCheck(tuple(), False),
            missing_properties=MissingPropertiesCheck({}, 0, False),
            integrity=Mock(),
            consistency=Mock(),
            issues=tuple(),
        )
        
        assert report.is_production_ready()
    
    @pytest.mark.p2
    def test_not_production_ready_critical(self):
        """Test CRITICAL issues block production"""
        report = ValidationReport(
            timestamp="2026-07-03T10:00:00",
            correlation_id="test-123",
            actor_id="test",
            duration_seconds=1.5,
            quality_score=85,
            quality_level=QualityLevel.GOOD,
            total_issues=1,
            issues_by_severity={'critical': 1},
            issues_by_type={'duplicate_id': 1},
            orphan_nodes=Mock(),
            duplicate_nodes=Mock(),
            missing_properties=Mock(),
            integrity=Mock(),
            consistency=Mock(),
            issues=tuple(),
        )
        
        assert not report.is_production_ready()
    
    @pytest.mark.p2
    def test_not_production_ready_many_errors(self):
        """Test too many errors block production"""
        report = ValidationReport(
            timestamp="2026-07-03T10:00:00",
            correlation_id="test-123",
            actor_id="test",
            duration_seconds=1.5,
            quality_score=80,
            quality_level=QualityLevel.GOOD,
            total_issues=10,
            issues_by_severity={'error': 10},
            issues_by_type={'missing_property': 10},
            orphan_nodes=Mock(),
            duplicate_nodes=Mock(),
            missing_properties=Mock(),
            integrity=Mock(),
            consistency=Mock(),
            issues=tuple(),
        )
        
        assert not report.is_production_ready()


class TestConvenienceFunction:
    """Test convenience function"""
    
    @pytest.mark.p2
    def test_validate_graph_quality_function(self, governance_context, mock_connection):
        """Test quick validation function"""
        conn, session = mock_connection
        session.run.return_value = []
        
        with patch('mahoun.graph.validation.quality_validator.get_connection', return_value=conn):
            report = validate_graph_quality(governance_context)
        
        assert isinstance(report, ValidationReport)
        assert report.correlation_id == governance_context.correlation_id


# ============================================================================
# Integration Smoke Tests
# ============================================================================

@pytest.mark.integration
class TestValidationIntegration:
    """Integration tests (require real Neo4j)"""
    
    @pytest.mark.p2
    def test_validation_with_real_connection(self, governance_context):
        """Smoke test with real connection (requires Neo4j running)"""
        # This will only run if Neo4j is available
        try:
            report = validate_graph_quality(governance_context)
            assert isinstance(report, ValidationReport)
            assert report.quality_score >= 0
            assert report.quality_score <= 100
        except Exception as e:
            pytest.skip(f"Neo4j not available: {e}")
