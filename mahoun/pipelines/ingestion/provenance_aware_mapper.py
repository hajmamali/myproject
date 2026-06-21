"""
Provenance-Aware NER-Chunk Mapper
==================================

Maps NER-extracted entities back to their source chunks with accurate provenance.
Fixes the coordinate misalignment between chunk-based processing and full-text NER.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ChunkInfo:
    """Structured representation of a text chunk for provenance mapping."""
    chunk_id: str
    doc_id: str
    start: int  # Start position in original document
    end: int    # End position in original document
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0  # Sequential index within document


@dataclass
class EntityProvenance:
    """Provenance information for an entity."""
    chunk_id: Optional[str]
    chunk_relative_start: int
    chunk_relative_end: int
    chunk_index: Optional[int]
    provenance_method: str
    confidence_adjustment: float = 0.0
    warnings: List[str] = field(default_factory=list)


class ProvenanceAwareNERMapper:
    """
    Maps NER entities to their source chunks with precise provenance tracking.
    
    Handles:
    - Entities contained within single chunks
    - Entities spanning chunk boundaries
    - Entities in processing gaps (should not occur with proper chunking)
    - Overlap regions to prevent duplicate entity attribution
    """
    
    def __init__(self, overlap_handling_strategy: str = "assign_to_first"):
        """
        Initialize the provenance mapper.
        
        Args:
            overlap_handling_strategy: How to handle entities in overlap regions:
                - "assign_to_first": Assign to the first chunk containing the entity
                - "assign_to_last": Assign to the last chunk containing the entity
                - "split_attribution": Create separate attributions (not recommended for nodes)
                - "highest_confidence": Assign to chunk where entity has most context
        """
        self.chunk_map: Dict[str, List[ChunkInfo]] = {}  # doc_id -> list of chunks
        self.overlap_strategy = overlap_handling_strategy
        
    def register_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Register chunks for provenance mapping.
        
        Args:
            chunks: List of chunk dictionaries with standard Chunk attributes:
                - chunk_id: Unique identifier
                - doc_id: Source document identifier
                - start: Start position in document
                - end: End position in document
                - text: Chunk text content
                - metadata: Additional chunk metadata
                - chunk_index: Sequential index (optional, will be derived if missing)
        """
        for chunk_dict in chunks:
            # Ensure required fields are present
            required_fields = ["chunk_id", "doc_id", "start", "end", "text"]
            for field in required_fields:
                if field not in chunk_dict:
                    raise ValueError(f"Chunk missing required field: {field}")
            
            chunk_info = ChunkInfo(
                chunk_id=chunk_dict["chunk_id"],
                doc_id=chunk_dict["doc_id"],
                start=chunk_dict["start"],
                end=chunk_dict["end"],
                text=chunk_dict["text"],
                metadata=chunk_dict.get("metadata", {}),
                chunk_index=chunk_dict.get("chunk_index", 0)
            )
            
            doc_id = chunk_info.doc_id
            if doc_id not in self.chunk_map:
                self.chunk_map[doc_id] = []
            self.chunk_map[doc_id].append(chunk_info)
        
        # Sort chunks by start position for efficient lookup
        for doc_id in self.chunk_map:
            self.chunk_map[doc_id].sort(key=lambda x: x.start)
            # Re-assign chunk indices based on sorted order
            for i, chunk in enumerate(self.chunk_map[doc_id]):
                chunk.chunk_index = i
    
    def map_entities_to_chunks(
        self, 
        entities: List[Dict[str, Any]], 
        doc_id: str
    ) -> List[Dict[str, Any]]:
        """
        Map NER entities to their source chunks with provenance metadata.
        
        Args:
            entities: List of entity dictionaries from NER with:
                - text: Entity text
                - start: Start position in document (0-based, inclusive)
                - end: End position in document (0-based, exclusive)
                - confidence: Extraction confidence (0.0 to 1.0)
                - ... other entity-specific fields
            doc_id: Document identifier
            
        Returns:
            List of entities with added provenance information:
                - All original entity fields preserved
                - Added: chunk_id, chunk_relative_start, chunk_relative_end, 
                         chunk_index, provenance_method, provenance_warnings
        """
        if doc_id not in self.chunk_map:
            # No chunks registered for this document - return entities with provenance warnings
            mapped_entities = []
            for entity in entities:
                mapped_entity = entity.copy()
                provenance = EntityProvenance(
                    chunk_id=None,
                    chunk_relative_start=entity["start"],
                    chunk_relative_end=entity["end"],
                    chunk_index=None,
                    provenance_method="no_chunks_registered",
                    warnings=[f"No chunks registered for doc_id {doc_id}"]
                )
                mapped_entity["provenance"] = self._provenance_to_dict(provenance)
                mapped_entities.append(mapped_entity)
            return mapped_entities
        
        chunks = self.chunk_map[doc_id]
        mapped_entities = []
        
        for entity in entities:
            # Validate entity positions
            if "start" not in entity or "end" not in entity:
                # Skip entities without position information
                mapped_entity = entity.copy()
                provenance = EntityProvenance(
                    chunk_id=None,
                    chunk_relative_start=0,
                    chunk_relative_end=0,
                    chunk_index=None,
                    provenance_method="missing_position_data",
                    warnings=["Entity missing start/end position data"]
                )
                mapped_entity["provenance"] = self._provenance_to_dict(provenance)
                mapped_entities.append(mapped_entity)
                continue
                
            entity_start = entity["start"]
            entity_end = entity["end"]
            
            # Validate position ordering
            if entity_start > entity_end:
                # Swap if backwards
                entity_start, entity_end = entity_end, entity_start
            
            # Find provenance for this entity
            provenance = self._determine_entity_provenance(
                entity_start, entity_end, chunks, entity
            )
            
            # Add provenance to entity
            mapped_entity = entity.copy()
            mapped_entity["provenance"] = self._provenance_to_dict(provenance)
            mapped_entities.append(mapped_entity)
            
        return mapped_entities
    
    def _determine_entity_provenance(
        self, 
        entity_start: int, 
        entity_end: int, 
        chunks: List[ChunkInfo],
        entity: Dict[str, Any]
    ) -> EntityProvenance:
        """
        Determine the provenance of an entity relative to chunks.
        """
        # Find all chunks that overlap with this entity
        overlapping_chunks = []
        for chunk in chunks:
            # Check for overlap: not (chunk_end <= entity_start OR chunk_start >= entity_end)
            if not (chunk.end <= entity_start or chunk.start >= entity_end):
                overlapping_chunks.append(chunk)
        
        if not overlapping_chunks:
            # Entity falls in a processing gap
            return EntityProvenance(
                chunk_id=None,
                chunk_relative_start=entity_start,
                chunk_relative_end=entity_end,
                chunk_index=None,
                provenance_method="entity_in_processing_gap",
                warnings=[f"Entity at [{entity_start}, {entity_end}) falls in chunk gap"]
            )
        
        # Check if entity is fully contained within a single chunk
        containing_chunks = [
            chunk for chunk in overlapping_chunks
            if chunk.start <= entity_start and entity_end <= chunk.end
        ]
        
        if len(containing_chunks) == 1:
            # Entity fully contained in exactly one chunk
            chunk = containing_chunks[0]
            return EntityProvenance(
                chunk_id=chunk.chunk_id,
                chunk_relative_start=entity_start - chunk.start,
                chunk_relative_end=entity_end - chunk.start,
                chunk_index=chunk.chunk_index,
                provenance_method="contained_in_single_chunk",
                confidence_adjustment=0.0  # No adjustment for clean containment
            )
        
        # Entity spans multiple chunks or overlaps with multiple chunks
        if self.overlap_strategy == "assign_to_first":
            selected_chunk = overlapping_chunks[0]
        elif self.overlap_strategy == "assign_to_last":
            selected_chunk = overlapping_chunks[-1]
        elif self.overlap_strategy == "highest_confidence":
            # Select chunk where entity has the most context
            selected_chunk = max(overlapping_chunks, key=lambda c:
                min(c.end, entity_end) - max(c.start, entity_start)
            )
        else:
            # Default to first chunk
            selected_chunk = overlapping_chunks[0]
        
        # Calculate overlap with selected chunk
        overlap_start = max(selected_chunk.start, entity_start)
        overlap_end = min(selected_chunk.end, entity_end)
        
        # Calculate what portion of entity is in this chunk
        entity_length = max(1, entity_end - entity_start)  # Avoid division by zero
        overlap_length = max(0, overlap_end - overlap_start)
        coverage_ratio = overlap_length / entity_length
        
        # Determine if this is a boundary case
        is_boundary_case = (
            entity_start < selected_chunk.start or 
            entity_end > selected_chunk.end
        )
        
        warnings = []
        if coverage_ratio < 1.0:
            warnings.append(f"Entity only {coverage_ratio:.1%} contained in selected chunk")
        if is_boundary_case:
            warnings.append("Entity spans chunk boundary")
        if len(overlapping_chunks) > 1:
            warnings.append(f"Entity overlaps with {len(overlapping_chunks)} chunks")
        
        return EntityProvenance(
            chunk_id=selected_chunk.chunk_id,
            chunk_relative_start=overlap_start - selected_chunk.start,
            chunk_relative_end=overlap_end - selected_chunk.start,
            chunk_index=selected_chunk.chunk_index,
            provenance_method="overlap_assignment",
            confidence_adjustment=-0.1 * (1.0 - coverage_ratio),  # Reduce confidence for partial overlap
            warnings=warnings
        )
    
    def _provenance_to_dict(self, provenance: EntityProvenance) -> Dict[str, Any]:
        """Convert EntityProvenance to dictionary for entity attachment."""
        return {
            "chunk_id": provenance.chunk_id,
            "chunk_relative_start": provenance.chunk_relative_start,
            "chunk_relative_end": provenance.chunk_relative_end,
            "chunk_index": provenance.chunk_index,
            "provenance_method": provenance.provenance_method,
            "confidence_adjustment": provenance.confidence_adjustment,
            "warnings": provenance.warnings
        }
    
    def get_mapping_statistics(self, doc_id: str) -> Dict[str, Any]:
        """
        Get statistics about chunk mapping for a document.
        """
        if doc_id not in self.chunk_map:
            return {"error": f"No chunks registered for doc_id {doc_id}"}
        
        chunks = self.chunk_map[doc_id]
        if not chunks:
            return {"error": f"No chunks found for doc_id {doc_id}"}
        
        # Calculate coverage and overlap
        total_covered = 0
        overlap_regions = []
        
        sorted_chunks = sorted(chunks, key=lambda x: x.start)
        prev_end = 0
        
        for chunk in sorted_chunks:
            if chunk.start > prev_end:
                # Gap detected
                overlap_regions.append({
                    "type": "gap",
                    "start": prev_end,
                    "end": chunk.start,
                    "size": chunk.start - prev_end
                })
            elif chunk.end > prev_end:
                # Overlap detected
                overlap_regions.append({
                    "type": "overlap",
                    "start": prev_end,
                    "end": chunk.end,
                    "size": chunk.end - prev_end
                })
            
            total_covered += chunk.end - chunk.start
            prev_end = max(prev_end, chunk.end)
        
        total_document_length = chunks[-1].end if chunks else 0
        coverage_pct = (total_covered / max(1, total_document_length)) * 100
        
        return {
            "doc_id": doc_id,
            "chunk_count": len(chunks),
            "total_covered_chars": total_covered,
            "estimated_document_length": total_document_length,
            "coverage_percentage": round(coverage_pct, 2),
            "overlap_regions": overlap_regions,
            "chunk_details": [
                {
                    "chunk_id": c.chunk_id,
                    "start": c.start,
                    "end": c.end,
                    "size": c.end - c.start,
                    "index": c.chunk_index
                }
                for c in chunks
            ]
        }


# Convenience function for easy integration
def map_ner_entities_to_chunks(
    entities: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    doc_id: str,
    overlap_strategy: str = "assign_to_first"
) -> List[Dict[str, Any]]:
    """
    Convenience function to map NER entities to chunks with provenance.
    
    Args:
        entities: List of entity dictionaries from NER
        chunks: List of chunk dictionaries
        doc_id: Document identifier
        overlap_strategy: Strategy for handling overlap regions
        
    Returns:
        List of entities with provenance information attached
    """
    mapper = ProvenanceAwareNERMapper(overlap_handling_strategy=overlap_strategy)
    mapper.register_chunks(chunks)
    return mapper.map_entities_to_chunks(entities, doc_id)