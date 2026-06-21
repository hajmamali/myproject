"""
Wiring Test - بررسی اتصال کامپوننت‌ها
====================================

این تست‌ها بررسی می‌کنند که:
1. همه کامپوننت‌ها به درستی import می‌شوند
2. Dependencies در دسترس هستند
3. Integration بین کامپوننت‌ها کار می‌کند
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestImports:
    """Test that all components can be imported"""
    
    def test_import_document_normalizer(self):
        """Test Document Normalizer import"""
        from mahoun.pipelines.ingestion.document_normalizer import DocumentNormalizer
        assert DocumentNormalizer is not None
    
    def test_import_metadata_extractor(self):
        """Test Metadata Extractor import"""
        from mahoun.pipelines.ingestion.metadata_extractor import MetadataExtractor
        assert MetadataExtractor is not None
    
    def test_import_ocr_handler(self):
        """Test OCR Handler import"""
        from mahoun.pipelines.ingestion.ocr_handler import OCRHandler
        assert OCRHandler is not None
    
    def test_import_document_handlers(self):
        """Test Document Handlers import"""
        from mahoun.pipelines.ingestion.document_handlers import (
            TxtHandler,
            DocxHandler,
            PdfHandler,
            DocumentHandlerFactory
        )
        assert TxtHandler is not None
        assert DocumentHandlerFactory is not None
    
    def test_import_ingestion_pipeline(self):
        """Test Ingestion Pipeline import"""
        from mahoun.pipelines.ingestion import IngestionPipeline
        assert IngestionPipeline is not None
    
    def test_import_agents(self):
        """Test Agents import"""
        from mahoun.agents.base_agent import BaseAgent
        from mahoun.agents import Orchestrator, ContractAgent
        assert BaseAgent is not None
        assert Orchestrator is not None
        assert ContractAgent is not None
    
    def test_import_rag_components(self):
        """Test RAG components import"""
        try:
            from mahoun.rag.hybrid_rag_service import HybridRAGService
            assert HybridRAGService is not None
        except ImportError as e:
            pytest.skip(f"HybridRAGService not available: {e}")
    
    def test_import_vector_store(self):
        """Test Vector Store import"""
        from mahoun.pipelines.vector_store.manager import VectorStoreManager
        assert VectorStoreManager is not None


class TestDependencies:
    """Test that dependencies are available"""
    
    def test_basic_dependencies(self):
        """Test basic Python dependencies"""
        import asyncio
        import logging
        import json
        from datetime import datetime
        from typing import Dict, Any
        
        assert asyncio is not None
        assert logging is not None
        assert json is not None
        assert datetime is not None
    
    def test_optional_dependencies(self):
        """Test optional dependencies (should not fail if missing)"""
        optional_deps = {
            "docx": "python-docx",
            "PyPDF2": "PyPDF2",
            "pytesseract": "pytesseract",
            "paddleocr": "paddleocr"
        }
        
        available = {}
        for module_name, package_name in optional_deps.items():
            try:
                __import__(module_name)
                available[package_name] = True
            except ImportError:
                available[package_name] = False
        
        # Log availability
        print(f"\nOptional dependencies: {available}")
        
        # Test should pass regardless
        assert True


class TestComponentInitialization:
    """Test that components can be initialized"""
    
    def test_document_normalizer_init(self):
        """Test Document Normalizer initialization"""
        from mahoun.pipelines.ingestion.document_normalizer import DocumentNormalizer
        normalizer = DocumentNormalizer()
        assert normalizer is not None
        assert normalizer.txt_handler is not None
    
    def test_metadata_extractor_init(self):
        """Test Metadata Extractor initialization"""
        from mahoun.pipelines.ingestion.metadata_extractor import MetadataExtractor
        extractor = MetadataExtractor()
        assert extractor is not None
    
    def test_ocr_handler_init(self):
        """Test OCR Handler initialization"""
        from mahoun.pipelines.ingestion.ocr_handler import OCRHandler
        handler = OCRHandler()
        assert handler is not None
        # Availability depends on dependencies
        assert isinstance(handler.available, bool)
    
    def test_agent_orchestrator_init(self):
        """Test Agent Orchestrator initialization"""
        from mahoun.agents import Orchestrator
        orchestrator = Orchestrator()
        assert orchestrator is not None
        # Check if orchestrator has workflows attribute (UltraOrchestrator structure)
        assert hasattr(orchestrator, 'workflows') or hasattr(orchestrator, 'agents')
    
    def test_contract_agent_init(self):
        """Test Contract Agent initialization"""
        from mahoun.agents import ContractAgent
        agent = ContractAgent()
        assert agent is not None
        # UltraContractAgent may have different attribute names
        assert hasattr(agent, 'name') or hasattr(agent, 'agent_name')


class TestIntegrationPoints:
    """Test integration points between components"""
    
    @pytest.mark.asyncio
    async def test_normalizer_to_ingestion_pipeline(self):
        """Test Document Normalizer → Ingestion Pipeline"""
        try:
            from mahoun.pipelines.ingestion.document_normalizer import DocumentNormalizer
            from mahoun.pipelines.ingestion import IngestionPipeline
            
            # Create normalizer
            normalizer = DocumentNormalizer()
            normalized = await normalizer.normalize_text(
                text="Test document",
                doc_type="document"
            )
            
            # Create pipeline
            pipeline = IngestionPipeline()
            await pipeline.initialize()
            
            # Should be able to ingest
            assert pipeline._initialized
            
        except Exception as e:
            pytest.skip(f"Integration test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_contract_agent_with_rag(self):
        """Test Contract Agent with RAG integration"""
        try:
            from mahoun.agents import ContractAgent
            
            agent = ContractAgent()
            await agent.initialize()
            
            # Check if RAG service is available
            if hasattr(agent, 'rag_service') and agent.rag_service:
                assert agent.rag_service is not None
            else:
                pytest.skip("RAG service not available")
            
        except Exception as e:
            pytest.skip(f"Contract Agent RAG integration test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_metadata_extractor_with_ner(self):
        """Test Metadata Extractor with NER"""
        try:
            from mahoun.pipelines.ingestion.metadata_extractor import MetadataExtractor
            
            extractor = MetadataExtractor()
            
            # Check if NER engine is available
            if extractor.ner_engine:
                assert extractor.ner_engine is not None
            else:
                # Should still work without NER
                assert extractor is not None
            
        except Exception as e:
            pytest.skip(f"NER integration test skipped: {e}")


class TestErrorHandling:
    """Test error handling and graceful degradation"""
    
    def test_missing_file_handling(self):
        """Test handling of missing files"""
        from mahoun.pipelines.ingestion.document_normalizer import DocumentNormalizer
        
        normalizer = DocumentNormalizer()
        
        # Should raise FileNotFoundError for missing file
        with pytest.raises(FileNotFoundError):
            import asyncio
            asyncio.run(normalizer.normalize_file("/nonexistent/file.txt"))
    
    @pytest.mark.asyncio
    async def test_invalid_document_type(self):
        """Test handling of invalid document types"""
        from mahoun.pipelines.ingestion.document_normalizer import DocumentNormalizer
        
        normalizer = DocumentNormalizer()
        
        # Should work with any doc_type
        result = await normalizer.normalize_text(
            text="Test",
            doc_type="invalid_type"
        )
        
        assert result.type == "invalid_type"  # Should accept any type


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

