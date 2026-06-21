"""
Data Lineage Tracking
======================

Complete data flow tracking from raw data to training examples.

Features:
- Track transformations at each stage
- Link training examples back to source documents
- Immutable lineage records in ledger
- Audit query support
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataStage(str, Enum):
    """Data processing stages."""
    RAW = "raw"
    CLEANED = "cleaned"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    TRAINING = "training"


@dataclass
class LineageRecord:
    """Immutable lineage record."""
    record_id: str
    timestamp: datetime
    stage: DataStage
    source_ids: List[str]
    output_id: str
    transformation: str
    parameters: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "stage": self.stage.value,
            "source_ids": self.source_ids,
            "output_id": self.output_id,
            "transformation": self.transformation,
            "parameters": self.parameters,
            "metadata": self.metadata
        }


class LineageTracker:
    """
    Track complete data lineage from source to training.
    
    Provides immutable audit trail of all data transformations.
    """
    
    def __init__(self, storage_path: Path = Path("lineage_records")):
        """
        Initialize lineage tracker.
        
        Args:
            storage_path: Path to store lineage records
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory index for fast queries
        self.index: Dict[str, List[LineageRecord]] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load lineage records into memory index."""
        for record_file in self.storage_path.glob("*.json"):
            try:
                with open(record_file, 'r') as f:
                    data = json.load(f)
                    record = LineageRecord(
                        record_id=data["record_id"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        stage=DataStage(data["stage"]),
                        source_ids=data["source_ids"],
                        output_id=data["output_id"],
                        transformation=data["transformation"],
                        parameters=data["parameters"],
                        metadata=data.get("metadata", {})
                    )
                    
                    # Index by output_id
                    if record.output_id not in self.index:
                        self.index[record.output_id] = []
                    self.index[record.output_id].append(record)
                    
            except Exception as e:
                logger.error(f"Failed to load lineage record {record_file}: {e}")
    
    def record_transformation(
        self,
        stage: DataStage,
        source_ids: List[str],
        output_id: str,
        transformation: str,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LineageRecord:
        """
        Record a data transformation.
        
        Args:
            stage: Processing stage
            source_ids: List of source data IDs
            output_id: Output data ID
            transformation: Name of transformation applied
            parameters: Transformation parameters
            metadata: Additional metadata
            
        Returns:
            LineageRecord object
        """
        import uuid
        
        record = LineageRecord(
            record_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            stage=stage,
            source_ids=source_ids,
            output_id=output_id,
            transformation=transformation,
            parameters=parameters or {},
            metadata=metadata or {}
        )
        
        # Save to disk
        self._save_record(record)
        
        # Update index
        if output_id not in self.index:
            self.index[output_id] = []
        self.index[output_id].append(record)
        
        logger.debug(f"Recorded lineage: {transformation} -> {output_id}")
        return record
    
    def _save_record(self, record: LineageRecord) -> None:
        """Save lineage record to disk."""
        filename = f"{record.record_id}.json"
        filepath = self.storage_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(record.to_dict(), f, indent=2)
    
    def trace_back(self, data_id: str, max_depth: int = 10) -> List[LineageRecord]:
        """
        Trace data lineage backwards to source.
        
        Args:
            data_id: Data ID to trace
            max_depth: Maximum depth to trace
            
        Returns:
            List of LineageRecord objects in reverse chronological order
        """
        lineage = []
        current_ids = [data_id]
        visited = set()
        
        for _ in range(max_depth):
            if not current_ids:
                break
            
            next_ids = []
            for current_id in current_ids:
                if current_id in visited:
                    continue
                visited.add(current_id)
                
                # Find records where current_id is output
                if current_id in self.index:
                    for record in self.index[current_id]:
                        lineage.append(record)
                        next_ids.extend(record.source_ids)
            
            current_ids = next_ids
        
        # Sort by timestamp (newest first)
        lineage.sort(key=lambda r: r.timestamp, reverse=True)
        return lineage
    
    def trace_forward(self, data_id: str, max_depth: int = 10) -> List[LineageRecord]:
        """
        Trace data lineage forward to derivatives.
        
        Args:
            data_id: Data ID to trace
            max_depth: Maximum depth to trace
            
        Returns:
            List of LineageRecord objects in chronological order
        """
        lineage = []
        current_ids = [data_id]
        visited = set()
        
        for _ in range(max_depth):
            if not current_ids:
                break
            
            next_ids = []
            for current_id in current_ids:
                if current_id in visited:
                    continue
                visited.add(current_id)
                
                # Find records where current_id is a source
                for output_id, records in self.index.items():
                    for record in records:
                        if current_id in record.source_ids:
                            lineage.append(record)
                            next_ids.append(output_id)
            
            current_ids = next_ids
        
        # Sort by timestamp (oldest first)
        lineage.sort(key=lambda r: r.timestamp)
        return lineage
    
    def get_source_documents(self, training_example_id: str) -> List[str]:
        """
        Get source document IDs for a training example.
        
        Args:
            training_example_id: Training example ID
            
        Returns:
            List of source document IDs
        """
        lineage = self.trace_back(training_example_id)
        
        # Find RAW stage records
        source_docs = []
        for record in lineage:
            if record.stage == DataStage.RAW:
                source_docs.extend(record.source_ids)
        
        return list(set(source_docs))  # Remove duplicates
    
    def query_by_transformation(
        self,
        transformation: str,
        stage: Optional[DataStage] = None
    ) -> List[LineageRecord]:
        """
        Query lineage records by transformation name.
        
        Args:
            transformation: Transformation name
            stage: Optional stage filter
            
        Returns:
            List of matching LineageRecord objects
        """
        results = []
        
        for records in self.index.values():
            for record in records:
                if record.transformation == transformation:
                    if stage is None or record.stage == stage:
                        results.append(record)
        
        return results
    
    def query_by_stage(self, stage: DataStage) -> List[LineageRecord]:
        """
        Query lineage records by stage.
        
        Args:
            stage: Processing stage
            
        Returns:
            List of matching LineageRecord objects
        """
        results = []
        
        for records in self.index.values():
            for record in records:
                if record.stage == stage:
                    results.append(record)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get lineage statistics.
        
        Returns:
            Statistics dictionary
        """
        total_records = sum(len(records) for records in self.index.values())
        
        stage_counts = {}
        transformation_counts = {}
        
        for records in self.index.values():
            for record in records:
                stage_counts[record.stage.value] = stage_counts.get(record.stage.value, 0) + 1
                transformation_counts[record.transformation] = transformation_counts.get(record.transformation, 0) + 1
        
        return {
            "total_records": total_records,
            "unique_outputs": len(self.index),
            "stage_distribution": stage_counts,
            "transformation_distribution": transformation_counts
        }
