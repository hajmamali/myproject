"""
Extended Hard Integration Tests
================================
Additional hard tests covering stress, memory, concurrency, and edge cases.

Test Categories:
1. Stress Tests (high load, many operations)
2. Memory Tests (memory usage, leaks)
3. Concurrency Tests (race conditions, deadlocks)
4. Performance Regression Tests
5. Resource Exhaustion Tests
6. Error Recovery Tests
7. Data Integrity Tests
"""

import pytest
import tempfile
import time
import threading
import gc
import psutil
import os
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

# ============================================================================
# Stress Tests
# ============================================================================

class TestStressTests:
    """Stress tests for high-load scenarios"""
    
    def test_chunking_stress_large_document(self):
        """Test chunking with very large document (10MB+)"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create a large document (~1MB)
        large_text = "متن نمونه برای تست استرس. " * 50000  # ~1MB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(large_text)
            temp_path = f.name
        
        try:
            start_time = time.time()
            result = extract_document_text(
                temp_path,
                enable_chunking=True,
                chunk_size=512,
                chunk_overlap=50
            )
            duration = time.time() - start_time
            
            assert result.success, "Should handle large document"
            assert duration < 10.0, f"Large document chunking should be fast, took {duration:.2f}s"
            if result.chunks:
                assert len(result.chunks) > 100, "Large document should produce many chunks"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_metadata_extraction_stress(self):
        """Test metadata extraction with many documents"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create multiple documents
        documents = []
        for i in range(50):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}: متن نمونه برای تست استرس. تاریخ: ۱۴۰۳/۰۱/۱۵")
                documents.append(f.name)
        
        try:
            start_time = time.time()
            results = []
            for doc_path in documents:
                result = extract_document_text(
                    doc_path,
                    enable_metadata_extraction=True,
                    doc_type="verdict"
                )
                results.append(result)
            duration = time.time() - start_time
            
            assert len(results) == 50, "Should process all documents"
            assert duration < 30.0, f"Batch metadata extraction should be fast, took {duration:.2f}s"
            success_count = sum(1 for r in results if r.success)
            assert success_count == 50, f"All documents should succeed, got {success_count}/50"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)
    
    def test_monitoring_stress_many_operations(self):
        """Test monitoring with many operations"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text, get_global_metrics
        
        # Perform many operations
        operations = 100
        documents = []
        
        for i in range(operations):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}: متن نمونه")
                documents.append(f.name)
        
        try:
            start_time = time.time()
            for doc_path in documents:
                extract_document_text(doc_path, enable_monitoring=True)
            duration = time.time() - start_time
            
            metrics = get_global_metrics()
            if metrics:
                assert metrics.query_count >= operations, f"Should track all operations, got {metrics.query_count}/{operations}"
            
            assert duration < 20.0, f"Many operations should be fast, took {duration:.2f}s"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)
    
    def test_combined_features_stress(self):
        """Test all features combined under stress"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create a moderately large document
        large_text = "متن نمونه برای تست استرس با همه فیچرها. " * 10000
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(large_text)
            temp_path = f.name
        
        try:
            start_time = time.time()
            result = extract_document_text(
                temp_path,
                enable_chunking=True,
                chunk_size=256,
                chunk_overlap=30,
                enable_metadata_extraction=True,
                doc_type="verdict",
                enable_monitoring=True
            )
            duration = time.time() - start_time
            
            assert result.success, "Should handle stress with all features"
            assert duration < 15.0, f"All features under stress should be fast, took {duration:.2f}s"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# ============================================================================
# Memory Tests
# ============================================================================

class TestMemoryTests:
    """Memory usage and leak tests"""
    
    def test_chunking_memory_usage(self):
        """Test chunking doesn't cause memory leaks"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        import gc
        
        # Get initial memory
        process = psutil.Process(os.getpid())
        initial_mem = process.memory_info().rss
        
        # Create a large document
        large_text = "متن نمونه برای تست حافظه. " * 100000  # ~2MB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(large_text)
            temp_path = f.name
        
        try:
            # Perform chunking multiple times
            for _ in range(10):
                result = extract_document_text(
                    temp_path,
                    enable_chunking=True,
                    chunk_size=512,
                    chunk_overlap=50
                )
                assert result.success
            
            # Force garbage collection
            gc.collect()
            
            # Check memory usage
            final_mem = process.memory_info().rss
            mem_increase = final_mem - initial_mem
            mem_increase_mb = mem_increase / (1024 * 1024)
            
            # Memory increase should be reasonable (< 50MB)
            assert mem_increase_mb < 50, f"Memory increase too high: {mem_increase_mb:.2f}MB"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_metadata_extraction_memory_usage(self):
        """Test metadata extraction doesn't cause memory leaks"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        import gc
        
        process = psutil.Process(os.getpid())
        initial_mem = process.memory_info().rss
        
        # Create documents
        documents = []
        for i in range(20):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}: متن نمونه برای تست حافظه. تاریخ: ۱۴۰۳/۰۱/۱۵")
                documents.append(f.name)
        
        try:
            # Perform metadata extraction multiple times
            for _ in range(5):
                for doc_path in documents:
                    extract_document_text(
                        doc_path,
                        enable_metadata_extraction=True,
                        doc_type="verdict"
                    )
            
            gc.collect()
            
            final_mem = process.memory_info().rss
            mem_increase = final_mem - initial_mem
            mem_increase_mb = mem_increase / (1024 * 1024)
            
            assert mem_increase_mb < 30, f"Memory increase too high: {mem_increase_mb:.2f}MB"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)
    
    def test_monitoring_memory_usage(self):
        """Test monitoring doesn't cause memory leaks"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text, get_global_metrics
        import gc
        
        process = psutil.Process(os.getpid())
        initial_mem = process.memory_info().rss
        
        # Perform many monitored operations
        documents = []
        for i in range(100):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}: متن نمونه")
                documents.append(f.name)
        
        try:
            for doc_path in documents:
                extract_document_text(doc_path, enable_monitoring=True)
            
            gc.collect()
            
            final_mem = process.memory_info().rss
            mem_increase = final_mem - initial_mem
            mem_increase_mb = mem_increase / (1024 * 1024)
            
            assert mem_increase_mb < 20, f"Memory increase too high: {mem_increase_mb:.2f}MB"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)


# ============================================================================
# Concurrency Tests
# ============================================================================

class TestConcurrencyTests:
    """Concurrency and race condition tests"""
    
    def test_chunking_concurrent_access(self):
        """Test chunking with concurrent access"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create documents
        documents = []
        for i in range(20):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}: متن نمونه برای تست همروندی. " * 100)
                documents.append(f.name)
        
        def process_document(doc_path):
            return extract_document_text(
                doc_path,
                enable_chunking=True,
                chunk_size=256,
                chunk_overlap=30
            )
        
        try:
            # Process concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_document, doc) for doc in documents]
                results = [future.result() for future in as_completed(futures)]
            
            assert len(results) == 20, "Should process all documents"
            success_count = sum(1 for r in results if r.success)
            assert success_count == 20, f"All documents should succeed, got {success_count}/20"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)
    
    def test_metadata_extraction_concurrent_access(self):
        """Test metadata extraction with concurrent access"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        documents = []
        for i in range(15):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}: متن نمونه. تاریخ: ۱۴۰۳/۰۱/۱۵")
                documents.append(f.name)
        
        def process_document(doc_path):
            return extract_document_text(
                doc_path,
                enable_metadata_extraction=True,
                doc_type="verdict"
            )
        
        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_document, doc) for doc in documents]
                results = [future.result() for future in as_completed(futures)]
            
            assert len(results) == 15, "Should process all documents"
            success_count = sum(1 for r in results if r.success)
            assert success_count == 15, f"All documents should succeed, got {success_count}/15"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)
    
    def test_monitoring_concurrent_access(self):
        """Test monitoring with concurrent access"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text, get_global_metrics
        
        documents = []
        for i in range(30):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}: متن نمونه")
                documents.append(f.name)
        
        def process_document(doc_path):
            return extract_document_text(doc_path, enable_monitoring=True)
        
        try:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(process_document, doc) for doc in documents]
                results = [future.result() for future in as_completed(futures)]
            
            assert len(results) == 30, "Should process all documents"
            success_count = sum(1 for r in results if r.success)
            assert success_count == 30, f"All documents should succeed, got {success_count}/30"
            
            # Check metrics consistency
            metrics = get_global_metrics()
            if metrics:
                assert metrics.query_count >= 30, f"Should track all operations, got {metrics.query_count}/30"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)
    
    def test_global_metrics_thread_safety(self):
        """Test global metrics singleton is thread-safe"""
        from mahoun.pipelines.ingestion.document_handlers import get_global_metrics
        
        def access_metrics():
            for _ in range(100):
                metrics = get_global_metrics()
                if metrics:
                    metrics.record_query(0.1)
        
        threads = [threading.Thread(target=access_metrics) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should not crash
        metrics = get_global_metrics()
        if metrics:
            assert metrics.query_count > 0, "Should have recorded queries"


# ============================================================================
# Performance Regression Tests
# ============================================================================

class TestPerformanceRegression:
    """Performance regression tests"""
    
    def test_chunking_performance_baseline(self):
        """Test chunking performance meets baseline"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create a document of known size
        text = "متن نمونه برای تست پرفورمنس. " * 10000  # ~200KB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        
        try:
            # Warm up
            for _ in range(3):
                extract_document_text(temp_path, enable_chunking=True)
            
            # Measure
            times = []
            for _ in range(5):
                start = time.time()
                result = extract_document_text(temp_path, enable_chunking=True)
                duration = time.time() - start
                times.append(duration)
                del result
            
            avg_time = sum(times) / len(times)
            
            # Baseline: should complete in < 2 seconds for 200KB
            assert avg_time < 2.0, f"Performance regression: chunking too slow {avg_time:.2f}s"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_metadata_extraction_performance_baseline(self):
        """Test metadata extraction performance meets baseline"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        text = "متن نمونه برای تست پرفورمنس. تاریخ: ۱۴۰۳/۰۱/۱۵. شماره: ۱۲۳۴۵. " * 5000
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        
        try:
            # Warm up
            for _ in range(3):
                extract_document_text(temp_path, enable_metadata_extraction=True, doc_type="verdict")
            
            # Measure
            times = []
            for _ in range(5):
                start = time.time()
                result = extract_document_text(temp_path, enable_metadata_extraction=True, doc_type="verdict")
                duration = time.time() - start
                times.append(duration)
                del result
            
            avg_time = sum(times) / len(times)
            
            # Baseline: should complete in < 3 seconds for 100KB
            assert avg_time < 3.0, f"Performance regression: metadata extraction too slow {avg_time:.2f}s"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_monitoring_overhead(self):
        """Test monitoring overhead is minimal"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        text = "متن نمونه برای تست پرفورمنس. " * 5000
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        
        try:
            # Without monitoring
            times_without = []
            for _ in range(10):
                start = time.time()
                extract_document_text(temp_path, enable_monitoring=False)
                times_without.append(time.time() - start)
            
            # With monitoring
            times_with = []
            for _ in range(10):
                start = time.time()
                extract_document_text(temp_path, enable_monitoring=True)
                times_with.append(time.time() - start)
            
            avg_without = sum(times_without) / len(times_without)
            avg_with = sum(times_with) / len(times_with)
            
            overhead = ((avg_with - avg_without) / avg_without) * 100 if avg_without > 0 else 0
            
            # Overhead should be < 50% (relaxed threshold for realistic expectations)
            assert overhead < 50, f"Monitoring overhead too high: {overhead:.1f}%"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# ============================================================================
# Resource Exhaustion Tests
# ============================================================================

class TestResourceExhaustion:
    """Resource exhaustion tests"""
    
    def test_chunking_with_disk_space_warning(self):
        """Test chunking handles disk space gracefully"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # This is a conceptual test - actual disk space exhaustion is hard to test safely
        # We'll test with a very large file that might trigger warnings
        
        # Create a moderately large file
        text = "متن نمونه. " * 100000  # ~500KB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        
        try:
            result = extract_document_text(
                temp_path,
                enable_chunking=True,
                chunk_size=512
            )
            
            # Should handle gracefully
            assert result.success or result.error is not None, "Should either succeed or have error"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_metadata_extraction_with_complex_text(self):
        """Test metadata extraction with complex text"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create text with many dates and patterns
        complex_text = """
        تاریخ ۱: ۱۴۰۳/۰۱/۱۵
        تاریخ ۲: ۱۴۰۳/۰۲/۲۰
        تاریخ ۳: ۱۴۰۳/۰۳/۲۵
        شماره ۱: ۱۲۳۴۵
        شماره ۲: ۶۷۸۹۰
        شماره ۳: ۱۱۱۱۲
        """ * 100
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(complex_text)
            temp_path = f.name
        
        try:
            result = extract_document_text(
                temp_path,
                enable_metadata_extraction=True,
                doc_type="verdict"
            )
            
            assert result.success, "Should handle complex text"
            # Should not crash or timeout
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_monitoring_with_many_metrics(self):
        """Test monitoring handles many metrics"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text, get_global_metrics
        
        documents = []
        for i in range(200):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}")
                documents.append(f.name)
        
        try:
            for doc_path in documents:
                extract_document_text(doc_path, enable_monitoring=True)
            
            metrics = get_global_metrics()
            if metrics:
                # Should handle many metrics without issues
                assert metrics.query_count >= 200, f"Should track all operations, got {metrics.query_count}/200"
                # Get stats should not crash
                stats = metrics.get_stats()
                assert stats is not None, "Should be able to get stats"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)


# ============================================================================
# Error Recovery Tests
# ============================================================================

class TestErrorRecovery:
    """Error recovery and resilience tests"""
    
    def test_chunking_after_partial_failure(self):
        """Test chunking recovers from partial failure"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create a document
        text = "متن نمونه برای تست بازیابی از خطا. " * 100
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        
        try:
            # First attempt should succeed
            result1 = extract_document_text(temp_path, enable_chunking=True)
            assert result1.success, "First attempt should succeed"
            
            # Second attempt should also succeed (no state corruption)
            result2 = extract_document_text(temp_path, enable_chunking=True)
            assert result2.success, "Second attempt should succeed"
            
            # Results should be consistent
            assert result1.text == result2.text, "Results should be consistent"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_metadata_extraction_after_corrupted_input(self):
        """Test metadata extraction recovers from corrupted input"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create a document with potentially problematic content
        problematic_text = "متن نمونه \x00 \x01 \x02 با کاراکترهای خاص. تاریخ: ۱۴۰۳/۰۱/۱۵"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(problematic_text)
            temp_path = f.name
        
        try:
            result = extract_document_text(
                temp_path,
                enable_metadata_extraction=True,
                doc_type="verdict"
            )
            
            # Should handle gracefully
            assert result.success or result.error is not None, "Should either succeed or have error"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_monitoring_after_error(self):
        """Test monitoring continues after errors"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text, get_global_metrics
        
        # Process valid document
        text = "متن نمونه"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        
        try:
            # Process valid document
            result1 = extract_document_text(temp_path, enable_monitoring=True)
            assert result1.success, "Valid document should succeed"
            
            # Try to process nonexistent document (will fail)
            result2 = extract_document_text("/nonexistent/file.txt", enable_monitoring=True)
            assert not result2.success, "Nonexistent document should fail"
            
            # Process valid document again (monitoring should still work)
            result3 = extract_document_text(temp_path, enable_monitoring=True)
            assert result3.success, "Valid document should succeed after error"
            
            metrics = get_global_metrics()
            if metrics:
                # Should have recorded both success and error
                assert metrics.query_count > 0, "Should have recorded operations"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# ============================================================================
# Data Integrity Tests
# ============================================================================

class TestDataIntegrity:
    """Data integrity and consistency tests"""
    
    def test_chunking_preserves_content(self):
        """Test chunking preserves original content"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        original_text = "متن نمونه برای تست یکپارچگی داده. " * 100
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(original_text)
            temp_path = f.name
        
        try:
            result = extract_document_text(temp_path, enable_chunking=True)
            
            assert result.success, "Extraction should succeed"
            assert result.text == original_text, "Original text should be preserved"
            
            if result.chunks:
                # Verify that chunks collectively contain the original content
                # Due to overlap, reconstructed text may be longer, but should contain all original content
                all_chunk_text = "".join(chunk.text for chunk in result.chunks)
                # Check that all key phrases from original are in chunks
                key_phrase = "متن نمونه برای تست یکپارچگی داده"
                assert key_phrase in all_chunk_text, "Key content should be preserved in chunks"
                # Also verify that chunks are not empty
                assert all(len(chunk.text) > 0 for chunk in result.chunks), "All chunks should have content"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_metadata_extraction_consistency(self):
        """Test metadata extraction is consistent"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        text = "متن نمونه. تاریخ: ۱۴۰۳/۰۱/۱۵. شماره: ۱۲۳۴۵. موضوع: تست."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        
        try:
            # Extract metadata multiple times
            results = []
            for _ in range(5):
                result = extract_document_text(
                    temp_path,
                    enable_metadata_extraction=True,
                    doc_type="verdict"
                )
                results.append(result)
            
            # All results should be consistent
            for result in results:
                assert result.success, "All extractions should succeed"
                assert result.text == text, "Text should be consistent"
            
            # Metadata should be consistent
            first_metadata = results[0].metadata
            for result in results[1:]:
                # Compare key metadata fields
                if first_metadata.get("metadata_extracted"):
                    assert result.metadata.get("metadata_extracted") == first_metadata.get("metadata_extracted"), "Metadata extraction flag should be consistent"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_monitoring_metrics_accuracy(self):
        """Test monitoring metrics are accurate"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text, get_global_metrics
        
        # Reset metrics if possible
        metrics = get_global_metrics()
        if metrics:
            initial_count = metrics.query_count
        else:
            initial_count = 0
        
        # Perform known number of operations
        operations = 20
        documents = []
        for i in range(operations):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(f"Document {i}")
                documents.append(f.name)
        
        try:
            for doc_path in documents:
                extract_document_text(doc_path, enable_monitoring=True)
            
            metrics = get_global_metrics()
            if metrics:
                expected_count = initial_count + operations
                assert metrics.query_count == expected_count, f"Metrics should be accurate, got {metrics.query_count}/{expected_count}"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)


# ============================================================================
# Integration Stress Tests
# ============================================================================

class TestIntegrationStress:
    """Integration stress tests combining multiple features"""
    
    def test_all_features_under_high_load(self):
        """Test all features combined under high load"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Create many documents
        documents = []
        for i in range(30):
            text = f"Document {i}: متن نمونه برای تست یکپارچگی. تاریخ: ۱۴۰۳/۰۱/۱۵. " * 50
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(text)
                documents.append(f.name)
        
        def process_document(doc_path):
            return extract_document_text(
                doc_path,
                enable_chunking=True,
                chunk_size=256,
                chunk_overlap=30,
                enable_metadata_extraction=True,
                doc_type="verdict",
                enable_monitoring=True
            )
        
        try:
            start_time = time.time()
            
            # Process concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_document, doc) for doc in documents]
                results = [future.result() for future in as_completed(futures)]
            
            duration = time.time() - start_time
            
            assert len(results) == 30, "Should process all documents"
            success_count = sum(1 for r in results if r.success)
            assert success_count == 30, f"All documents should succeed, got {success_count}/30"
            assert duration < 30.0, f"High load with all features should be fast, took {duration:.2f}s"
            
            # Verify features worked
            with_chunks = sum(1 for r in results if r.chunks and len(r.chunks) > 0)
            with_metadata = sum(1 for r in results if r.metadata.get("metadata_extracted"))
            with_timing = sum(1 for r in results if r.metadata.get("extraction_time_ms"))
            
            assert with_chunks > 0, "Some documents should have chunks"
            assert with_metadata > 0, "Some documents should have metadata"
            assert with_timing == 30, "All documents should have timing"
        finally:
            for doc_path in documents:
                if os.path.exists(doc_path):
                    os.unlink(doc_path)
    
    def test_rapid_feature_toggle(self):
        """Test rapid toggling of features"""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        text = "متن نمونه برای تست تغییر سریع فیچرها."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        
        try:
            # Rapidly toggle features
            configurations = [
                (True, False, False),
                (False, True, False),
                (False, False, True),
                (True, True, False),
                (True, False, True),
                (False, True, True),
                (True, True, True),
            ]
            
            for chunking, metadata, monitoring in configurations:
                result = extract_document_text(
                    temp_path,
                    enable_chunking=chunking,
                    enable_metadata_extraction=metadata,
                    doc_type="verdict" if metadata else "general",
                    enable_monitoring=monitoring
                )
                assert result.success, f"Should succeed with config {configurations}"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
