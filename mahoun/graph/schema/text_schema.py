"""
Text Document Schema - L1 (TextDocument)
=========================================
Canonical Pydantic model for text-level document representation.

This schema represents the L1 layer: raw/normalized text with minimal metadata
for RAG indexing, search, and retrieval operations.

Aligns with mahoun_schema_v1.json but simplified for ingestion pipeline use.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class TextDocument(BaseModel):
    """
    Text-level document representation for RAG/indexing.
    
    This is the L1 schema used for:
    - Vector store indexing
    - Full-text search
    - Document retrieval
    - RAG context formation
    
    Usage:
        >>> doc = TextDocument(
        ...     document_id="verdict_001",
        ...     document_type="verdict",
        ...     full_text="رأی دادگاه...",
        ...     clean_text="رای دادگاه...",
        ...     court="دادگاه تجدیدنظر تهران",
        ...     date_issued="1403-08-15"
        ... )
    """
    document_id: str = Field(..., description="Unique document identifier")
    document_type: str = Field(default="verdict", description="Document type (verdict, law, etc.)")
    
    title: Optional[str] = Field(None, description="Document title or case number")
    full_text: str = Field(..., description="Complete raw text of document")
    clean_text: Optional[str] = Field(None, description="Normalized/cleaned text")
    
    date_issued: Optional[str] = Field(None, description="Date issued (ISO format YYYY-MM-DD)")
    court: Optional[str] = Field(None, description="Court name or issuing authority")
    
    source_file_path: Optional[str] = Field(None, description="Original source file path")
    ingestion_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when document was ingested"
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "document_id": "verdict_2024_001",
                "document_type": "verdict",
                "title": "پرونده 9809980998000001",
                "full_text": "رأی دادگاه تجدیدنظر استان تهران...",
                "clean_text": "رای دادگاه تجدیدنظر استان تهران...",
                "date_issued": "1403-08-15",
                "court": "دادگاه تجدیدنظر استان تهران شعبه 10",
                "source_file_path": "/data/verdicts/verdict_001.txt",
                "ingestion_timestamp": "2024-11-30T16:15:00Z"
            }
        }
    )
