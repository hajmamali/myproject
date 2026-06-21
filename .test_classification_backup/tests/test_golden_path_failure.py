"""
Golden Path Failure Path Test
=============================
Test system behavior when Golden Path components fail.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from mahoun.pipelines.ingestion.pipeline import IngestionPipelineV2
from mahoun.pipelines.vector_store.manager import VectorStoreManager


@pytest.mark.asyncio
async def test_vector_store_unavailable():
    """Test system behavior when vector store is unavailable"""
    
    # Setup pipeline
    pipeline = IngestionPipelineV2()
    await pipeline.initialize()
    
    # Create test document
    test_content = "Simple test document content for ingestion."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        # Mock vector store to simulate failure
        with patch.object(pipeline, 'vector_store') as mock_vector_store:
            # Simulate insertion failure
            mock_vector_store.insert.return_value = False
            
            # Attempt ingestion
            doc_id = "test_doc_fail"
            result = await pipeline.ingest_file(temp_path, doc_id=doc_id)
            
            # Verification - should fail gracefully
            assert result.success == False, "Ingestion should have failed with unavailable vector store"
            assert result.indexed == False, "Document should not be marked as indexed"
            assert "Vector storage failed" in result.error, \
                f"Error message should indicate storage failure, got: {result.error}"
            
    finally:
        # Cleanup
        os.unlink(temp_path)
        await pipeline.close()


@pytest.mark.asyncio
async def test_embedding_generation_failure():
    """Test system behavior when embedding generation fails"""
    
    # Setup pipeline
    pipeline = IngestionPipelineV2()
    await pipeline.initialize()
    
    # Create test document
    test_content = "Simple test document content for ingestion."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        # Mock embedding service to simulate failure
        with patch.object(pipeline.embedding_service, 'embed_texts') as mock_embed:
            # Simulate embedding generation failure
            mock_embed.side_effect = Exception("Embedding model not loaded")
            
            # Attempt ingestion
            doc_id = "test_doc_embed_fail"
            result = await pipeline.ingest_file(temp_path, doc_id=doc_id)
            
            # Verification - should fail gracefully
            assert result.success == False, "Ingestion should have failed with embedding generation error"
            assert result.embeddings_created == 0, "No embeddings should be created"
            assert "Embedding generation failed" in result.error, \
                f"Error message should indicate embedding failure, got: {result.error}"
            
    finally:
        # Cleanup
        os.unlink(temp_path)
        await pipeline.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])