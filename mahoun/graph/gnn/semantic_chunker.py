# pipelines/gnn/semantic_chunker.py
"""
Semantic Chunker with Entity Awareness for MAHOUN Legal AI

این ماژول chunking هوشمند با استفاده از:
- Semantic similarity بین جملات
- Entity-aware boundary detection
- Dynamic chunk sizing
"""

import importlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import torch

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

from mahoun.core.logging import setup_logger

utils_text = importlib.import_module("mahoun.pipelines.utils_text")
sent_tokenize_simple = utils_text.sent_tokenize_simple
normalize_fa = utils_text.normalize_fa

log = setup_logger("semantic_chunker")


@dataclass
class Chunk:
    """
    Data model for a semantic chunk

    Attributes:
        id: Unique identifier
        text: Chunk text content
        embedding: Dense embedding vector (optional)
        entities: Extracted entities by type
        metadata: Additional metadata
        coherence_score: Internal semantic coherence (0-1)
        entity_count: Total number of entities
        semantic_density: Measure of information density
        start_idx: Start position in original text
        end_idx: End position in original text
    """

    id: str
    text: str
    embedding: np.ndarray | None = None
    entities: dict[str, list[str]] = None
    metadata: dict[str, Any] = None
    coherence_score: float = 0.0
    entity_count: int = 0
    semantic_density: float = 0.0
    start_idx: int = 0
    end_idx: int = 0

    def __post_init__(self):
        if self.entities is None:
            self.entities = {}
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        d = asdict(self)
        # Convert numpy array to list for JSON serialization
        if self.embedding is not None:
            d["embedding"] = self.embedding.tolist()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        """Create Chunk from dictionary"""
        # Convert embedding list back to numpy array
        if "embedding" in data and data["embedding"] is not None:
            data["embedding"] = np.array(data["embedding"])
        return cls(**data)

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Chunk":
        """Deserialize from JSON string"""
        return cls.from_dict(json.loads(json_str))

    def save(self, path: str):
        """Save chunk to file"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "Chunk":
        """Load chunk from file"""
        with open(path, encoding="utf-8") as f:
            return cls.from_json(f.read())


class SemanticChunker:
    """
    Ultra-advanced semantic chunker with fail-closed DI.
    
    Constructor Injection Contract
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``embed_model_instance`` MUST be injected by bootstrap (primary path).
    Lazy fallback is DEPRECATED and triggers loud warnings.
    
    Architectural Mandate
    ~~~~~~~~~~~~~~~~~~~~~
    Bootstrap wiring is MANDATORY in production. Lazy construction
    exists only for backward compatibility and will be removed.
    
    Features:
    - Semantic boundary detection using embeddings
    - Entity-aware chunking (preserves legal entities)
    - Dynamic chunk sizing based on content density
    - Coherence scoring for quality assessment
    """

    def __init__(
        self,
        embed_model: str = "BAAI/bge-m3",
        ner_model: str = "HooshvareLab/bert-base-parsbert-uncased",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        batch_size: int = 32,
        embed_model_instance: Optional["SentenceTransformer"] = None,
        correlation_id: str = "",
    ):
        """
        Initialize SemanticChunker

        Args:
            embed_model: Sentence embedding model name (only used for lazy fallback)
            ner_model: NER model name
            device: Device to use (cuda/cpu)
            batch_size: Batch size for processing
            embed_model_instance: Pre-constructed SentenceTransformer (MANDATORY in production).
                                 If None, triggers DEPRECATED lazy fallback with warning.
            correlation_id: Request tracking ID for observability.
        """
        import time
        self._correlation_id = correlation_id or f"chunk-{time.time()}"
        
        log.info(f"[{self._correlation_id}] Initializing SemanticChunker on {device}")

        self.device = device
        self.batch_size = batch_size

        if embed_model_instance is not None:
            # PRIMARY PATH: Bootstrap-injected model
            self.embed_model = embed_model_instance
            self._embed_model_name = None  # Not needed when injected
            log.info(
                f"[{self._correlation_id}] ✅ SemanticChunker initialized "
                f"(bootstrap-injected embedding model)"
            )
        else:
            # FAIL-CLOSED: No construction allowed outside composition root
            raise ValueError(
                "Embedding model dependency was not injected. "
                "SemanticChunker requires a pre-constructed SentenceTransformer "
                "instance via the `embed_model_instance` parameter. "
                "Construction is only permitted in bootstrap/composition root. "
                "Remediation: Update bootstrap/runtime.py to inject SentenceTransformer."
            )

        # Load NER model
        tokenizer = AutoTokenizer.from_pretrained(
            ner_model,
            local_files_only=True  # AirGap: block HuggingFace downloads
        )
        model = AutoModelForTokenClassification.from_pretrained(
            ner_model,
            local_files_only=True  # AirGap: block HuggingFace downloads
        )
        self.ner_pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
            device=0 if device == "cuda" else -1,
        )
        log.info("NER model loaded")

    def _get_embed_model(self):
        """Return the injected embedding model. Fail-closed if not available."""
        if self.embed_model is None:
            raise ValueError(
                "Embedding model dependency was not injected. "
                "This should never happen — constructor enforces injection."
            )
        return self.embed_model

    def _compute_embeddings(self, sentences: list[str]) -> np.ndarray:
        """
        Compute embeddings for sentences

        Args:
            sentences: List of sentences

        Returns:
            Array of embeddings (n_sentences, embed_dim)
        """
        embeddings = self._get_embed_model().encode(
            sentences,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings

    def _compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Compute pairwise cosine similarity matrix

        Args:
            embeddings: Sentence embeddings

        Returns:
            Similarity matrix (n_sentences, n_sentences)
        """
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-8)

        # Compute cosine similarity
        similarity = np.dot(normalized, normalized.T)
        return similarity

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        """
        Extract entities from text using NER

        Args:
            text: Input text

        Returns:
            Dictionary of entity type -> list of entities
        """
        # Limit text length for NER (model constraint)
        text_truncated = text[:4000]

        try:
            entities_raw = self.ner_pipeline(text_truncated)

            # Group by entity type
            entities = {}
            for ent in entities_raw:
                entity_type = ent["entity_group"]
                entity_text = ent["word"]

                if entity_type not in entities:
                    entities[entity_type] = []
                entities[entity_type].append(entity_text)

            return entities
        except Exception as e:
            log.warning(f"NER extraction failed: {e}")
            return {}

    def _find_entity_positions(self, text: str, entities: dict[str, list[str]]) -> list[tuple[int, int]]:
        """
        Find positions of entities in text

        Args:
            text: Input text
            entities: Dictionary of entities

        Returns:
            List of (start, end) positions
        """
        positions = []
        for entity_list in entities.values():
            for entity in entity_list:
                # Find all occurrences
                start = 0
                while True:
                    pos = text.find(entity, start)
                    if pos == -1:
                        break
                    positions.append((pos, pos + len(entity)))
                    start = pos + 1

        # Sort and merge overlapping positions
        positions.sort()
        merged = []
        for start, end in positions:
            if merged and start <= merged[-1][1]:
                # Merge overlapping
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        return merged

    def chunk_text(
        self,
        text: str,
        min_size: int = 300,
        max_size: int = 800,
        target_size: int = 600,
        overlap: int = 80,
        similarity_threshold: float = 0.7,
        coherence_threshold: float = 0.7,
        preserve_entities: bool = True,
        doc_id: str = None,
        metadata: dict[str, Any] = None,
    ) -> list[Chunk]:
        """
        Chunk text with semantic awareness

        Args:
            text: Input text to chunk
            min_size: Minimum chunk size (words)
            max_size: Maximum chunk size (words)
            target_size: Target chunk size (words)
            overlap: Overlap size (words)
            similarity_threshold: Threshold for semantic boundary detection
            coherence_threshold: Minimum coherence score
            preserve_entities: Whether to preserve entity boundaries
            doc_id: Document ID for chunk IDs
            metadata: Additional metadata

        Returns:
            List of Chunk objects
        """
        # Normalize text
        text = normalize_fa(text)

        # Tokenize into sentences
        sentences = sent_tokenize_simple(text)
        if not sentences:
            log.warning("No sentences found in text")
            return []

        log.info(f"Processing {len(sentences)} sentences")

        # Compute sentence embeddings
        embeddings = self._compute_embeddings(sentences)

        # Extract entities if needed
        entities_global = {}
        entity_positions = []
        if preserve_entities:
            entities_global = self._extract_entities(text)
            entity_positions = self._find_entity_positions(text, entities_global)
            log.info(f"Found {len(entity_positions)} entity regions")

        # Compute similarity matrix
        similarity_matrix = self._compute_similarity_matrix(embeddings)

        # Find semantic boundaries
        boundaries = self._find_semantic_boundaries(
            sentences,
            similarity_matrix,
            similarity_threshold,
            min_size,
            max_size,
            target_size,
        )

        # Adjust boundaries to preserve entities
        if preserve_entities and entity_positions:
            boundaries = self._adjust_boundaries_for_entities(text, sentences, boundaries, entity_positions)

        # Create chunks
        chunks = []
        for i, (start_idx, end_idx) in enumerate(boundaries):
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = " ".join(chunk_sentences)

            # Compute chunk embedding (mean of sentence embeddings)
            chunk_embedding = embeddings[start_idx:end_idx].mean(axis=0)

            # Extract entities for this chunk
            chunk_entities = self._extract_entities(chunk_text)

            # Compute coherence score
            coherence = self._compute_coherence(embeddings[start_idx:end_idx])

            # Compute semantic density
            density = self._compute_semantic_density(embeddings[start_idx:end_idx])

            # Create chunk ID
            chunk_id = f"{doc_id or 'doc'}-chunk-{i}"

            # Create Chunk object
            chunk = Chunk(
                id=chunk_id,
                text=chunk_text,
                embedding=chunk_embedding,
                entities=chunk_entities,
                metadata=metadata or {},
                coherence_score=coherence,
                entity_count=sum(len(v) for v in chunk_entities.values()),
                semantic_density=density,
                start_idx=start_idx,
                end_idx=end_idx,
            )

            chunks.append(chunk)

        log.info(f"Created {len(chunks)} chunks")
        log.info(f"Avg coherence: {np.mean([c.coherence_score for c in chunks]):.3f}")

        return chunks

    def _find_semantic_boundaries(
        self,
        sentences: list[str],
        similarity_matrix: np.ndarray,
        threshold: float,
        min_size: int,
        max_size: int,
        target_size: int,
    ) -> list[tuple[int, int]]:
        """
        Find semantic boundaries based on similarity drops

        Algorithm:
        1. Compute similarity between consecutive sentences
        2. Find drops in similarity (potential boundaries)
        3. Apply size constraints (min/max/target)
        4. Adjust dynamically based on semantic density

        Args:
            sentences: List of sentences
            similarity_matrix: Pairwise similarity matrix
            threshold: Similarity threshold for boundary detection
            min_size: Minimum chunk size (words)
            max_size: Maximum chunk size (words)
            target_size: Target chunk size (words)

        Returns:
            List of (start_idx, end_idx) boundaries
        """
        n = len(sentences)
        if n == 0:
            return []
        if n == 1:
            return [(0, 1)]

        # Compute consecutive similarities
        consecutive_sims = np.array([similarity_matrix[i, i + 1] for i in range(n - 1)])

        # Find similarity drops (potential boundaries)
        # A drop is where similarity decreases significantly
        mean_sim = consecutive_sims.mean()
        std_sim = consecutive_sims.std()

        # Boundary candidates: where similarity < mean - 0.5*std
        boundary_threshold = mean_sim - 0.5 * std_sim
        potential_boundaries = []
        for i in range(len(consecutive_sims)):
            if consecutive_sims[i] < boundary_threshold:
                potential_boundaries.append(i + 1)  # boundary after sentence i

        # Add start and end
        potential_boundaries = [0] + potential_boundaries + [n]
        potential_boundaries = sorted(set(potential_boundaries))

        # Apply size constraints
        boundaries = []
        start = 0
        current_size = 0

        for i in range(len(sentences)):
            sent_words = len(sentences[i].split())
            current_size += sent_words

            # Check if we should create a boundary here
            is_potential_boundary = (i + 1) in potential_boundaries
            exceeds_target = current_size >= target_size
            exceeds_max = current_size >= max_size
            is_last = i == n - 1

            # Decision logic
            should_break = False

            if exceeds_max:
                # Must break if exceeds max
                should_break = True
            elif is_last:
                # Must include last sentence
                should_break = True
            elif exceeds_target and is_potential_boundary:
                # Break at semantic boundary if near target
                should_break = True
            elif current_size >= target_size * 1.5:
                # Force break if significantly over target
                should_break = True

            if should_break:
                # Check minimum size constraint
                if current_size >= min_size or is_last:
                    boundaries.append((start, i + 1))
                    start = i + 1
                    current_size = 0
                # else: continue accumulating to meet min_size

        # Handle edge case: if no boundaries created, create one
        if not boundaries:
            boundaries = [(0, n)]

        return boundaries

    def _adjust_boundaries_for_entities(
        self,
        text: str,
        sentences: list[str],
        boundaries: list[tuple[int, int]],
        entity_positions: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """
        Adjust chunk boundaries to avoid splitting entities

        Algorithm:
        1. Convert sentence boundaries to character positions
        2. Check if any entity is split by a boundary
        3. Adjust boundary to include the entire entity
        4. Ensure size constraints are still respected

        Args:
            text: Full text
            sentences: List of sentences
            boundaries: Current chunk boundaries (sentence indices)
            entity_positions: List of (start, end) character positions of entities

        Returns:
            Adjusted boundaries
        """
        if not entity_positions:
            return boundaries

        # Build sentence position map (sentence_idx -> char_start, char_end)
        sentence_positions = []
        char_pos = 0
        for sent in sentences:
            start = text.find(sent, char_pos)
            if start == -1:
                # Fallback: approximate position
                start = char_pos
            end = start + len(sent)
            sentence_positions.append((start, end))
            char_pos = end

        # Convert boundaries to character positions
        adjusted_boundaries = []

        for start_idx, end_idx in boundaries:
            # Get character range for this chunk
            # chunk_start_char = sentence_positions[start_idx][0]
            chunk_end_char = sentence_positions[end_idx - 1][1]

            # Check if any entity is split by this boundary
            # needs_adjustment = False

            for ent_start, ent_end in entity_positions:
                # Check if entity spans the boundary
                if ent_start < chunk_end_char < ent_end:
                    # Entity is split! Need to adjust

                    # Extend chunk to include entire entity
                    # Find which sentence contains the entity end
                    for sent_idx in range(end_idx, len(sentences)):
                        sent_end_char = sentence_positions[sent_idx][1]
                        if sent_end_char >= ent_end:
                            # Extend to this sentence
                            end_idx = sent_idx + 1
                            chunk_end_char = sent_end_char
                            break

            adjusted_boundaries.append((start_idx, end_idx))

        # Merge overlapping boundaries (if adjustment caused overlap)
        merged_boundaries = []
        for start, end in adjusted_boundaries:
            if merged_boundaries and start < merged_boundaries[-1][1]:
                # Overlap: merge with previous
                merged_boundaries[-1] = (
                    merged_boundaries[-1][0],
                    max(merged_boundaries[-1][1], end),
                )
            else:
                merged_boundaries.append((start, end))

        return merged_boundaries

    def _compute_coherence(self, embeddings: np.ndarray) -> float:
        """
        Compute internal coherence of chunk

        Args:
            embeddings: Sentence embeddings in chunk

        Returns:
            Coherence score (0-1)
        """
        if len(embeddings) < 2:
            return 1.0

        # Compute pairwise similarities
        similarity_matrix = self._compute_similarity_matrix(embeddings)

        # Average similarity (excluding diagonal)
        n = len(embeddings)
        coherence = (similarity_matrix.sum() - n) / (n * (n - 1))

        return float(coherence)

    def _compute_semantic_density(self, embeddings: np.ndarray) -> float:
        """
        Compute semantic density (information richness)

        Args:
            embeddings: Sentence embeddings

        Returns:
            Density score
        """
        if len(embeddings) < 2:
            return 0.5

        # Use variance of embeddings as proxy for density
        variance = np.var(embeddings, axis=0).mean()

        # Normalize to 0-1 range (heuristic)
        density = min(1.0, variance * 10)

        return float(density)


# Task 2.1 Complete: Chunk data model with serialization/deserialization
