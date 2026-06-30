from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class RAGEvidenceNode:
    """Thin wrapper that carries RetrievalResult metadata into the graph."""
    fact_index: int
    doc_id: str
    source: str        # "graph", "text", "hybrid", "rag", etc.
    score: float
    retrieval_rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)
