"""
Example Usage of Data Ingestion System
======================================

Complete example showing how to use the ingestion orchestrator
"""

import asyncio
from pathlib import Path
from loguru import logger

from pipelines.ingestion.data_orchestrator import (
    DataIngestionOrchestrator,
    IngestionConfig,
    DataSource,
)
from pipelines.ingestion.parsers import (
    ParserFactory,
    LegalDocumentParser,
)
from pipelines.ingestion.validators import (
    FileValidator,
    ContentValidator,
    LegalDocumentValidator,
    QualityValidator,
    SecurityValidator,
    ValidatorChain,
)


async def main():
    """Main example"""
    
    # Configure logging
    logger.add("logs/ingestion_{time}.log", rotation="100 MB")
    
    print("=" * 80)
    print("MAHOUN Data Ingestion System - Example Usage")
    print("=" * 80)
    
    # 1. Create configuration
    config = IngestionConfig(
        input_dir=Path("data/raw"),
        output_dir=Path("data/processed"),
        failed_dir=Path("data/failed"),
        enable_parallel=True,
        max_workers=4,
        batch_size=10,
        enable_validation=True,
        enable_deduplication=True,
        enable_incremental=True,
        min_quality_score=0.5,
    )
    
    print(f"\n📁 Input directory: {config.input_dir}")
    print(f"📁 Output directory: {config.output_dir}")
    print(f"⚙️  Parallel processing: {config.enable_parallel}")
    print(f"👷 Max workers: {config.max_workers}")
    
    # 2. Create orchestrator
    orchestrator = DataIngestionOrchestrator(config)
    
    # 3. Register custom parsers
    orchestrator.register_parser(
        DataSource.TXT,
        lambda path: LegalDocumentParser().parse(path)
    )
    
    print("\n✅ Registered custom legal document parser")
    
    # 4. Register validators
    validator_chain = ValidatorChain()
    validator_chain.add_validator(FileValidator(min_size=100, max_size=10*1024*1024))
    validator_chain.add_validator(ContentValidator(min_length=50, required_language='fa'))
    validator_chain.add_validator(LegalDocumentValidator())
    validator_chain.add_validator(QualityValidator(min_quality_score=0.5))
    validator_chain.add_validator(SecurityValidator())
    
    orchestrator.register_validator(
        lambda file: validator_chain.validate(file.file_path)
    )
    
    print("✅ Registered validator chain (5 validators)")
    
    # 5. Run ingestion
    print("\n" + "=" * 80)
    print("Starting Data Ingestion...")
    print("=" * 80 + "\n")
    
    results = await orchestrator.ingest_directory(
        directory=config.input_dir,
        recursive=True,
        file_pattern="*.txt",
    )
    
    # 6. Display results
    print("\n" + "=" * 80)
    print("Ingestion Results")
    print("=" * 80)
    
    stats = orchestrator.get_statistics()
    
    print(f"\n📊 Statistics:")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Processed: {stats['processed']}")
    print(f"   Success: {stats['success']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Skipped: {stats['skipped']}")
    print(f"   Total records: {stats['total_records']}")
    
    if stats['success'] > 0:
        success_rate = (stats['success'] / stats['processed']) * 100 if stats['processed'] > 0 else 0
        print(f"   Success rate: {success_rate:.1f}%")
    
    # 7. Show detailed results
    print(f"\n📋 Detailed Results:")
    
    for i, result in enumerate(results[:10], 1):  # Show first 10
        status_emoji = "✅" if result.status.value == "success" else "❌"
        print(f"\n   {status_emoji} File {i}: {result.file.file_path.name}")
        print(f"      Status: {result.status.value}")
        print(f"      Stage: {result.stage.value}")
        print(f"      Duration: {result.duration_ms:.0f}ms")
        print(f"      Records: {result.records_processed}")
        
        if result.errors:
            print(f"      Errors: {', '.join(result.errors[:2])}")
        
        if result.warnings:
            print(f"      Warnings: {', '.join(result.warnings[:2])}")
    
    if len(results) > 10:
        print(f"\n   ... and {len(results) - 10} more files")
    
    print("\n" + "=" * 80)
    print("✅ Ingestion Complete!")
    print("=" * 80)


async def example_single_file():
    """Example: Process single file"""
    
    print("\n" + "=" * 80)
    print("Example: Single File Processing")
    print("=" * 80)
    
    orchestrator = DataIngestionOrchestrator()
    
    # Process single file
    file_path = Path("data/raw/madani_processed_sentences.txt")
    
    if file_path.exists():
        print(f"\n📄 Processing: {file_path}")
        
        result = await orchestrator.ingest_file(file_path)
        
        print(f"\n✅ Result:")
        print(f"   Status: {result.status.value}")
        print(f"   Duration: {result.duration_ms:.0f}ms")
        print(f"   Records: {result.records_processed}")
        
        if result.errors:
            print(f"   Errors: {result.errors}")
    else:
        print(f"\n❌ File not found: {file_path}")


async def example_custom_parser():
    """Example: Custom parser"""
    
    print("\n" + "=" * 80)
    print("Example: Custom Parser")
    print("=" * 80)
    
    # Get parser for file
    file_path = Path("data/raw/madani_processed_sentences.txt")
    
    if file_path.exists():
        parser = ParserFactory.get_parser(file_path, parser_type='legal')
        
        print(f"\n📄 Parsing: {file_path}")
        print(f"   Parser: {parser.__class__.__name__}")
        
        result = parser.parse(file_path)
        
        print(f"\n✅ Parse Result:")
        print(f"   Success: {result.success}")
        print(f"   Errors: {len(result.errors)}")
        print(f"   Warnings: {len(result.warnings)}")
        
        if result.success and result.data:
            data = result.data
            print(f"\n📊 Extracted Data:")
            print(f"   Law name: {data.get('law_name', 'N/A')}")
            print(f"   Articles: {len(data.get('articles', []))}")
            print(f"   Notes: {len(data.get('notes', []))}")
            print(f"   Chapters: {len(data.get('chapters', []))}")
            
            # Show first article
            if data.get('articles'):
                first_article = data['articles'][0]
                print(f"\n   First Article:")
                print(f"      Number: {first_article.get('number')}")
                print(f"      Content: {first_article.get('content', '')[:100]}...")
    else:
        print(f"\n❌ File not found: {file_path}")


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())
    
    # Run additional examples
    # asyncio.run(example_single_file())
    # asyncio.run(example_custom_parser())
