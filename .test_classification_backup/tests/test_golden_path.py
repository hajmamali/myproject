"""
Golden Path End-to-End Test
===========================
Test the complete Golden Path execution flow as defined in the specification.
"""

import pytest
import tempfile
import os
from pathlib import Path

from mahoun.pipelines.ingestion.pipeline import IngestionPipelineV2
from mahoun.retrieval.hybrid_search_v2 import HybridSearchV2, RetrievalMethod, FusionMethod
from mahoun.pipelines.vector_store.manager import VectorStoreManager


@pytest.mark.asyncio
async def test_golden_path_e2e():
    """Test the complete Golden Path execution flow"""
    
    # Setup
    pipeline = IngestionPipelineV2()
    await pipeline.initialize()
    
    vector_store = VectorStoreManager()
    await vector_store.initialize()
    
    search = HybridSearchV2(vector_store=vector_store)
    await search.initialize()
    
    # Create test document
    test_content = """
    بسمه تعالی
    
    قرارداد خرید و فروش اموال منقول
    
    تاریخ: 1403/05/15
    شماره: 789456/1403
    
    طرف اول: شرکت تجارت نوین
    نام و نام خانوادگی: محمد رضایی
    کد ملی: 1234567890
    
    طرف دوم: شرکت توسعه صنعتی
    نام و نام خانوادگی: احمد محمدی
    کد ملی: 0987654321
    
    موضوع قرارداد: خرید و فروش ماشین آلات صنعتی
    
    متن کامل قرارداد شامل شرایط و ضوابط مربوط به خرید و فروش ماشین آلات 
    صنعتی و تعهدات طرفین در قبال یکدیگر و نحوه تسویه حساب و تحویل کالا.
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        # Step 1: Document Ingestion
        doc_id = "test_contract_001"
        result = await pipeline.ingest_file(temp_path, doc_id=doc_id)
        
        # Verification
        assert result.success == True, f"Ingestion failed: {result.error}"
        assert result.chunks_created > 0, "No chunks were created"
        assert result.embeddings_created == result.chunks_created, \
            f"Mismatch between chunks ({result.chunks_created}) and embeddings ({result.embeddings_created})"
        assert result.indexed == True, "Document was not indexed in vector store"
        
        # Validate runtime evidence
        assert result.chunks_created >= 2, f"Expected at least 2 chunks, got {result.chunks_created}"
        assert result.embeddings_created == result.chunks_created, \
            f"Embeddings count ({result.embeddings_created}) doesn't match chunks count ({result.chunks_created})"
        
        # Step 2: Retrieval
        query = "خرید و فروش ماشین آلات"
        search_result = await search.search(
            query=query,
            top_k=5,
            method=RetrievalMethod.HYBRID,
            fusion=FusionMethod.RRF
        )
        
        # Verification
        assert len(search_result.results) > 0, "No search results returned"
        assert all(0 <= r.score <= 1 for r in search_result.results), \
            "Search scores are not in expected range [0, 1]"
        
        # Check that our document appears in results
        doc_found = any(r.id.startswith(doc_id) for r in search_result.results)
        assert doc_found, "Original document not found in search results"
        
        # Validate result quality
        assert len(search_result.results) <= 5, "Too many results returned"
        
    finally:
        # Cleanup
        os.unlink(temp_path)
        await pipeline.close()
        await search.close()


@pytest.mark.asyncio
async def test_golden_path_vector_store_failure_path(monkeypatch):
    """
    Failure path: رفتار سیستم وقتی vector store در دسترس نیست.

    سناریو:
    - ingestion روی فایل معتبر انجام می‌شود
    - مرحلهٔ embedding با موفقیت انجام می‌شود
    - ولی insert در VectorStoreManager همیشه شکست می‌خورد
    انتظار:
    - result.success == False
    - result.indexed == False
    - هیچ fake success برگردانده نمی‌شود
    - پیام خطا شفاف و مرتبط با vector store باشد
    """

    # Setup: یک pipeline واقعی ولی با vector_store خراب‌شده
    pipeline = IngestionPipelineV2()

    # اول initialize را صدا می‌زنیم تا vector_store ساخته شود
    await pipeline.initialize()

    # اطمینان از این‌که vector_store واقعاً از نوع VectorStoreManager است
    assert isinstance(pipeline.vector_store, VectorStoreManager)

    # همهٔ تلاش‌های insert در vector_store را به شکست تبدیل می‌کنیم
    async def _failing_insert(*args, **kwargs):
        # شبیه‌سازی unavailability: همیشه False برمی‌گردد
        return False

    monkeypatch.setattr(
        pipeline.vector_store,
        "insert",
        _failing_insert,
        raising=True,
    )

    # یک فایل موقت معتبر می‌سازیم
    test_content = """
    قرارداد نمونه برای تست failure path
    موضوع: خرید تجهیزات
    مبلغ: ۵۰۰ میلیون تومان
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_path = f.name

    try:
        # اجرای ingestion
        result = await pipeline.ingest_file(temp_path, doc_id="failure_path_contract")

        # انتظارات اصلی failure path
        assert result.success is False, "ingestion نباید در صورت خرابی vector store موفق گزارش شود"
        assert result.indexed is False, "در failure path نباید سند index شده باشد"

        # embedding تا قبل از insert باید انجام شده باشد
        assert result.chunks_created > 0, "در failure path هم باید chunk تولید شده باشد"
        assert result.embeddings_created == result.chunks_created, (
            "تعداد embedding باید با تعداد chunk برابر باشد، حتی اگر ذخیره‌سازی شکست بخورد"
        )

        # پیام خطا باید شفاف و مرتبط با vector store باشد
        assert result.error is not None
        assert "Vector storage failed" in result.error, (
            f"پیام خطا باید به شکست vector store اشاره کند، ولی بود: {result.error}"
        )

        # آمار pipeline باید failure را ثبت کرده باشد
        stats = pipeline.get_stats()
        assert stats["documents_processed"] >= 1
        assert stats["documents_failed"] >= 1

        # و مهم‌تر از همه: هیچ insert موفقی در vector_store ثبت نشده باشد
        vs_stats = stats.get("vector_store", {})
        if vs_stats:
            # اگر backend آمار inserts دارد، باید صفر بماند
            inserts = vs_stats.get("inserts", 0)
            assert inserts == 0, f"در failure path نباید insert موفق ثبت شود، ولی inserts={inserts}"

    finally:
        os.unlink(temp_path)
        await pipeline.close()


@pytest.mark.asyncio
async def test_golden_path_health_status():
    """Test that health status accurately reflects Golden Path components"""
    
    # Setup
    pipeline = IngestionPipelineV2()
    await pipeline.initialize()
    
    vector_store = VectorStoreManager()
    await vector_store.initialize()
    
    # Verify components are properly initialized
    assert pipeline._initialized == True, "Ingestion pipeline not initialized"
    assert vector_store._initialized == True, "Vector store not initialized"
    
    # Check stats for evidence of operation
    pipeline_stats = pipeline.get_stats()
    vector_stats = vector_store.get_stats()
    
    # These should exist as evidence of proper initialization
    assert "documents_processed" in pipeline_stats, "Pipeline stats missing documents_processed"
    assert "inserts" in vector_stats, "Vector store stats missing inserts"
    
    # Cleanup
    await pipeline.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])