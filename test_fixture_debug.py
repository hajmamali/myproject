"""Debug test to verify inject_fake_embedding_service works"""
import sys
sys.path.insert(0, '.')

from tests.bootstrap.characterization.fixtures import inject_fake_embedding_service

print("✅ Import successful")

# Test the patch
with inject_fake_embedding_service() as patch_context:
    print("✅ Patch context entered")
    
    # Now try importing inside the patch
    from mahoun.embeddings.local_service import LocalEmbeddingService
    print(f"✅ LocalEmbeddingService imported: {LocalEmbeddingService}")
    
    # Try instantiating WITHOUT config (the production bug)
    try:
        service = LocalEmbeddingService()
        print(f"✅ Service instantiated without config: {service}")
        print(f"   Has inner: {hasattr(service, 'inner')}")
    except TypeError as e:
        print(f"❌ FAILED to instantiate: {e}")
        
print("✅ Test complete")
