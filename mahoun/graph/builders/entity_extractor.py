"""
Entity Extractor for Legal Knowledge Graph
==========================================

This module extracts entities from legal documents using a hybrid approach:
- Persian Legal NLP for legal term patterns
- NER model for named entities
- Regex patterns for structured information
"""

import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

# Import persian_legal_nlp (fixed import path)
from mahoun.nlp.persian_legal_nlp import (
    normalize,
    extract_legal_terms,
    extract_article_numbers,
    extract_case_numbers,
    extract_entities_for_graph,
)

logger = logging.getLogger(__name__)


# Entity types supported (16 types as per requirements)
ENTITY_TYPES = {
    "COURT",
    "PARTY",
    "VERDICT",
    "LAW_NAME",
    "ARTICLE",
    "LOCATION",
    "LAWYER",
    "JUDGE",
    "PROVISION",
    "REMEDY",
    "REQUEST",
    "LEGAL_REASONING",
    "DISPOSITION",
    "CITATION",
    "DATE",
    "CASE_NO",
}


@dataclass
class Entity:
    """
    Entity data class

    Attributes:
        text: Entity text
        label: Entity type/label
        start: Start position in text
        end: End position in text
        score: Confidence score (0-1)
        source: Extraction source (ner, regex, nlp)
        normalized_text: Normalized text for deduplication
        metadata: Additional metadata
    """

    text: str
    label: str
    start: int
    end: int
    score: float = 1.0
    source: str = "unknown"
    normalized_text: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization processing"""
        if self.normalized_text is None:
            self.normalized_text = normalize(self.text).strip().lower()

        # Validate label
        if self.label not in ENTITY_TYPES:
            logger.warning(f"Unknown entity type: {self.label}")

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "text": self.text,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "score": self.score,
            "source": self.source,
            "normalized_text": self.normalized_text,
            "metadata": self.metadata,
        }

    def __hash__(self):
        """Hash for deduplication"""
        return hash((self.normalized_text, self.label))

    def __eq__(self, other):
        """Equality for deduplication"""
        if not isinstance(other, Entity):
            return False
        return (
            self.normalized_text == other.normalized_text and self.label == other.label
        )


class EntityExtractor:
    """
    Entity Extractor for Legal Documents

    Extracts entities using a hybrid approach combining:
    1. Persian Legal NLP patterns
    2. NER model (if available)
    3. Regex patterns

    Supports 16 entity types as per requirements.
    """

    def __init__(self, use_ner: bool = True, min_score: float = 0.7):
        """
        Initialize EntityExtractor

        Args:
            use_ner: Whether to use NER model
            min_score: Minimum confidence score threshold
        """
        self.use_ner = use_ner
        self.min_score = min_score
        self.ner_model = None

        # Load NER model if requested
        if use_ner:
            self._load_ner_model()

        logger.info(
            f"EntityExtractor initialized (use_ner={use_ner}, min_score={min_score})"
        )

    def _load_ner_model(self):
        """Load NER model (lazy loading)"""
        try:
            # Try to load transformers-based NER
            from transformers import pipeline

            self.ner_model = pipeline(
                "ner",
                model="HooshvareLab/bert-base-parsbert-uncased",
                aggregation_strategy="simple",
            )
            logger.info("NER model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load NER model: {e}")
            self.ner_model = None
            self.use_ner = False

    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities from text using hybrid approach

        Combines:
        - Persian Legal NLP patterns
        - NER model (if available)
        - Regex patterns

        Args:
            text: Input text

        Returns:
            List of extracted entities
        """
        if not text or len(text.strip()) < 10:
            return []

        # Normalize text
        normalized_text = normalize(text)

        entities = []

        # 1. Extract using Persian Legal NLP
        nlp_entities = self._extract_with_nlp(normalized_text)
        entities.extend(nlp_entities)

        # 2. Extract using NER model
        if self.use_ner and self.ner_model:
            ner_entities = self._extract_with_ner(normalized_text)
            entities.extend(ner_entities)

        # 3. Extract using regex patterns
        regex_entities = self._extract_with_regex(normalized_text)
        entities.extend(regex_entities)

        # 4. Normalize and merge duplicates
        entities = self.merge_duplicates(entities)

        # 5. Filter by score threshold
        entities = [e for e in entities if e.score >= self.min_score]

        # 6. Sort by position
        entities.sort(key=lambda e: e.start)

        logger.debug(f"Extracted {len(entities)} entities from text")

        return entities

    def _extract_with_nlp(self, text: str) -> List[Entity]:
        """Extract entities using Persian Legal NLP"""
        entities = []

        # Map Persian legal term categories to entity types
        category_to_label = {
            "ماده": "ARTICLE",
            "تبصره": "ARTICLE",
            "بند": "PROVISION",
            "قانون": "LAW_NAME",
            "حکم": "VERDICT",
            "رأی": "VERDICT",
            "قرار": "VERDICT",
            "دادگاه": "COURT",
            "دادسرا": "COURT",
            "دیوان": "COURT",
            "شورا": "COURT",
            "جرم": "LEGAL_REASONING",
            "مجازات": "REMEDY",
            "حبس": "REMEDY",
            "جزای_نقدی": "REMEDY",
            "طرفین": "PARTY",
            "وکیل": "LAWYER",
            "قاضی": "JUDGE",
            "پرونده": "CASE_NO",
            "شعبه": "COURT",
            "دادنامه": "VERDICT",
            "سند": "CITATION",
            "حق": "LEGAL_REASONING",
            "دعوا": "REQUEST",
            "اعتراض": "REQUEST",
            "مهلت": "PROVISION",
            "اجرا": "REMEDY",
            "خسارت": "REMEDY",
            "مهریه": "REMEDY",
            "نفقه": "REMEDY",
            "طلاق": "DISPOSITION",
            "ارث": "LEGAL_REASONING",
            "رسیدگی": "LEGAL_REASONING",
            "ابطال": "REMEDY",
        }

        try:
            # Use extract_entities_for_graph from persian_legal_nlp
            nlp_results = extract_entities_for_graph(text)

            for ent in nlp_results:
                category = ent.get("category", "")
                label = category_to_label.get(category, ent.get("label", "LEGAL_TERM"))

                # Skip if not a valid entity type
                if label not in ENTITY_TYPES:
                    continue

                entity = Entity(
                    text=ent.get("text", ""),
                    label=label,
                    start=ent.get("start", 0),
                    end=ent.get("end", 0),
                    score=ent.get("confidence", 1.0),
                    source="persian_legal_nlp",
                    metadata={"category": category},
                )
                entities.append(entity)

        except Exception as e:
            logger.warning(f"Persian Legal NLP extraction failed: {e}")

        return entities

    def _extract_with_ner(self, text: str, max_length: int = 4000) -> List[Entity]:
        """Extract entities using NER model"""
        entities = []

        if not self.ner_model:
            return entities

        try:
            # Truncate text if too long
            text_chunk = text[:max_length]

            # Run NER
            ner_results = self.ner_model(text_chunk)

            # Map NER labels to our entity types
            label_map = {
                "PER": "PERSON",
                "PERSON": "PERSON",
                "ORG": "ORGANIZATION",
                "LOC": "LOCATION",
                "LOCATION": "LOCATION",
                "LAW": "LAW_NAME",
                "ARTICLE": "ARTICLE",
                "COURT": "COURT",
                "JUDGE": "JUDGE",
                "LAWYER": "LAWYER",
            }

            for ent in ner_results:
                # Get label
                label = ent.get("entity_group") or ent.get("entity", "")
                label = label.split("-")[-1]  # Remove B-/I- prefix
                label = label_map.get(label, label)

                # Skip if not in our entity types
                if label not in ENTITY_TYPES and label not in [
                    "PERSON",
                    "ORGANIZATION",
                ]:
                    continue

                entity = Entity(
                    text=ent.get("word", ""),
                    label=label,
                    start=ent.get("start", 0),
                    end=ent.get("end", 0),
                    score=ent.get("score", 0.8),
                    source="ner_model",
                )
                entities.append(entity)

        except Exception as e:
            logger.warning(f"NER extraction failed: {e}")

        return entities

    def _extract_with_regex(self, text: str) -> List[Entity]:
        """Extract entities using regex patterns"""
        entities = []

        # Pattern for case numbers
        case_pattern = r"\b\d{2,4}/\d{1,6}\b"
        for match in re.finditer(case_pattern, text):
            entity = Entity(
                text=match.group(),
                label="CASE_NO",
                start=match.start(),
                end=match.end(),
                score=0.95,
                source="regex",
            )
            entities.append(entity)

        # Pattern for dates (Persian)
        date_pattern = r"\d{2,4}/\d{1,2}/\d{1,2}"
        for match in re.finditer(date_pattern, text):
            entity = Entity(
                text=match.group(),
                label="DATE",
                start=match.start(),
                end=match.end(),
                score=0.9,
                source="regex",
            )
            entities.append(entity)

        # Pattern for article numbers
        article_pattern = r"ماده\s+\d+"
        for match in re.finditer(article_pattern, text):
            entity = Entity(
                text=match.group(),
                label="ARTICLE",
                start=match.start(),
                end=match.end(),
                score=0.95,
                source="regex",
            )
            entities.append(entity)

        return entities

    def normalize_entity(self, entity: Entity) -> Entity:
        """
        Normalize entity

        - Normalize text
        - Clean whitespace
        - Update normalized_text field

        Args:
            entity: Entity to normalize

        Returns:
            Normalized entity
        """
        # Normalize text
        normalized = normalize(entity.text).strip()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Update entity
        entity.normalized_text = normalized.lower()

        return entity

    def merge_duplicates(self, entities: List[Entity]) -> List[Entity]:
        """
        Merge duplicate entities

        Entities are considered duplicates if they have:
        - Same normalized_text
        - Same label

        When merging, keep the entity with highest score.

        Args:
            entities: List of entities

        Returns:
            List of unique entities
        """
        if not entities:
            return []

        # Normalize all entities first
        entities = [self.normalize_entity(e) for e in entities]

        # Group by (normalized_text, label)
        groups = defaultdict(list)
        for entity in entities:
            key = (entity.normalized_text, entity.label)
            groups[key].append(entity)

        # Keep best entity from each group
        unique_entities = []
        for group in groups.values():
            # Sort by score (descending)
            group.sort(key=lambda e: e.score, reverse=True)
            best_entity = group[0]

            # If multiple sources, combine them
            if len(group) > 1:
                sources = [e.source for e in group]
                best_entity.source = "+".join(sorted(set(sources)))
                best_entity.metadata["duplicate_count"] = len(group)

            unique_entities.append(best_entity)

        logger.debug(
            f"Merged {len(entities)} entities into {len(unique_entities)} unique entities"
        )

        return unique_entities

    def validate_entity(self, entity: Entity) -> bool:
        """
        Validate entity

        Checks:
        - Required properties exist
        - Score threshold (>0.7)
        - Text length (>2 characters)

        Args:
            entity: Entity to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required properties
        if not entity.text or not entity.label:
            return False

        # Check score threshold
        if entity.score < self.min_score:
            return False

        # Check text length
        if len(entity.text.strip()) < 2:
            return False

        # Check label is valid
        if entity.label not in ENTITY_TYPES and entity.label not in [
            "PERSON",
            "ORGANIZATION",
        ]:
            return False

        return True

    def filter_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Filter entities by validation rules

        Args:
            entities: List of entities

        Returns:
            List of valid entities
        """
        return [e for e in entities if self.validate_entity(e)]

    def extract_and_validate(self, text: str) -> List[Entity]:
        """
        Extract and validate entities

        Convenience method that combines extraction and validation.

        Args:
            text: Input text

        Returns:
            List of valid entities
        """
        entities = self.extract_entities(text)
        entities = self.filter_entities(entities)
        return entities

    def get_entity_statistics(self, entities: List[Entity]) -> Dict:
        """
        Get statistics about extracted entities

        Args:
            entities: List of entities

        Returns:
            Dictionary with statistics
        """
        if not entities:
            return {"total": 0, "by_label": {}, "by_source": {}, "avg_score": 0.0}

        # Count by label
        by_label = defaultdict(int)
        for entity in entities:
            by_label[entity.label] += 1

        # Count by source
        by_source = defaultdict(int)
        for entity in entities:
            by_source[entity.source] += 1

        # Average score
        avg_score = sum(e.score for e in entities) / len(entities)

        return {
            "total": len(entities),
            "by_label": dict(by_label),
            "by_source": dict(by_source),
            "avg_score": avg_score,
            "unique_labels": len(by_label),
            "unique_sources": len(by_source),
        }


# Convenience functions
def extract_entities_from_text(
    text: str, use_ner: bool = True, min_score: float = 0.7
) -> List[Entity]:
    """
    Convenience function to extract entities from text

    Args:
        text: Input text
        use_ner: Whether to use NER model
        min_score: Minimum confidence score

    Returns:
        List of entities
    """
    extractor = EntityExtractor(use_ner=use_ner, min_score=min_score)
    return extractor.extract_and_validate(text)


def extract_entities_batch(
    texts: List[str], use_ner: bool = True, min_score: float = 0.7
) -> List[List[Entity]]:
    """
    Extract entities from multiple texts

    Args:
        texts: List of input texts
        use_ner: Whether to use NER model
        min_score: Minimum confidence score

    Returns:
        List of entity lists (one per text)
    """
    extractor = EntityExtractor(use_ner=use_ner, min_score=min_score)
    return [extractor.extract_and_validate(text) for text in texts]
