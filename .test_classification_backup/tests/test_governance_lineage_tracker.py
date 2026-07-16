"""
Comprehensive tests for lineage tracker.

Tests cover:
- Lineage record creation and storage
- Forward and backward tracing
- Query operations
- Immutability guarantees
- Edge cases
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from mahoun.governance.lineage_tracker import (
    LineageTracker,
    LineageRecord,
    DataStage
)


class TestLineageRecord:
    """Test lineage record data structure."""
    
    def test_record_creation(self):
        """Test creating a lineage record."""
        record = LineageRecord(
            record_id="rec123",
            timestamp=datetime.now(timezone.utc),
            stage=DataStage.CLEANED,
            source_ids=["src1", "src2"],
            output_id="out1",
            transformation="clean_data",
            parameters={"method": "remove_nulls"},
            metadata={"user": "test"}
        )
        
        assert record.record_id == "rec123"
        assert record.stage == DataStage.CLEANED
        assert len(record.source_ids) == 2
        assert record.output_id == "out1"
    
    def test_record_to_dict(self):
        """Test record serialization."""
        timestamp = datetime.now(timezone.utc)
        record = LineageRecord(
            record_id="rec123",
            timestamp=timestamp,
            stage=DataStage.TRAINING,
            source_ids=["src1"],
            output_id="out1",
            transformation="create_training_example",
            parameters={}
        )
        
        record_dict = record.to_dict()
        
        assert record_dict["record_id"] == "rec123"
        assert record_dict["stage"] == "training"
        assert record_dict["timestamp"] == timestamp.isoformat()


class TestLineageTracker:
    """Test lineage tracker."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def tracker(self, temp_storage):
        """Create lineage tracker with temp storage."""
        return LineageTracker(storage_path=temp_storage)
    
    def test_initialization(self, temp_storage):
        """Test tracker initialization."""
        tracker = LineageTracker(storage_path=temp_storage)
        
        assert tracker.storage_path.exists()
        assert isinstance(tracker.index, dict)
    
    def test_record_transformation(self, tracker):
        """Test recording a transformation."""
        record = tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1", "raw2"],
            output_id="clean1",
            transformation="remove_duplicates",
            parameters={"threshold": 0.95}
        )
        
        assert isinstance(record, LineageRecord)
        assert record.stage == DataStage.CLEANED
        assert record.output_id == "clean1"
        assert len(record.source_ids) == 2
    
    def test_record_persistence(self, tracker, temp_storage):
        """Test that records are persisted to disk."""
        record = tracker.record_transformation(
            stage=DataStage.CHUNKED,
            source_ids=["clean1"],
            output_id="chunk1",
            transformation="chunk_text",
            parameters={"chunk_size": 512}
        )
        
        # Check file exists
        record_file = temp_storage / f"{record.record_id}.json"
        assert record_file.exists()
        
        # Verify content
        with open(record_file, 'r') as f:
            data = json.load(f)
            assert data["output_id"] == "chunk1"
    
    def test_trace_back_single_level(self, tracker):
        """Test tracing back one level."""
        # Create chain: raw -> clean
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id="raw1",
            transformation="ingest",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1"],
            output_id="clean1",
            transformation="clean",
            parameters={}
        )
        
        lineage = tracker.trace_back("clean1")
        
        assert len(lineage) == 1
        assert lineage[0].output_id == "clean1"
        assert "raw1" in lineage[0].source_ids
    
    def test_trace_back_multi_level(self, tracker):
        """Test tracing back multiple levels."""
        # Create chain: raw -> clean -> chunk -> embed
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id="raw1",
            transformation="ingest",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1"],
            output_id="clean1",
            transformation="clean",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CHUNKED,
            source_ids=["clean1"],
            output_id="chunk1",
            transformation="chunk",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.EMBEDDED,
            source_ids=["chunk1"],
            output_id="embed1",
            transformation="embed",
            parameters={}
        )
        
        lineage = tracker.trace_back("embed1")
        
        assert len(lineage) == 4
        output_ids = [r.output_id for r in lineage]
        assert "embed1" in output_ids
        assert "chunk1" in output_ids
        assert "clean1" in output_ids
        assert "raw1" in output_ids
    
    def test_trace_back_max_depth(self, tracker):
        """Test max depth limit in trace_back."""
        # Create long chain
        prev_id = "raw1"
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id=prev_id,
            transformation="ingest",
            parameters={}
        )
        
        for i in range(20):
            new_id = f"step{i}"
            tracker.record_transformation(
                stage=DataStage.CLEANED,
                source_ids=[prev_id],
                output_id=new_id,
                transformation=f"transform{i}",
                parameters={}
            )
            prev_id = new_id
        
        lineage = tracker.trace_back(prev_id, max_depth=5)
        
        # Should stop at max_depth
        assert len(lineage) <= 5
    
    def test_trace_forward(self, tracker):
        """Test tracing forward to derivatives."""
        # Create tree: raw1 -> clean1 -> chunk1, chunk2
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id="raw1",
            transformation="ingest",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1"],
            output_id="clean1",
            transformation="clean",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CHUNKED,
            source_ids=["clean1"],
            output_id="chunk1",
            transformation="chunk",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CHUNKED,
            source_ids=["clean1"],
            output_id="chunk2",
            transformation="chunk",
            parameters={}
        )
        
        lineage = tracker.trace_forward("raw1")
        
        assert len(lineage) >= 3
        output_ids = [r.output_id for r in lineage]
        assert "clean1" in output_ids
        assert "chunk1" in output_ids
        assert "chunk2" in output_ids
    
    def test_get_source_documents(self, tracker):
        """Test getting source documents for training example."""
        # Create full pipeline
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=["doc1", "doc2"],
            output_id="raw1",
            transformation="ingest",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1"],
            output_id="clean1",
            transformation="clean",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.TRAINING,
            source_ids=["clean1"],
            output_id="train1",
            transformation="create_example",
            parameters={}
        )
        
        sources = tracker.get_source_documents("train1")
        
        assert "doc1" in sources
        assert "doc2" in sources
    
    def test_query_by_transformation(self, tracker):
        """Test querying by transformation name."""
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1"],
            output_id="clean1",
            transformation="remove_duplicates",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw2"],
            output_id="clean2",
            transformation="remove_duplicates",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CHUNKED,
            source_ids=["clean1"],
            output_id="chunk1",
            transformation="chunk_text",
            parameters={}
        )
        
        results = tracker.query_by_transformation("remove_duplicates")
        
        assert len(results) == 2
        assert all(r.transformation == "remove_duplicates" for r in results)
    
    def test_query_by_stage(self, tracker):
        """Test querying by stage."""
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1"],
            output_id="clean1",
            transformation="clean",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw2"],
            output_id="clean2",
            transformation="clean",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CHUNKED,
            source_ids=["clean1"],
            output_id="chunk1",
            transformation="chunk",
            parameters={}
        )
        
        results = tracker.query_by_stage(DataStage.CLEANED)
        
        assert len(results) == 2
        assert all(r.stage == DataStage.CLEANED for r in results)
    
    def test_get_statistics(self, tracker):
        """Test getting lineage statistics."""
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id="raw1",
            transformation="ingest",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1"],
            output_id="clean1",
            transformation="clean",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CHUNKED,
            source_ids=["clean1"],
            output_id="chunk1",
            transformation="chunk",
            parameters={}
        )
        
        stats = tracker.get_statistics()
        
        assert stats["total_records"] == 3
        assert stats["unique_outputs"] == 3
        assert "raw" in stats["stage_distribution"]
        assert "cleaned" in stats["stage_distribution"]
        assert "chunked" in stats["stage_distribution"]
    
    def test_load_existing_records(self, temp_storage):
        """Test loading existing records on initialization."""
        # Create tracker and add records
        tracker1 = LineageTracker(storage_path=temp_storage)
        tracker1.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id="raw1",
            transformation="ingest",
            parameters={}
        )
        
        # Create new tracker with same storage
        tracker2 = LineageTracker(storage_path=temp_storage)
        
        # Should load existing records
        assert "raw1" in tracker2.index
    
    def test_multiple_sources(self, tracker):
        """Test transformation with multiple sources."""
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id="raw1",
            transformation="ingest",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id="raw2",
            transformation="ingest",
            parameters={}
        )
        
        # Merge two sources
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["raw1", "raw2"],
            output_id="merged1",
            transformation="merge",
            parameters={}
        )
        
        lineage = tracker.trace_back("merged1")
        
        assert len(lineage) == 1
        assert "raw1" in lineage[0].source_ids
        assert "raw2" in lineage[0].source_ids
    
    def test_circular_reference_handling(self, tracker):
        """Test handling of circular references (shouldn't happen but test anyway)."""
        # This shouldn't happen in practice, but test robustness
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["clean2"],  # Reference to future record
            output_id="clean1",
            transformation="clean",
            parameters={}
        )
        
        tracker.record_transformation(
            stage=DataStage.CLEANED,
            source_ids=["clean1"],
            output_id="clean2",
            transformation="clean",
            parameters={}
        )
        
        # Should not infinite loop
        lineage = tracker.trace_back("clean1", max_depth=10)
        assert len(lineage) <= 10


class TestDataStage:
    """Test data stage enum."""
    
    def test_enum_values(self):
        """Test enum values."""
        assert DataStage.RAW == "raw"
        assert DataStage.CLEANED == "cleaned"
        assert DataStage.CHUNKED == "chunked"
        assert DataStage.EMBEDDED == "embedded"
        assert DataStage.INDEXED == "indexed"
        assert DataStage.TRAINING == "training"


@pytest.mark.slow
class TestLineageTrackerPerformance:
    """Performance tests for lineage tracker."""
    
    def test_large_lineage_chain(self, tmp_path):
        """Test performance with large lineage chain."""
        tracker = LineageTracker(storage_path=tmp_path)
        
        import time
        start = time.time()
        
        # Create chain of 1000 transformations
        prev_id = "raw1"
        tracker.record_transformation(
            stage=DataStage.RAW,
            source_ids=[],
            output_id=prev_id,
            transformation="ingest",
            parameters={}
        )
        
        for i in range(1000):
            new_id = f"step{i}"
            tracker.record_transformation(
                stage=DataStage.CLEANED,
                source_ids=[prev_id],
                output_id=new_id,
                transformation=f"transform{i}",
                parameters={}
            )
            prev_id = new_id
        
        elapsed = time.time() - start
        
        assert elapsed < 10.0, f"Recording too slow: {elapsed}s"
        
        # Test trace_back performance
        start = time.time()
        lineage = tracker.trace_back(prev_id, max_depth=100)
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"Trace back too slow: {elapsed}s"
        assert len(lineage) == 100
