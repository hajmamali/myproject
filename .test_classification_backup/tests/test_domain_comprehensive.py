"""
Comprehensive Domain Module Tests
==================================
Tests for mahoun.domain modules.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any


# =============================================================================
# BASE ENGINE TESTS
# =============================================================================

class TestBaseDomainEngine:
    """Tests for BaseDomainEngine"""
    
    def test_base_engine_init(self):
        from mahoun.domain.base_engine import BaseDomainEngine
        
        # Create a concrete implementation
        class TestEngine(BaseDomainEngine):
            async def analyze(self, input_data):
                return {"result": "test"}
        
        engine = TestEngine("test_engine", {"key": "value"})
        assert engine.name == "test_engine"
        assert engine.config == {"key": "value"}
    
    def test_base_engine_default_config(self):
        from mahoun.domain.base_engine import BaseDomainEngine
        
        class TestEngine(BaseDomainEngine):
            async def analyze(self, input_data):
                return {}
        
        engine = TestEngine("test")
        assert engine.config == {}
    
    @pytest.mark.asyncio
    async def test_base_engine_validate_input(self):
        from mahoun.domain.base_engine import BaseDomainEngine
        
        class TestEngine(BaseDomainEngine):
            async def analyze(self, input_data):
                return {}
        
        engine = TestEngine("test")
        result = await engine.validate_input({"query": "test"})
        assert result is True
    
    def test_base_engine_export_json(self):
        from mahoun.domain.base_engine import BaseDomainEngine
        
        class TestEngine(BaseDomainEngine):
            async def analyze(self, input_data):
                return {}
        
        engine = TestEngine("test")
        results = {"data": "test", "score": 0.9}
        exported = engine.export_results(results, "json")
        assert exported == results
    
    def test_base_engine_export_dict(self):
        from mahoun.domain.base_engine import BaseDomainEngine
        
        class TestEngine(BaseDomainEngine):
            async def analyze(self, input_data):
                return {}
        
        engine = TestEngine("test")
        results = {"data": "test"}
        exported = engine.export_results(results, "dict")
        assert exported == results
    
    def test_base_engine_export_invalid_format(self):
        from mahoun.domain.base_engine import BaseDomainEngine
        
        class TestEngine(BaseDomainEngine):
            async def analyze(self, input_data):
                return {}
        
        engine = TestEngine("test")
        with pytest.raises(ValueError, match="Unsupported format"):
            engine.export_results({}, "xml")
    
    def test_base_engine_get_status(self):
        from mahoun.domain.base_engine import BaseDomainEngine
        
        class TestEngine(BaseDomainEngine):
            async def analyze(self, input_data):
                return {}
        
        engine = TestEngine("my_engine", {"option": True})
        status = engine.get_status()
        assert status["name"] == "my_engine"
        assert status["status"] == "ready"
        assert status["config"]["option"] is True


# =============================================================================
# TIMELINE ANALYZER TESTS
# =============================================================================

class TestTimelineAnalyzer:
    """Tests for TimelineAnalyzer"""
    
    def test_timeline_analyzer_init(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        assert analyzer.name == "timeline_analyzer"
        assert analyzer._initialized is False
        assert analyzer.timeline_agent is None
    
    def test_timeline_analyzer_init_with_config(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        config = {"max_events": 100}
        analyzer = TimelineAnalyzer(config)
        assert analyzer.config == config
    
    def test_build_visualization_data_empty(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        result = analyzer._build_visualization_data([], [])
        
        assert result["events"] == []
        assert result["conflicts"] == []
        assert result["date_range"]["start"] is None
        assert result["date_range"]["end"] is None
    
    def test_build_visualization_data_with_events(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        timeline = [
            {"date": "2024-01-01", "description": "رویداد اول", "sequence": 1},
            {"date": "2024-01-15", "description": "رویداد دوم", "sequence": 2},
            {"date": "2024-02-01", "description": "رویداد سوم", "sequence": 3}
        ]
        conflicts = [
            {"date": "2024-01-15", "type": "overlap", "conflicting_events": ["e1", "e2"]}
        ]
        
        result = analyzer._build_visualization_data(timeline, conflicts)
        
        assert len(result["events"]) == 3
        assert result["events"][0]["date"] == "2024-01-01"
        assert result["date_range"]["start"] == "2024-01-01"
        assert result["date_range"]["end"] == "2024-02-01"
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["events_count"] == 2
    
    def test_analyze_patterns_empty(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        result = analyzer._analyze_patterns([])
        assert result == {}
    
    def test_analyze_patterns_single_event(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        result = analyzer._analyze_patterns([{"date": "2024-01-01"}])
        
        assert result["total_events"] == 1
        assert result["average_interval"] == 0
    
    def test_analyze_patterns_multiple_events(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        timeline = [
            {"date": "2024-01-01"},
            {"date": "2024-01-05"},
            {"date": "2024-01-10"},
            {"date": "2024-01-15"}
        ]
        result = analyzer._analyze_patterns(timeline)
        
        assert result["total_events"] == 4
        assert result["average_interval"] == 2.0  # (1+2+3)/3
    
    def test_calculate_timeline_span_empty(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        result = analyzer._calculate_timeline_span([])
        assert result is None
    
    def test_calculate_timeline_span_single(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        result = analyzer._calculate_timeline_span([{"date": "2024-01-01"}])
        assert result is None
    
    def test_calculate_timeline_span_multiple(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        timeline = [
            {"date": "2024-01-01"},
            {"date": "2024-01-05"},
            {"date": "2024-01-10"}
        ]
        result = analyzer._calculate_timeline_span(timeline)
        assert result == 2  # len(timeline) - 1


# =============================================================================
# DISPUTE EXTRACTOR TESTS
# =============================================================================

class TestDisputeExtractionEngine:
    """Tests for DisputeExtractionEngine"""
    
    def test_dispute_engine_init(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        assert engine.name == "dispute_extractor"
        assert engine._initialized is False
        assert engine.dispute_agent is None
    
    def test_dispute_engine_init_with_config(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        config = {"severity_threshold": 0.5}
        engine = DisputeExtractionEngine(config)
        assert engine.config == config
    
    def test_calculate_severity_default(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        # Default score without keywords
        item = {"description": "یک موضوع عادی", "score": 0.5}
        severity = engine._calculate_severity(item)
        assert severity == 0.5
    
    def test_calculate_severity_critical(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        # Critical keyword
        item = {"description": "موضوع بحرانی و فوری", "score": 0.5}
        severity = engine._calculate_severity(item)
        assert severity == 0.8  # 0.5 + 0.3
    
    def test_calculate_severity_high(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        # High keyword (using "significant" which is only in high list)
        item = {"description": "موضوع significant", "score": 0.5}
        severity = engine._calculate_severity(item)
        assert severity == 0.7  # 0.5 + 0.2
    
    def test_calculate_severity_low(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        # Low keyword
        item = {"description": "یک مشکل کم اهمیت", "score": 0.5}
        severity = engine._calculate_severity(item)
        assert severity == 0.3  # 0.5 - 0.2
    
    def test_calculate_severity_max_cap(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        # Should not exceed 1.0
        item = {"description": "critical issue", "score": 0.9}
        severity = engine._calculate_severity(item)
        assert severity == 1.0  # min(1.0, 0.9 + 0.3)
    
    def test_calculate_severity_min_cap(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        # Should not go below 0.0
        item = {"description": "minor low issue", "score": 0.1}
        severity = engine._calculate_severity(item)
        assert severity == 0.0  # max(0.0, 0.1 - 0.2)
    
    def test_calculate_severity_no_description(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        # No description provided
        item = {"score": 0.6}
        severity = engine._calculate_severity(item)
        assert severity == 0.6


# =============================================================================
# DELAY NARRATIVE TESTS
# =============================================================================

class TestDelayNarrativeGenerator:
    """Tests for DelayNarrativeGenerator"""
    
    def test_delay_narrative_import(self):
        from mahoun.domain.delay_narrative import DelayNarrativeGenerator
        assert DelayNarrativeGenerator is not None
    
    def test_delay_narrative_init(self):
        from mahoun.domain.delay_narrative import DelayNarrativeGenerator
        
        engine = DelayNarrativeGenerator()
        assert engine.name == "delay_narrative_generator"


# =============================================================================
# DOMAIN INIT TESTS
# =============================================================================

class TestDomainInit:
    """Tests for domain module initialization"""
    
    def test_domain_init_imports(self):
        from mahoun.domain.base_engine import BaseDomainEngine
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        from mahoun.domain.delay_narrative import DelayNarrativeGenerator
        
        assert BaseDomainEngine is not None
        assert TimelineAnalyzer is not None
        assert DisputeExtractionEngine is not None
        assert DelayNarrativeGenerator is not None


# =============================================================================
# ASYNC TESTS WITH MOCKING
# =============================================================================

class TestTimelineAnalyzerAsync:
    """Async tests for TimelineAnalyzer with mocked dependencies"""
    
    @pytest.mark.asyncio
    async def test_analyze_success(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        
        # Mock the timeline_agent
        mock_agent = AsyncMock()
        mock_agent.process.return_value = {
            "success": True,
            "timeline": [
                {"date": "2024-01-01", "description": "رویداد اول"},
                {"date": "2024-01-15", "description": "رویداد دوم"}
            ],
            "events": ["e1", "e2"],
            "conflicts": [],
            "matrix": {},
            "metadata": {}
        }
        
        analyzer.timeline_agent = mock_agent
        analyzer._initialized = True
        
        result = await analyzer.analyze({"query": "test"})
        
        assert result["success"] is True
        assert len(result["timeline"]) == 2
        assert result["metadata"]["has_conflicts"] is False
    
    @pytest.mark.asyncio
    async def test_analyze_failure(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        
        # Mock agent returns failure
        mock_agent = AsyncMock()
        mock_agent.process.return_value = {
            "success": False,
            "error": "Analysis failed"
        }
        
        analyzer.timeline_agent = mock_agent
        analyzer._initialized = True
        
        result = await analyzer.analyze({"query": "test"})
        
        assert result["success"] is False
        assert result["error"] == "Analysis failed"
        assert result["timeline"] == []
    
    @pytest.mark.asyncio
    async def test_analyze_exception(self):
        from mahoun.domain.timeline_analyzer import TimelineAnalyzer
        
        analyzer = TimelineAnalyzer()
        
        # Mock agent raises exception
        mock_agent = AsyncMock()
        mock_agent.process.side_effect = Exception("Connection error")
        
        analyzer.timeline_agent = mock_agent
        analyzer._initialized = True
        
        result = await analyzer.analyze({"query": "test"})
        
        assert result["success"] is False
        assert "Connection error" in result["error"]


class TestDisputeExtractionAsync:
    """Async tests for DisputeExtractionEngine with mocked dependencies"""
    
    @pytest.mark.asyncio
    async def test_analyze_success(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        # Mock the dispute_agent
        mock_agent = AsyncMock()
        mock_agent.process.return_value = {
            "success": True,
            "disputes": [
                {"description": "اختلاف بحرانی", "score": 0.6}
            ],
            "violations": [
                {"description": "نقض قرارداد", "score": 0.5}
            ],
            "related_clauses": ["clause1"],
            "citations": [],
            "metadata": {}
        }
        
        engine.dispute_agent = mock_agent
        engine._initialized = True
        
        result = await engine.analyze({"query": "test"})
        
        assert result["success"] is True
        assert len(result["disputes"]) == 1
        assert result["disputes"][0]["severity"] > 0.6  # Adjusted for critical keyword
    
    @pytest.mark.asyncio
    async def test_analyze_sorts_by_severity(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        mock_agent = AsyncMock()
        mock_agent.process.return_value = {
            "success": True,
            "disputes": [
                {"description": "مشکل کم", "score": 0.3},
                {"description": "مشکل بحرانی", "score": 0.7},
                {"description": "مشکل معمولی", "score": 0.5}
            ],
            "violations": [],
            "metadata": {}
        }
        
        engine.dispute_agent = mock_agent
        engine._initialized = True
        
        result = await engine.analyze({"query": "test"})
        
        # Should be sorted by severity (highest first)
        severities = [d["severity"] for d in result["disputes"]]
        assert severities == sorted(severities, reverse=True)
    
    @pytest.mark.asyncio
    async def test_analyze_failure(self):
        from mahoun.domain.dispute_extractor import DisputeExtractionEngine
        
        engine = DisputeExtractionEngine()
        
        mock_agent = AsyncMock()
        mock_agent.process.return_value = {
            "success": False,
            "error": "Failed to extract"
        }
        
        engine.dispute_agent = mock_agent
        engine._initialized = True
        
        result = await engine.analyze({"query": "test"})
        
        assert result["success"] is False
        assert result["disputes"] == []
        assert result["violations"] == []

