"""
Advanced Data Ingestion Pipeline
=================================

Enterprise-grade data ingestion with parsers, validators, and orchestration
"""

from pipelines.ingestion.data_orchestrator import (
    DataIngestionOrchestrator,
    IngestionConfig,
    DataFile,
    IngestionResult,
    DataSource,
    IngestionStage,
    IngestionStatus,
)

from pipelines.ingestion.parsers import (
    ParserFactory,
    BaseParser,
    PDFParser,
    DOCXParser,
    JSONParser,
    TXTParser,
    XMLParser,
    LegalDocumentParser,
    ParseResult,
)

from pipelines.ingestion.validators import (
    ValidatorChain,
    BaseValidator,
    FileValidator,
    SchemaValidator,
    ContentValidator,
    LegalDocumentValidator,
    QualityValidator,
    SecurityValidator,
    ValidationResult,
)

__all__ = [
    # Orchestrator
    "DataIngestionOrchestrator",
    "IngestionConfig",
    "DataFile",
    "IngestionResult",
    "DataSource",
    "IngestionStage",
    "IngestionStatus",
    
    # Parsers
    "ParserFactory",
    "BaseParser",
    "PDFParser",
    "DOCXParser",
    "JSONParser",
    "TXTParser",
    "XMLParser",
    "LegalDocumentParser",
    "ParseResult",
    
    # Validators
    "ValidatorChain",
    "BaseValidator",
    "FileValidator",
    "SchemaValidator",
    "ContentValidator",
    "LegalDocumentValidator",
    "QualityValidator",
    "SecurityValidator",
    "ValidationResult",
]

__version__ = "2.0.0"
__author__ = "MAHOUN Team"
