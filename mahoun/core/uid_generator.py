"""
UUID Generator for MAHOUN Legal Ecosystem
==========================================
Standardized, collision-resistant UUID generation for legal entities.
Provides deterministic ID generation (UUID v5) to ensure consistent
identities across different ingestion batches.
"""

import uuid
from typing import Optional, Union


class UIDGenerator:
    """Standardized deterministic UUID generator for legal entities"""

    @staticmethod
    def generate_deterministic(namespace_str: str, name: str) -> str:
        """
        Generate a deterministic UUID (v5) based on namespace and name.
        This ensures the same legal entity always gets the same ID.

        Args:
            namespace_str: String identifier for the specific namespace/category
            name: The unique name or identifier of the entity

        Returns:
            String representation of the UUID
        """
        unique_string = f"{namespace_str}:{name}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

    @staticmethod
    def generate_entity_id(entity_type: str, entity_value: str) -> str:
        """
        Helper method specifically for legal entities

        Args:
            entity_type: Type of entity (e.g., 'person', 'organization', 'law')
            entity_value: The canonical value/name of the entity

        Returns:
            Deterministic UUID string
        """
        return UIDGenerator.generate_deterministic(
            entity_type.upper(), str(entity_value)
        )

    @staticmethod
    def generate_document_id(doc_hash: str) -> str:
        """
        Generate a document ID from its hash
        """
        return UIDGenerator.generate_deterministic("DOCUMENT", str(doc_hash))


# Expose functions directly for convenience
generate_deterministic = UIDGenerator.generate_deterministic
generate_entity_id = UIDGenerator.generate_entity_id
generate_document_id = UIDGenerator.generate_document_id
