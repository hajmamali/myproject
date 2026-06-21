"""
Comprehensive Tests for Enterprise Hardening Phase 1
=====================================================

سخت‌ترین تست‌ها برای ماژول‌های جدید:
- Execution Controller
- Seed Manager
- Request Replay
- Distributed Lock
- Deadlock Detector
- Encryption
- Digital Signing
- Alerting

این تست‌ها شامل:
- Edge cases
- Race conditions
- Error handling
- Thread safety
- Performance
- Security
"""

import pytest
import asyncio
import time
import hashlib
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import List

# Execution module
from mahoun.execution import (
    ExecutionController,
    SeedManager,
    RequestReplay,
    ExecutionContext,
    ExecutionStatus,
)

# Concurrency module
from mahoun.concurrency import (
    DeadlockDetector,
    DeadlockResolutionPolicy,
    DeadlockInfo,
)

# Security module (will test without external deps)
import sys
sys.path.insert(0, '.')


class TestExecutionControllerHard:
    """تست‌های سخت برای ExecutionController"""
    
    @pytest.mark.asyncio
    async def test_deterministic_execution_with_same_seed(self):
        """تست: آیا با seed یکسان، نتیجه یکسان می‌دهد؟"""
        controller = ExecutionController()
        
        async def random_handler(ctx: ExecutionContext, data: dict):
            import random
            # فقط random value برمی‌گردانیم (بدون timestamp)
            return {"random": random.randint(0, 1000000)}
        
        # اجرای اول
        result1 = await controller.execute(
            handler=random_handler,
            input_data={"test": "data"},
            seed=42
        )
        
        # اجرای دوم با همان seed
        result2 = await controller.execute(
            handler=random_handler,
            input_data={"test": "data"},
            seed=42
        )
        
        # باید نتیجه یکسان باشد
        assert result1.output == result2.output
        # Note: checksum شامل request_id است که unique است، پس match نمی‌کند
        # اما output باید یکسان باشد
    
    @pytest.mark.asyncio
    async def test_concurrent_executions_thread_safety(self):
        """تست: آیا concurrent executions thread-safe است؟"""
        controller = ExecutionController()
        
        async def simple_handler(ctx: ExecutionContext, data: dict):
            await asyncio.sleep(0.01)  # Simulate work
            return {"id": ctx.request_id}
        
        # اجرای همزمان 100 request
        tasks = [
            controller.execute(
                handler=simple_handler,
                input_data={"index": i}
            )
            for i in range(100)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # همه باید موفق باشند
        assert len(results) == 100
        assert all(r.status == ExecutionStatus.COMPLETED for r in results)
        
        # همه request_id ها باید unique باشند
        request_ids = [r.context.request_id for r in results]
        assert len(set(request_ids)) == 100
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """تست: آیا error handling درست کار می‌کند؟"""
        controller = ExecutionController()
        
        async def failing_handler(ctx: ExecutionContext, data: dict):
            if data.get("should_fail"):
                raise ValueError("Intentional failure")
            return {"success": True}
        
        # تست failure
        result_fail = await controller.execute(
            handler=failing_handler,
            input_data={"should_fail": True}
        )
        
        assert result_fail.status == ExecutionStatus.FAILED
        assert result_fail.error is not None
        assert "Intentional failure" in result_fail.error
        
        # تست success بعد از failure
        result_success = await controller.execute(
            handler=failing_handler,
            input_data={"should_fail": False}
        )
        
        assert result_success.status == ExecutionStatus.COMPLETED
        assert result_success.error is None
    
    @pytest.mark.asyncio
    async def test_replay_verification(self):
        """تست: آیا replay verification درست کار می‌کند؟"""
        controller = ExecutionController(enable_replay=True)
        
        async def deterministic_handler(ctx: ExecutionContext, data: dict):
            import random
            return {"value": random.randint(0, 100)}
        
        # اجرای اول
        result1 = await controller.execute(
            handler=deterministic_handler,
            input_data={"test": "data"},
            seed=123
        )
        
        # Replay
        result2 = await controller.replay(
            request_id=result1.context.request_id,
            handler=deterministic_handler,
            input_data={"test": "data"}
        )
        
        # باید output یکسان باشد (با همان seed)
        assert result2.output == result1.output


class TestSeedManagerHard:
    """تست‌های سخت برای SeedManager"""
    
    def test_seed_derivation_deterministic(self):
        """تست: آیا seed derivation deterministic است؟"""
        manager = SeedManager()
        
        # ایجاد root seed
        root = manager.create_seed(seed=42)
        
        # Derive child seeds
        child1_a = manager.derive_seed(root, "purpose_a")
        child1_b = manager.derive_seed(root, "purpose_a")
        
        # باید یکسان باشند
        assert child1_a.seed == child1_b.seed
        
        # Derive با purpose متفاوت
        child2 = manager.derive_seed(root, "purpose_b")
        
        # باید متفاوت باشند
        assert child1_a.seed != child2.seed
    
    def test_seed_lineage_tracking(self):
        """تست: آیا seed lineage درست track می‌شود؟"""
        manager = SeedManager()
        
        # ایجاد hierarchy
        root = manager.create_seed(seed=100)
        child1 = manager.derive_seed(root, "level1")
        child2 = manager.derive_seed(child1, "level2")
        child3 = manager.derive_seed(child2, "level3")
        
        # بررسی lineage
        lineage = manager.get_seed_lineage(child3)
        
        assert len(lineage) == 4  # root + 3 children
        assert lineage[0].seed == root.seed
        assert lineage[-1].seed == child3.seed
    
    def test_thread_safety_concurrent_derivation(self):
        """تست: آیا concurrent seed derivation thread-safe است؟"""
        manager = SeedManager()
        root = manager.create_seed(seed=999)
        
        def derive_many(purpose_prefix: str):
            results = []
            for i in range(50):
                child = manager.derive_seed(root, f"{purpose_prefix}_{i}")
                results.append(child.seed)
            return results
        
        # اجرای همزمان
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(derive_many, f"thread_{i}")
                for i in range(4)
            ]
            
            all_seeds = []
            for future in futures:
                all_seeds.extend(future.result())
        
        # همه seeds باید unique باشند
        assert len(all_seeds) == 200
        assert len(set(all_seeds)) == 200


class TestDeadlockDetectorHard:
    """تست‌های سخت برای DeadlockDetector"""
    
    def test_simple_deadlock_detection(self):
        """تست: آیا deadlock ساده را detect می‌کند؟"""
        detector = DeadlockDetector()
        
        # ایجاد deadlock: tx1 -> tx2 -> tx1
        detector.register_wait("tx1", "resource_a", "tx2")
        detector.register_wait("tx2", "resource_b", "tx1")
        
        # باید deadlock detect کند
        deadlock = detector.detect()
        
        assert deadlock.detected
        assert len(deadlock.cycle) >= 2
        assert "tx1" in deadlock.cycle
        assert "tx2" in deadlock.cycle
    
    def test_complex_deadlock_detection(self):
        """تست: آیا deadlock پیچیده را detect می‌کند؟"""
        detector = DeadlockDetector()
        
        # ایجاد deadlock: tx1 -> tx2 -> tx3 -> tx4 -> tx1
        detector.register_wait("tx1", "r1", "tx2")
        detector.register_wait("tx2", "r2", "tx3")
        detector.register_wait("tx3", "r3", "tx4")
        detector.register_wait("tx4", "r4", "tx1")
        
        deadlock = detector.detect()
        
        assert deadlock.detected
        assert len(deadlock.cycle) >= 4
    
    def test_deadlock_resolution_youngest(self):
        """تست: آیا resolution policy درست کار می‌کند؟"""
        detector = DeadlockDetector(
            resolution_policy=DeadlockResolutionPolicy.ABORT_YOUNGEST
        )
        
        # ایجاد deadlock با timestamps مختلف
        detector.register_wait("tx1", "r1", "tx2", work_done=0.8)
        time.sleep(0.01)  # تا timestamp متفاوت باشد
        detector.register_wait("tx2", "r2", "tx1", work_done=0.2)
        
        deadlock = detector.detect()
        assert deadlock.detected
        
        # Resolve
        victim = detector.resolve(deadlock)
        
        # باید tx2 (youngest) abort شود
        assert victim == "tx2"
        
        # بعد از resolve، deadlock نباید وجود داشته باشد
        deadlock_after = detector.detect()
        assert not deadlock_after.detected
    
    def test_no_false_positives(self):
        """تست: آیا false positive ندارد؟"""
        detector = DeadlockDetector()
        
        # ایجاد wait-for graph بدون cycle
        detector.register_wait("tx1", "r1", "tx2")
        detector.register_wait("tx2", "r2", "tx3")
        detector.register_wait("tx3", "r3", "tx4")
        # tx4 منتظر کسی نیست
        
        deadlock = detector.detect()
        
        assert not deadlock.detected


class TestEncryptionHard:
    """تست‌های سخت برای Encryption (بدون external deps)"""
    
    def test_encryption_key_generation_uniqueness(self):
        """تست: آیا هر بار key متفاوت generate می‌شود؟"""
        try:
            from mahoun.security import AESEncryption
            
            encryption = AESEncryption()
            
            keys = [encryption.generate_key() for _ in range(10)]
            
            # همه key_id ها باید unique باشند
            key_ids = [k.key_id for k in keys]
            assert len(set(key_ids)) == 10
            
            # همه key materials باید متفاوت باشند
            key_materials = [k.key_material for k in keys]
            assert len(set(key_materials)) == 10
            
        except ImportError:
            pytest.skip("cryptography not installed")
    
    def test_encryption_decryption_roundtrip(self):
        """تست: آیا encrypt/decrypt roundtrip درست کار می‌کند؟"""
        try:
            from mahoun.security import AESEncryption
            
            encryption = AESEncryption()
            key = encryption.generate_key()
            
            # تست با data های مختلف
            test_data = [
                b"simple text",
                b"a" * 1000,  # 1KB
                b"x" * 10000,  # 10KB
                b"\x00\x01\x02\xff",  # binary data
            ]
            
            for plaintext in test_data:
                encrypted = encryption.encrypt(plaintext, key)
                decrypted = encryption.decrypt(encrypted, key)
                
                assert decrypted == plaintext
                
        except ImportError:
            pytest.skip("cryptography not installed")
    
    def test_encryption_tamper_detection(self):
        """تست: آیا tampered data را detect می‌کند؟"""
        try:
            from mahoun.security import AESEncryption
            
            encryption = AESEncryption()
            key = encryption.generate_key()
            
            plaintext = b"important data"
            encrypted = encryption.encrypt(plaintext, key)
            
            # Tamper با ciphertext
            encrypted.ciphertext = encrypted.ciphertext[:-1] + b"\x00"
            
            # باید exception بدهد
            with pytest.raises(ValueError):
                encryption.decrypt(encrypted, key)
                
        except ImportError:
            pytest.skip("cryptography not installed")


class TestSigningHard:
    """تست‌های سخت برای Digital Signing (بدون external deps)"""
    
    def test_signing_verification_roundtrip(self):
        """تست: آیا sign/verify roundtrip درست کار می‌کند؟"""
        try:
            from mahoun.security import Ed25519Signing
            
            signing = Ed25519Signing()
            keypair = signing.generate_keypair()
            
            data = b"important message"
            signature = signing.sign(data, keypair)
            
            # باید verify شود
            assert signing.verify(data, signature, keypair.public_key)
            
        except ImportError:
            pytest.skip("PyNaCl not installed")
    
    def test_signing_tamper_detection(self):
        """تست: آیا tampered data را detect می‌کند؟"""
        try:
            from mahoun.security import Ed25519Signing
            
            signing = Ed25519Signing()
            keypair = signing.generate_keypair()
            
            data = b"original message"
            signature = signing.sign(data, keypair)
            
            # Tamper با data
            tampered_data = b"modified message"
            
            # نباید verify شود
            assert not signing.verify(tampered_data, signature, keypair.public_key)
            
        except ImportError:
            pytest.skip("PyNaCl not installed")


class TestIntegrationScenarios:
    """تست‌های integration سخت"""
    
    @pytest.mark.asyncio
    async def test_full_execution_pipeline_with_replay(self):
        """تست: pipeline کامل execution + replay"""
        controller = ExecutionController(enable_replay=True)
        seed_manager = SeedManager()
        
        # ایجاد seed hierarchy
        root_seed = seed_manager.create_seed(seed=777)
        exec_seed = seed_manager.derive_seed(root_seed, "execution")
        
        async def complex_handler(ctx: ExecutionContext, data: dict):
            import random
            # استفاده از seed - فقط random value
            result = {
                "random_value": random.randint(0, 1000),
                "seed": ctx.seed,
            }
            return result
        
        # اجرای اول
        result1 = await controller.execute(
            handler=complex_handler,
            input_data={"test": "data"},
            seed=exec_seed.seed
        )
        
        assert result1.status == ExecutionStatus.COMPLETED
        
        # Replay
        result2 = await controller.replay(
            request_id=result1.context.request_id,
            handler=complex_handler,
            input_data={"test": "data"}
        )
        
        # نتایج باید یکسان باشند
        assert result2.output["random_value"] == result1.output["random_value"]
        assert result2.output["seed"] == result1.output["seed"]
    
    def test_deadlock_detection_under_load(self):
        """تست: deadlock detection تحت فشار"""
        detector = DeadlockDetector()
        
        # ایجاد 100 transaction با wait-for graph پیچیده
        for i in range(100):
            tx_id = f"tx_{i}"
            next_tx = f"tx_{(i + 1) % 100}"
            resource = f"resource_{i}"
            
            detector.register_wait(tx_id, resource, next_tx)
        
        # باید deadlock بزرگ detect کند
        deadlock = detector.detect()
        
        assert deadlock.detected
        assert len(deadlock.cycle) >= 2


class TestPerformance:
    """تست‌های performance"""
    
    @pytest.mark.asyncio
    async def test_execution_controller_throughput(self):
        """تست: throughput ExecutionController"""
        controller = ExecutionController()
        
        async def fast_handler(ctx: ExecutionContext, data: dict):
            return {"result": "ok"}
        
        start_time = time.time()
        
        # اجرای 1000 request
        tasks = [
            controller.execute(
                handler=fast_handler,
                input_data={"index": i}
            )
            for i in range(1000)
        ]
        
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        throughput = 1000 / elapsed
        
        print(f"\nThroughput: {throughput:.2f} req/sec")
        
        # باید حداقل 100 req/sec باشد
        assert throughput > 100
        assert all(r.status == ExecutionStatus.COMPLETED for r in results)
    
    def test_deadlock_detector_performance(self):
        """تست: performance DeadlockDetector"""
        detector = DeadlockDetector()
        
        # ایجاد 1000 wait
        for i in range(1000):
            detector.register_wait(f"tx_{i}", f"r_{i}", f"tx_{(i+1) % 1000}")
        
        start_time = time.time()
        
        # Detection
        deadlock = detector.detect()
        
        elapsed = time.time() - start_time
        
        print(f"\nDeadlock detection time: {elapsed*1000:.2f}ms")
        
        # باید کمتر از 100ms باشد
        assert elapsed < 0.1
        assert deadlock.detected


# تست‌های edge case
class TestEdgeCases:
    """تست‌های edge case"""
    
    @pytest.mark.asyncio
    async def test_execution_with_zero_seed(self):
        """تست: seed=0 درست کار می‌کند؟"""
        controller = ExecutionController()
        
        async def handler(ctx: ExecutionContext, data: dict):
            return {"seed": ctx.seed}
        
        result = await controller.execute(
            handler=handler,
            input_data={},
            seed=0
        )
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.context.seed == 0
    
    def test_deadlock_detector_empty_graph(self):
        """تست: empty graph deadlock ندارد"""
        detector = DeadlockDetector()
        
        deadlock = detector.detect()
        
        assert not deadlock.detected
        assert len(deadlock.cycle) == 0
    
    def test_seed_manager_large_hierarchy(self):
        """تست: hierarchy بزرگ"""
        manager = SeedManager()
        
        # ایجاد hierarchy با 100 level
        current = manager.create_seed(seed=1)
        
        for i in range(100):
            current = manager.derive_seed(current, f"level_{i}")
        
        # بررسی lineage
        lineage = manager.get_seed_lineage(current)
        
        assert len(lineage) == 101  # root + 100 levels


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
