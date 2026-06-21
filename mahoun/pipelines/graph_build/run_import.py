"""
Graph Build Pipeline - Official Entrypoint
===========================================
Converts parsed verdict structures into graph-ready nodes and edges.

This is the canonical pipeline that:
1. Receives normalized & parsed verdict objects
2. Converts them into nodes + edges (citations, references, law-article links)
3. Submits to Neo4j OR produces JSON batch files for background importer

Usage:
    from mahoun.pipelines.graph_build import GraphBuildPipeline
    
    pipeline = GraphBuildPipeline()
    result = pipeline.build_from_verdict(verdict_struct, source_id="verdict_001")
    
    # Or batch mode
    results = pipeline.build_batch(verdict_list)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from mahoun.core.runtime_config import get_runtime_settings, should_skip_graph

# Entity Linker Integration (Enterprise NER Subsystem)
try:
    from mahoun.pipelines.graph.entity_linker import link_entities_to_graph, EntityLinker
    HAS_ENTITY_LINKER = True
except ImportError:
    HAS_ENTITY_LINKER = False
    link_entities_to_graph: Optional[Any] = None
    EntityLinker: Optional[Any] = None
logger = logging.getLogger(__name__)


@dataclass
class GraphBuildResult:
    """Result of graph build operation"""
    success: bool
    verdict_id: str
    nodes_created: int = 0
    edges_created: int = 0
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    batch_file: Optional[str] = None  # If using batch mode


class GraphBuildPipeline:
    """
    Official Graph Build Pipeline for MAHOUN Enterprise.
    
    This pipeline converts parsed verdict structures into graph-ready format
    and either:
    - Directly submits to Neo4j (if enabled and connected)
    - Produces JSON batch files for background import
    
    The pipeline does NOT modify ingestion logic; it only attaches
    a new step after parsing.
    """
    
    def __init__(
        self,
        use_neo4j: Optional[bool] = None,
        batch_output_dir: Optional[str] = None,
        batch_size: int = 100
    ):
        """
        Initialize Graph Build Pipeline.
        
        Args:
            use_neo4j: Force Neo4j mode (None = auto-detect from runtime config)
            batch_output_dir: Directory for batch JSON files (if not using Neo4j)
            batch_size: Number of verdicts per batch file
        """
        self.settings = get_runtime_settings()
        
        # Determine mode
        if use_neo4j is None:
            self.use_neo4j = (
                self.settings.graph_enabled and 
                self.settings.graph_backend != "disabled_fallback"
            )
        else:
            self.use_neo4j = use_neo4j
        
        self.batch_output_dir = Path(batch_output_dir) if batch_output_dir else Path("./graph_batch_data")
        self.batch_size = batch_size
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_nodes": 0,
            "total_edges": 0,
            "neo4j_submissions": 0,
            "batch_files_created": 0,
            "errors": 0
        }
        
        logger.info(f"GraphBuildPipeline initialized (use_neo4j={self.use_neo4j})")
    
    def build_from_verdict(
        self,
        verdict_struct: Dict[str, Any],
        source_id: Optional[str] = None
    ) -> GraphBuildResult:
        """
        Build graph structure from a single parsed verdict.
        
        Args:
            verdict_struct: Parsed verdict dictionary (from minimal_verdict_parser)
            source_id: Optional source identifier (defaults to generated ID)
        
        Returns:
            GraphBuildResult with status and statistics
        """
        import time
        start_time = time.time()
        
        if should_skip_graph():
            logger.debug("Graph build skipped (desktop_minimal mode or graph disabled)")
            return GraphBuildResult(
                success=True,
                verdict_id=source_id or "skipped",
                error="Graph disabled in current mode"
            )
        
        try:
            # Extract nodes and edges from verdict structure
            nodes, edges = self._extract_graph_structure(verdict_struct, source_id)
            
            # Submit to Neo4j or batch file
            if self.use_neo4j:
                verdict_id = self._submit_to_neo4j(verdict_struct, nodes, edges)
            else:
                verdict_id = self._write_to_batch(verdict_struct, nodes, edges)
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Update stats
            self.stats["total_processed"] += 1
            self.stats["total_nodes"] += len(nodes)
            self.stats["total_edges"] += len(edges)
            
            logger.info(
                f"Graph build complete: {len(nodes)} nodes, {len(edges)} edges "
                f"({processing_time_ms:.1f}ms)"
            )
            
            return GraphBuildResult(
                success=True,
                verdict_id=verdict_id,
                nodes_created=len(nodes),
                edges_created=len(edges),
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Graph build failed: {e}", exc_info=True)
            self.stats["errors"] += 1
            
            return GraphBuildResult(
                success=False,
                verdict_id=source_id or "unknown",
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    def build_batch(
        self,
        verdict_list: List[Dict[str, Any]],
        source_ids: Optional[List[str]] = None
    ) -> List[GraphBuildResult]:
        """
        Build graph structures from a batch of verdicts.
        
        Args:
            verdict_list: List of parsed verdict dictionaries
            source_ids: Optional list of source identifiers
        
        Returns:
            List of GraphBuildResult objects
        """
        results: List[Any] = []
        for i, verdict_struct in enumerate(verdict_list):
            source_id = source_ids[i] if source_ids and i < len(source_ids) else None
            result = self.build_from_verdict(verdict_struct, source_id)
            results.append(result)
        
        return results
    
    def _extract_graph_structure(
        self,
        verdict_struct: Dict[str, Any],
        source_id: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract nodes and edges from verdict structure.
        
        Uses EntityLinker from NER subsystem if entities are available,
        otherwise falls back to legacy extraction.
        
        Returns:
            (nodes, edges) tuple
        """
        nodes: List[Any] = []
        edges: List[Any] = []
        # Generate verdict ID
        from mahoun.graph.neo4j.operations import _generate_verdict_id
        verdict_id = source_id or _generate_verdict_id(verdict_struct)
        
        # ========================================================================
        # Enterprise NER Subsystem Integration
        # ========================================================================
        # Check if entities are available from NER extraction
        entities = verdict_struct.get("entities", {})
        has_entities = any(
            len(entities.get(et, [])) > 0 
            for et in ["persons", "organizations", "courts", "laws", "topics"]
        )
        
        # Use EntityLinker if entities are available and linker is imported
        if has_entities and HAS_ENTITY_LINKER and link_entities_to_graph is not None:
            try:
                case_metadata = verdict_struct.get("case_meta", {})
                entity_nodes, entity_edges = link_entities_to_graph(
                    entities=entities,
                    case_id=verdict_id,
                    case_metadata=case_metadata
                )
                
                # Convert to expected format
                for node in entity_nodes:
                    nodes.append({
                        "type": node["label"],
                        "id": node["node_id"],
                        "properties": node["properties"]
                    })
                
                for edge in entity_edges:
                    edges.append({
                        "from_type": edge["from_label"],
                        "from_id": edge["from_id"],
                        "to_type": edge["to_label"],
                        "to_id": edge["to_id"],
                        "relationship": edge["relationship_type"],
                        "properties": edge.get("properties", {})
                    })
                
                logger.info(
                    f"NER_PIPELINE: Graph structure from EntityLinker - "
                    f"nodes={len(nodes)}, edges={len(edges)}"
                )
                
                return nodes, edges
                
            except Exception as e:
                logger.warning(f"EntityLinker failed, falling back to legacy extraction: {e}")
                # Fall through to legacy extraction
                nodes: List[Any] = []
                edges: List[Any] = []
        # ========================================================================
        # Legacy Graph Extraction (Fallback)
        # ========================================================================
        
        # Node 1: Verdict
        case_meta = verdict_struct.get("case_meta", {})
        nodes.append({
            "type": "Verdict",
            "id": verdict_id,
            "properties": {
                "verdict_id": verdict_id,
                "court_level": case_meta.get("court_level", "نامشخص"),
                "procedure_stage": case_meta.get("procedure_stage", "نامشخص"),
                "case_type": case_meta.get("case_type", "نامشخص"),
                "is_final": case_meta.get("is_final", False),
                "finality_basis": case_meta.get("finality_basis", "")
            }
        })
        
        # Nodes 2-N: LawArticles
        legal_refs = verdict_struct.get("legal_references", {})
        all_articles: List[Any] = []
        all_articles.extend(legal_refs.get("substantive_law", []))
        all_articles.extend(legal_refs.get("procedural_law", []))
        
        from mahoun.graph.neo4j.operations import _parse_law_article
        
        for article_str in all_articles[:50]:  # Limit to 50
            try:
                parsed = _parse_law_article(article_str)
                article_id = f"article_{parsed['code']}_{parsed['article_no']}"
                
                nodes.append({
                    "type": "LawArticle",
                    "id": article_id,
                    "properties": {
                        "label": parsed["label"],
                        "code": parsed["code"],
                        "article_no": parsed["article_no"]
                    }
                })
                
                # Edge: Verdict -> LawArticle
                edges.append({
                    "from_type": "Verdict",
                    "from_id": verdict_id,
                    "to_type": "LawArticle",
                    "to_id": article_id,
                    "relationship": "REFERS_TO",
                    "properties": {}
                })
            except Exception as e:
                logger.warning(f"Failed to parse article '{article_str}': {e}")
        
        # Nodes: Tags
        system_tags = verdict_struct.get("system_tags", [])
        for tag in system_tags[:30]:  # Limit to 30
            tag_id = f"tag_{tag.replace(' ', '_')}"
            
            nodes.append({
                "type": "Tag",
                "id": tag_id,
                "properties": {"name": tag}
            })
            
            # Edge: Verdict -> Tag
            edges.append({
                "from_type": "Verdict",
                "from_id": verdict_id,
                "to_type": "Tag",
                "to_id": tag_id,
                "relationship": "HAS_TAG",
                "properties": {}
            })
        
        # Nodes: Persons (Parties)
        parties = verdict_struct.get("parties", {})
        
        # Third party objector
        objector = parties.get("third_party_objector")
        if objector and objector.get("name"):
            person_id = f"person_{verdict_id}_objector"
            display_name = f"{objector.get('title', '')} {objector.get('name', '')}".strip()
            
            nodes.append({
                "type": "Person",
                "id": person_id,
                "properties": {
                    "display_name": display_name,
                    "father_name": objector.get("father_name", "")
                }
            })
            
            edges.append({
                "from_type": "Verdict",
                "from_id": verdict_id,
                "to_type": "Person",
                "to_id": person_id,
                "relationship": "HAS_PARTY",
                "properties": {"role": "third_party_objector"}
            })
        
        # Respondents
        respondents = parties.get("respondents", [])
        for i, resp in enumerate(respondents[:10]):  # Limit to 10
            if resp.get("name"):
                person_id = f"person_{verdict_id}_respondent_{i}"
                display_name = f"{resp.get('title', '')} {resp.get('name', '')}".strip()
                
                nodes.append({
                    "type": "Person",
                    "id": person_id,
                    "properties": {
                        "display_name": display_name,
                        "father_name": resp.get("father_name", "")
                    }
                })
                
                edges.append({
                    "from_type": "Verdict",
                    "from_id": verdict_id,
                    "to_type": "Person",
                    "to_id": person_id,
                    "relationship": "HAS_PARTY",
                    "properties": {"role": "respondent"}
                })
        
        return nodes, edges
    
    def _submit_to_neo4j(
        self,
        verdict_struct: Dict[str, Any],
        nodes: List[Dict],
        edges: List[Dict]
    ) -> str:
        """Submit directly to Neo4j using existing operations"""
        from mahoun.graph.neo4j.operations import upsert_verdict_struct
        
        verdict_id = upsert_verdict_struct(verdict_struct)
        self.stats["neo4j_submissions"] += 1
        
        return verdict_id
    
    def _write_to_batch(
        self,
        verdict_struct: Dict[str, Any],
        nodes: List[Dict],
        edges: List[Dict]
    ) -> str:
        """Write to batch JSON file for background import"""
        from mahoun.graph.neo4j.operations import _generate_verdict_id
        
        verdict_id = _generate_verdict_id(verdict_struct)
        
        # Ensure batch directory exists
        self.batch_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create batch entry
        batch_entry = {
            "verdict_id": verdict_id,
            "verdict_struct": verdict_struct,
            "nodes": nodes,
            "edges": edges,
            "timestamp": datetime.now().isoformat()
        }
        
        # Write to file (one file per verdict for simplicity)
        batch_file = self.batch_output_dir / f"{verdict_id}.graph.json"
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch_entry, f, ensure_ascii=False, indent=2)
        
        self.stats["batch_files_created"] += 1
        
        logger.info(f"Wrote batch file: {batch_file}")
        
        return verdict_id
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return self.stats.copy()


# ============================================================================
# Convenience Functions
# ============================================================================

def build_graph_from_verdict(
    verdict_struct: Dict[str, Any],
    source_id: Optional[str] = None
) -> GraphBuildResult:
    """
    Convenience function to build graph from a single verdict.
    
    Usage:
        from mahoun.pipelines.graph_build.run_import import build_graph_from_verdict
        
        result = build_graph_from_verdict(verdict_struct, "verdict_001")
    """
    pipeline = GraphBuildPipeline()
    return pipeline.build_from_verdict(verdict_struct, source_id)

