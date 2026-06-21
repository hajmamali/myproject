"""
Advanced Data Ingestion Orchestrator
====================================

Enterprise-grade data ingestion with:
- Multi-source support (PDF, DOCX, JSON, TXT, XML)
- Parallel processing
- Error recovery and retry
- Quality validation
- Progress tracking
- Incremental updates
- Data versioning
"""


import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime


class DataSource(str, Enum):
    """Supported data sources"""
    PDF = "pdf"
    DOCX = "docx"
    JSON = "json"
    TXT = "txt"
    XML = "xml"
    DATABASE = "database"
    API = "api"


class IngestionStage(str, Enum):
    """Ingestion pipeline stages"""
    DISCOVERY = "discovery"
    VALIDATION = "validation"
    PARSING = "parsing"
    EXTRACTION = "extraction"
    TRANSFORMATION = "transformation"
    ENRICHMENT = "enrichment"
    STORAGE = "storage"
    INDEXING = "indexing"


class IngestionStatus(str, Enum):
    """Status of ingestion"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"


@dataclass
class DataFile:
    """Metadata for a data file"""
    file_path: Path
    source_type: DataSource
    file_hash: str
    file_size: int
    created_at: datetime
    modified_at: datetime
    status: IngestionStatus = IngestionStatus.PENDING
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_path(cls, path: Path) -> 'DataFile':
        """Create DataFile from path"""
        stat = path.stat()
        
        # Compute file hash
        with open(path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Determine source type
        suffix = path.suffix.lower()
        source_map = {
            '.pdf': DataSource.PDF,
            '.docx': DataSource.DOCX,
            '.doc': DataSource.DOCX,
            '.json': DataSource.JSON,
            '.jsonl': DataSource.JSON,
            '.txt': DataSource.TXT,
            '.xml': DataSource.XML,
        }
        source_type = source_map.get(suffix, DataSource.TXT)
        
        return cls(
            file_path=path,
            source_type=source_type,
            file_hash=file_hash,
            file_size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )


@dataclass
class IngestionResult:
    """Result of ingestion process"""
    file: DataFile
    stage: IngestionStage
    status: IngestionStatus
    duration_ms: float
    records_processed: int = 0
    records_success: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionConfig:
    """Configuration for data ingestion"""
    # Paths
    input_dir: Path = Path("data/input")
    output_dir: Path = Path("data/processed")
    failed_dir: Path = Path("data/failed")
    
    # Processing
    enable_parallel: bool = True
    max_workers: int = 4
    batch_size: int = 100
    
    # Retry
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    
    # Validation
    enable_validation: bool = True
    min_file_size: int = 100  # bytes
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # Deduplication
    enable_deduplication: bool = True
    dedup_by_hash: bool = True
    dedup_by_content: bool = False
    
    # Incremental
    enable_incremental: bool = True
    track_processed_files: bool = True
    
    # Quality
    min_quality_score: float = 0.5
    enable_quality_check: bool = True



class DataIngestionOrchestrator:
    """
    Advanced Data Ingestion Orchestrator
    
    Features:
    - Multi-source support
    - Parallel processing with worker pools
    - Automatic retry with exponential backoff
    - Deduplication (hash-based and content-based)
    - Incremental updates
    - Quality validation
    - Progress tracking
    - Error recovery
    - Comprehensive logging
    """
    
    def __init__(self, config: Optional[IngestionConfig] = None):
        """Initialize orchestrator"""
        self.config = config or IngestionConfig()
        
        # Create directories
        self.config.input_dir.mkdir(parents=True, exist_ok=True)
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.config.failed_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.processed_files: Dict[str, DataFile] = {}
        self.processed_hashes: set = set()
        self.results: List[IngestionResult] = []
        
        # Load processed files history
        if self.config.track_processed_files:
            self._load_processed_history()
        
        # Parsers registry
        self.parsers: Dict[DataSource, Callable] = {}
        self._register_default_parsers()
        
        # Validators registry
        self.validators: List[Callable] = []
        self._register_default_validators()
        
        # Statistics
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total_records": 0,
        }
        
        logger.info(f"DataIngestionOrchestrator initialized: {self.config.input_dir}")
    
    def register_parser(self, source_type: DataSource, parser: Callable):
        """Register custom parser for a source type"""
        self.parsers[source_type] = parser
        logger.info(f"Registered parser for {source_type.value}")
    
    def register_validator(self, validator: Callable):
        """Register custom validator"""
        self.validators.append(validator)
        logger.info(f"Registered validator: {validator.__name__}")
    
    async def ingest_directory(
        self,
        directory: Optional[Path] = None,
        recursive: bool = True,
        file_pattern: str = "*",
    ) -> List[IngestionResult]:
        """
        Ingest all files from directory
        
        Args:
            directory: Directory to scan (default: config.input_dir)
            recursive: Scan subdirectories
            file_pattern: File pattern to match
            
        Returns:
            List of ingestion results
        """
        directory = directory or self.config.input_dir
        logger.info(f"Starting directory ingestion: {directory}")
        
        # Stage 1: Discovery
        files = await self._discover_files(directory, recursive, file_pattern)
        logger.info(f"Discovered {len(files)} files")
        
        if not files:
            logger.warning("No files found to ingest")
            return []
        
        self.stats["total_files"] = len(files)
        
        # Stage 2: Filter already processed (if incremental)
        if self.config.enable_incremental:
            files = self._filter_processed_files(files)
            logger.info(f"After incremental filter: {len(files)} files")
        
        # Stage 3: Deduplicate
        if self.config.enable_deduplication:
            files = self._deduplicate_files(files)
            logger.info(f"After deduplication: {len(files)} files")
        
        # Stage 4: Process files
        if self.config.enable_parallel:
            results = await self._process_files_parallel(files)
        else:
            results = await self._process_files_sequential(files)
        
        # Stage 5: Save results
        self._save_results(results)
        
        # Update statistics
        self._update_statistics(results)
        
        logger.info(f"Ingestion complete: {self.stats}")
        
        return results
    
    async def ingest_file(self, file_path: Path) -> IngestionResult:
        """Ingest single file"""
        data_file = DataFile.from_path(file_path)
        return await self._process_single_file(data_file)
    
    async def _discover_files(
        self,
        directory: Path,
        recursive: bool,
        pattern: str
    ) -> List[DataFile]:
        """Discover files in directory"""
        files = []
        
        if recursive:
            paths = directory.rglob(pattern)
        else:
            paths = directory.glob(pattern)
        
        for path in paths:
            if not path.is_file():
                continue
            
            # Check file size
            if path.stat().st_size < self.config.min_file_size:
                logger.warning(f"File too small, skipping: {path}")
                continue
            
            if path.stat().st_size > self.config.max_file_size:
                logger.warning(f"File too large, skipping: {path}")
                continue
            
            try:
                data_file = DataFile.from_path(path)
                files.append(data_file)
            except Exception as e:
                logger.error(f"Error creating DataFile for {path}: {e}")
        
        return files
    
    def _filter_processed_files(self, files: List[DataFile]) -> List[DataFile]:
        """Filter out already processed files"""
        filtered = []
        
        for file in files:
            # Check by hash
            if file.file_hash in self.processed_hashes:
                logger.debug(f"File already processed (hash): {file.file_path}")
                file.status = IngestionStatus.SKIPPED
                self.stats["skipped"] += 1
                continue
            
            # Check by path
            if str(file.file_path) in self.processed_files:
                prev_file = self.processed_files[str(file.file_path)]
                # Check if modified
                if file.modified_at <= prev_file.modified_at:
                    logger.debug(f"File not modified: {file.file_path}")
                    file.status = IngestionStatus.SKIPPED
                    self.stats["skipped"] += 1
                    continue
            
            filtered.append(file)
        
        return filtered
    
    def _deduplicate_files(self, files: List[DataFile]) -> List[DataFile]:
        """Remove duplicate files"""
        seen_hashes = set()
        unique_files = []
        
        for file in files:
            if file.file_hash in seen_hashes:
                logger.debug(f"Duplicate file: {file.file_path}")
                file.status = IngestionStatus.SKIPPED
                self.stats["skipped"] += 1
                continue
            
            seen_hashes.add(file.file_hash)
            unique_files.append(file)
        
        return unique_files

    
    async def _process_files_parallel(
        self,
        files: List[DataFile]
    ) -> List[IngestionResult]:
        """Process files in parallel"""
        logger.info(f"Processing {len(files)} files in parallel (workers={self.config.max_workers})")
        
        results = []
        
        # Process in batches
        for i in range(0, len(files), self.config.batch_size):
            batch = files[i:i + self.config.batch_size]
            logger.info(f"Processing batch {i//self.config.batch_size + 1}")
            
            # Create tasks
            tasks = [self._process_single_file(file) for file in batch]
            
            # Execute in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
                else:
                    results.append(result)
        
        return results
    
    async def _process_files_sequential(
        self,
        files: List[DataFile]
    ) -> List[IngestionResult]:
        """Process files sequentially"""
        logger.info(f"Processing {len(files)} files sequentially")
        
        results = []
        for i, file in enumerate(files, 1):
            logger.info(f"Processing file {i}/{len(files)}: {file.file_path}")
            result = await self._process_single_file(file)
            results.append(result)
        
        return results
    
    async def _process_single_file(self, file: DataFile) -> IngestionResult:
        """Process single file through all stages"""
        start_time = time.time()
        
        try:
            # Stage 1: Validation
            if self.config.enable_validation:
                validation_result = await self._validate_file(file)
                if not validation_result["valid"]:
                    return IngestionResult(
                        file=file,
                        stage=IngestionStage.VALIDATION,
                        status=IngestionStatus.FAILED,
                        duration_ms=(time.time() - start_time) * 1000,
                        errors=validation_result["errors"],
                    )
            
            # Stage 2: Parsing
            parsed_data = await self._parse_file(file)
            
            # Stage 3: Extraction
            extracted_data = await self._extract_data(file, parsed_data)
            
            # Stage 4: Transformation
            transformed_data = await self._transform_data(file, extracted_data)
            
            # Stage 5: Enrichment
            enriched_data = await self._enrich_data(file, transformed_data)
            
            # Stage 6: Quality Check
            if self.config.enable_quality_check:
                quality_score = await self._check_quality(file, enriched_data)
                if quality_score < self.config.min_quality_score:
                    return IngestionResult(
                        file=file,
                        stage=IngestionStage.ENRICHMENT,
                        status=IngestionStatus.FAILED,
                        duration_ms=(time.time() - start_time) * 1000,
                        errors=[f"Quality score too low: {quality_score:.2f}"],
                        metadata={"quality_score": quality_score},
                    )
            
            # Stage 7: Storage
            storage_result = await self._store_data(file, enriched_data)
            
            # Stage 8: Indexing
            index_result = await self._index_data(file, enriched_data)
            
            # Success
            file.status = IngestionStatus.SUCCESS
            self.processed_files[str(file.file_path)] = file
            self.processed_hashes.add(file.file_hash)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return IngestionResult(
                file=file,
                stage=IngestionStage.INDEXING,
                status=IngestionStatus.SUCCESS,
                duration_ms=duration_ms,
                records_processed=len(enriched_data),
                records_success=len(enriched_data),
                metadata={
                    "storage": storage_result,
                    "indexing": index_result,
                },
            )
            
        except Exception as e:
            logger.error(f"Error processing {file.file_path}: {e}")
            
            # Retry logic
            if file.retry_count < self.config.max_retries:
                file.retry_count += 1
                file.status = IngestionStatus.RETRY
                logger.info(f"Retrying {file.file_path} (attempt {file.retry_count})")
                
                # Exponential backoff
                await asyncio.sleep(self.config.retry_delay_seconds * (2 ** file.retry_count))
                
                return await self._process_single_file(file)
            
            # Failed after retries
            file.status = IngestionStatus.FAILED
            file.error_message = str(e)
            
            # Move to failed directory
            self._move_to_failed(file)
            
            return IngestionResult(
                file=file,
                stage=IngestionStage.PARSING,
                status=IngestionStatus.FAILED,
                duration_ms=(time.time() - start_time) * 1000,
                errors=[str(e)],
            )
    
    async def _validate_file(self, file: DataFile) -> Dict[str, Any]:
        """Validate file"""
        errors = []
        
        # Run all validators
        for validator in self.validators:
            try:
                result = validator(file)
                if not result["valid"]:
                    errors.extend(result.get("errors", []))
            except Exception as e:
                errors.append(f"Validator error: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
    
    async def _parse_file(self, file: DataFile) -> Any:
        """Parse file based on source type"""
        parser = self.parsers.get(file.source_type)
        
        if not parser:
            raise ValueError(f"No parser registered for {file.source_type}")
        
        return parser(file.file_path)
    
    async def _extract_data(self, file: DataFile, parsed_data: Any) -> List[Dict]:
        """Extract structured data from parsed content.
        
        GOVERNANCE: Must be implemented to route through canonical pipeline.
        Placeholder no-ops are FORBIDDEN in production.
        """
        raise NotImplementedError(
            "_extract_data must be implemented to route through "
            "mahoun.pipelines.ingestion.minimal_verdict_parser. "
            "Placeholder no-op ingestion is forbidden."
        )
    
    async def _transform_data(self, file: DataFile, data: List[Dict]) -> List[Dict]:
        """Transform data to standard format.
        
        GOVERNANCE: Must be implemented to route through canonical schema_builder.
        """
        raise NotImplementedError(
            "_transform_data must be implemented to route through "
            "mahoun.pipelines.ingestion.schema_builder. "
            "Placeholder no-op transformation is forbidden."
        )
    
    async def _enrich_data(self, file: DataFile, data: List[Dict]) -> List[Dict]:
        """Enrich data with additional information.
        
        GOVERNANCE: Must be implemented or disabled.
        """
        raise NotImplementedError(
            "_enrich_data must be implemented. "
            "Placeholder no-op enrichment is forbidden."
        )
    
    async def _check_quality(self, file: DataFile, data: List[Dict]) -> float:
        """Check data quality.
        
        GOVERNANCE: Must be implemented with real quality metrics.
        """
        raise NotImplementedError(
            "_check_quality must be implemented with real quality metrics. "
            "Returning hardcoded 1.0 is forbidden."
        )
    
    async def _store_data(self, file: DataFile, data: List[Dict]) -> Dict:
        """Store data to databases.
        
        GOVERNANCE: Must route through GovernedNeo4jSession.
        Direct database writes are FORBIDDEN.
        """
        raise NotImplementedError(
            "_store_data must be implemented to route through GovernedNeo4jSession. "
            "Direct database access is forbidden."
        )
    
    async def _index_data(self, file: DataFile, data: List[Dict]) -> Dict:
        """Index data for search.
        
        GOVERNANCE: Must be implemented with real indexing.
        """
        raise NotImplementedError(
            "_index_data must be implemented. "
            "Placeholder no-op indexing is forbidden."
        )
    
    def _register_default_parsers(self):
        """Register default parsers"""
        # Placeholder - register parsers
        pass
    
    def _register_default_validators(self):
        """Register default validators"""
        def file_exists_validator(file: DataFile) -> Dict:
            return {
                "valid": file.file_path.exists(),
                "errors": [] if file.file_path.exists() else ["File not found"],
            }
        
        self.validators.append(file_exists_validator)
    
    def _load_processed_history(self):
        """Load history of processed files"""
        history_file = self.config.output_dir / ".processed_history.json"
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    
                for file_data in data.get("files", []):
                    file_path = file_data["file_path"]
                    self.processed_hashes.add(file_data["file_hash"])
                    # Reconstruct DataFile (simplified)
                    
                logger.info(f"Loaded {len(self.processed_hashes)} processed files from history")
            except Exception as e:
                logger.error(f"Error loading processed history: {e}")
    
    def _save_results(self, results: List[IngestionResult]):
        """Save ingestion results"""
        results_file = self.config.output_dir / f"ingestion_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "input_dir": str(self.config.input_dir),
                    "output_dir": str(self.config.output_dir),
                },
                "statistics": self.stats,
                "results": [
                    {
                        "file_path": str(r.file.file_path),
                        "status": r.status.value,
                        "stage": r.stage.value,
                        "duration_ms": r.duration_ms,
                        "records_processed": r.records_processed,
                        "errors": r.errors,
                    }
                    for r in results
                ],
            }
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {results_file}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def _update_statistics(self, results: List[IngestionResult]):
        """Update statistics"""
        for result in results:
            self.stats["processed"] += 1
            
            if result.status == IngestionStatus.SUCCESS:
                self.stats["success"] += 1
                self.stats["total_records"] += result.records_processed
            elif result.status == IngestionStatus.FAILED:
                self.stats["failed"] += 1
    
    def _move_to_failed(self, file: DataFile):
        """Move failed file to failed directory"""
        try:
            failed_path = self.config.failed_dir / file.file_path.name
            file.file_path.rename(failed_path)
            logger.info(f"Moved failed file to {failed_path}")
        except Exception as e:
            logger.error(f"Error moving failed file: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        return self.stats.copy()
