"""
Relation Extraction using GNNs
==============================
Identifies and classifies relationships between legal entities in documents.

Note: Requires torch for full GNN functionality.
Falls back to rule-based extraction without torch.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)

# Optional torch import
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch: Optional[Any] = None
    nn: Optional[Any] = None
    F: Optional[Any] = None
    logger.info("torch not available - RelationExtractor will use rule-based mode")


# Relation types
RELATION_NAMES = ["REFERENCES", "CITES", "MODIFIES", "IMPLEMENTS", "RELATED_TO"]


class RelationExtractorBase:
    """
    Base Relation Extractor using rule-based extraction.
    Works without torch.
    """

    def __init__(
        self, 
        input_dim: int = 384, 
        hidden_dim: int = 256, 
        num_relations: int = 5
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_relations = num_relations

    def extract_entities(self, text: str) -> List[Tuple[str, str, int, int]]:
        """
        Extract legal entities from text using regex patterns.
        
        Returns:
            List of (value, type, start, end) tuples
        """
        entities: List[Any] = []
        # Legal articles pattern
        article_pattern = r"(ماده|حکم|دادنامه|ر\.?)\s*(\d+)"
        for match in re.finditer(article_pattern, text, re.IGNORECASE):
            entity_value = f"{match.group(1)} {match.group(2)}"
            entities.append((entity_value, "LEGAL_ARTICLE", match.start(), match.end()))

        # Legal entities pattern
        legal_entities_pattern = r"(دادگاه|خواهان|خوانده|وکیل|رئیس شعبه|مستشار)"
        for match in re.finditer(legal_entities_pattern, text, re.IGNORECASE):
            entities.append((match.group(0), "LEGAL_ENTITY", match.start(), match.end()))

        return entities

    def create_entity_dependency_graph(
        self, text: str, entities: List[Tuple[str, str, int, int]]
    ) -> np.ndarray:
        """Create a dependency graph based on entity relationships in text."""
        n_entities = len(entities)
        adj_matrix = np.zeros((n_entities, n_entities), dtype=np.float32)

        sentences = re.split(r"[.!?؟]+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            entity_indices_in_sentence: List[Any] = []
            for i, (entity_val, _, _, _) in enumerate(entities):
                if entity_val in sentence:
                    entity_indices_in_sentence.append(i)

            for i in entity_indices_in_sentence:
                for j in entity_indices_in_sentence:
                    if i != j:
                        adj_matrix[i, j] = 1.0

        return adj_matrix

    def extract_relations(
        self, text: str, entity_embeddings: Optional[np.ndarray] = None
    ) -> List[Dict]:
        """
        Extract relations from text using rule-based approach.
        
        Returns:
            List of relation dictionaries
        """
        entities = self.extract_entities(text)

        if not entities or len(entities) < 2:
            return []

        adj_matrix = self.create_entity_dependency_graph(text, entities)
        
        relations: List[Any] = []
        for i in range(len(entities)):
            for j in range(len(entities)):
                if i != j and adj_matrix[i, j] > 0:
                    # Determine relation type based on entity types
                    relation_name = self._infer_relation_type(entities[i], entities[j])
                    confidence = 0.5  # Default confidence for rule-based
                    
                    relations.append({
                        "entity1": entities[i][0],
                        "entity2": entities[j][0],
                        "relation": relation_name,
                        "confidence": confidence,
                    })

        relations.sort(key=lambda x: x["confidence"], reverse=True)
        return relations

    def _infer_relation_type(
        self, 
        entity1: Tuple[str, str, int, int], 
        entity2: Tuple[str, str, int, int]
    ) -> str:
        """Infer relation type based on entity types"""
        type1, type2 = entity1[1], entity2[1]
        
        if type1 == "LEGAL_ARTICLE" and type2 == "LEGAL_ARTICLE":
            return "REFERENCES"
        elif type1 == "LEGAL_ENTITY" and type2 == "LEGAL_ARTICLE":
            return "CITES"
        else:
            return "RELATED_TO"

    def get_relation_name(self, relation_idx: int) -> str:
        """Get relation name based on index."""
        if relation_idx < len(RELATION_NAMES):
            return RELATION_NAMES[relation_idx]
        return f"RELATION_TYPE_{relation_idx}"


# Full GNN-based extractor (requires torch)
if HAS_TORCH:
    class RelationExtractor(nn.Module):
        """
        Relation extraction component using GNNs to identify and classify
        relationships between legal entities in documents.
        """

        def __init__(
            self, 
            input_dim: int = 384, 
            hidden_dim: int = 256, 
            num_relations: int = 5
        ):
            super(RelationExtractor, self).__init__()

            self.input_dim = input_dim
            self.hidden_dim = hidden_dim
            self.num_relations = num_relations

            self.gnn_layer = nn.Linear(input_dim, hidden_dim)
            self.edge_classifier = nn.Linear(hidden_dim * 2, num_relations)
            self.activation = nn.ReLU()

        def extract_entities(self, text: str) -> List[Tuple[str, str, int, int]]:
            """Extract legal entities from text using regex patterns."""
            entities: List[Any] = []
            article_pattern = r"(ماده|حکم|دادنامه|ر\.?)\s*(\d+)"
            for match in re.finditer(article_pattern, text, re.IGNORECASE):
                entity_value = f"{match.group(1)} {match.group(2)}"
                entities.append((entity_value, "LEGAL_ARTICLE", match.start(), match.end()))

            legal_entities_pattern = r"(دادگاه|خواهان|خوانده|وکیل|رئیس شعبه|مستشار)"
            for match in re.finditer(legal_entities_pattern, text, re.IGNORECASE):
                entities.append((match.group(0), "LEGAL_ENTITY", match.start(), match.end()))

            return entities

        def create_entity_dependency_graph(
            self, text: str, entities: List[Tuple[str, str, int, int]]
        ) -> "torch.Tensor":
            """Create a dependency graph based on entity relationships."""
            n_entities = len(entities)
            adj_matrix = torch.zeros((n_entities, n_entities), dtype=torch.float32)

            sentences = re.split(r"[.!?؟]+", text)

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                entity_indices_in_sentence: List[Any] = []
                for i, (entity_val, _, _, _) in enumerate(entities):
                    if entity_val in sentence:
                        entity_indices_in_sentence.append(i)

                for i in entity_indices_in_sentence:
                    for j in entity_indices_in_sentence:
                        if i != j:
                            adj_matrix[i, j] = 1.0

            return adj_matrix

        def forward(
            self, 
            entity_embeddings: "torch.Tensor", 
            adj_matrix: "torch.Tensor"
        ) -> "torch.Tensor":
            """Forward pass to extract relations."""
            h = self.activation(self.gnn_layer(entity_embeddings))
            num_entities = h.size(0)

            relations: List[Any] = []
            for i in range(num_entities):
                for j in range(num_entities):
                    if i != j:
                        pair_embedding = torch.cat([h[i], h[j]], dim=-1)
                        relation_score = self.edge_classifier(pair_embedding)
                        relations.append(relation_score)

            if relations:
                relations_tensor = torch.stack(relations, dim=0)
                relations_tensor = relations_tensor.view(num_entities, num_entities - 1, -1)
            else:
                relations_tensor = torch.zeros(
                    (num_entities, max(1, num_entities - 1), self.num_relations),
                    dtype=entity_embeddings.dtype,
                    device=entity_embeddings.device,
                )

            return F.softmax(relations_tensor, dim=-1)

        def extract_relations(
            self, text: str, entity_embeddings: np.ndarray
        ) -> List[Dict]:
            """Extract relations from text using GNN."""
            entities = self.extract_entities(text)

            if not entities or len(entities) < 2:
                return []

            entity_embeddings_tensor = torch.tensor(
                entity_embeddings[: len(entities)], dtype=torch.float32
            )

            adj_matrix = self.create_entity_dependency_graph(text, entities)

            with torch.no_grad():
                relation_probs = self.forward(entity_embeddings_tensor, adj_matrix)

            relations: List[Any] = []
            idx = 0
            for i in range(len(entities)):
                for j in range(len(entities)):
                    if i != j:
                        if idx < relation_probs.size(0) * relation_probs.size(1):
                            flat_idx = idx
                            row = flat_idx // (len(entities) - 1)
                            col = flat_idx % (len(entities) - 1)
                            if row < relation_probs.size(0) and col < relation_probs.size(1):
                                relation_scores = relation_probs[row, col]
                                relation_type_idx = torch.argmax(relation_scores).item()
                                confidence = relation_scores[relation_type_idx].item()

                                if confidence > 0.1:
                                    relations.append({
                                        "entity1": entities[i][0],
                                        "entity2": entities[j][0],
                                        "relation": self.get_relation_name(relation_type_idx),
                                        "confidence": confidence,
                                    })
                        idx += 1

            relations.sort(key=lambda x: x["confidence"], reverse=True)
            return relations

        def get_relation_name(self, relation_idx: int) -> str:
            """Get relation name based on index."""
            if relation_idx < len(RELATION_NAMES):
                return RELATION_NAMES[relation_idx]
            return f"RELATION_TYPE_{relation_idx}"

else:
    # Fallback when torch is not available
    RelationExtractor = RelationExtractorBase


def get_relation_extractor(input_dim: int = 384, **kwargs) -> Any:
    """
    Factory function to get the appropriate relation extractor.
    """
    if HAS_TORCH:
        logger.info("Using GNN-based RelationExtractor (torch available)")
        return RelationExtractor(input_dim=input_dim, **kwargs)
    else:
        logger.info("Using rule-based RelationExtractorBase (torch not available)")
        return RelationExtractorBase(input_dim=input_dim, **kwargs)


def test_relation_extractor():
    """Test the relation extractor"""
    legal_text = """
    دادگاه بدوی در خصوص دعوی آقایان به وکالت از آقای ساکن تهران، 
    به طرفیت آقای که بعداً آقای و خانم از جانب خوانده ردیف اول اعلام وکالت نموده 
    به خواسته اثبات عقد هبه خواهان با خوانده ردیف اول در سال 1381
    طبق ماده 123 و ماده 456 قانون مدنی رسیدگی شد.
    """

    extractor = get_relation_extractor(input_dim=384, num_relations=5)
    
    # For rule-based, embeddings are optional
    if HAS_TORCH:
        entities = extractor.extract_entities(legal_text)
        entity_embeddings = np.random.rand(len(entities), 384).astype(np.float32)
        relations = extractor.extract_relations(legal_text, entity_embeddings)
    else:
        relations = extractor.extract_relations(legal_text)

    print(f"Extractor type: {type(extractor).__name__}")
    print(f"torch available: {HAS_TORCH}")
    print("\nExtracted relations:")
    for relation in relations[:5]:
        print(
            f"  {relation['entity1']} --{relation['relation']}--> {relation['entity2']} "
            f"(confidence: {relation['confidence']:.3f})"
        )

    return relations


if __name__ == "__main__":
    test_relation_extractor()
