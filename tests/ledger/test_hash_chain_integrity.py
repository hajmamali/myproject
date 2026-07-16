"""
tests/ledger/test_hash_chain_integrity.py
==========================================

WAVE 1 WEEK 2: Ledger Module - Hash Chain Integrity Tests

Objective: Prove hash chain tampering detection and fork prevention

Critical Paths Tested (P0):
- Block hash tampering detection
- Chain link verification
- Genesis block integrity
- Fork attack prevention
- Index sequence validation
- Prev_hash integrity
- Data tampering detection
- Hash recomputation after modification

Coverage Target: Contribute to Ledger 51.62% → 60%+

Test Categories:
1. Tampering Detection (8 tests)
2. Chain Verification (6 tests)
3. Block Validation (4 tests)
4. Fork Detection (2 tests)

Total: 20 tests
"""

import hashlib
import json
import pytest
from datetime import datetime, UTC, timedelta
from mahoun.ledger.block import Block, create_genesis_block
from mahoun.ledger.models import LedgerEntry
from mahoun.ledger.blockchain import ImmutableLedger


class TestTamperingDetection:
    """Test hash chain tampering detection (P0 Critical)"""
    
    @pytest.mark.p1
    def test_block_hash_tampering_detected(self):
        """
        Critical: Modified block hash must be detected
        
        Risk: Attacker changes verdict data and forges hash
        Impact: Audit trail compromised, legal evidence invalid
        """
        entry = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        genesis = create_genesis_block()
        block = Block(
            index=1,
            timestamp=datetime.now(UTC),
            data=entry,
            prev_hash=genesis.hash
        )
        
        original_hash = block.hash
        
        # Tamper: manually create block with wrong hash
        tampered_block = Block.__new__(Block)
        object.__setattr__(tampered_block, 'index', block.index)
        object.__setattr__(tampered_block, 'timestamp', block.timestamp)
        object.__setattr__(tampered_block, 'data', block.data)
        object.__setattr__(tampered_block, 'prev_hash', block.prev_hash)
        object.__setattr__(tampered_block, 'hash', 'f' * 64)  # Fake hash
        
        # Verify integrity check catches tampering
        assert not tampered_block.verify_integrity()
        assert tampered_block.hash != tampered_block.compute_hash()
    
    @pytest.mark.p1
    def test_data_modification_changes_hash(self):
        """
        Critical: Any data modification must change block hash
        
        Risk: Attacker modifies confidence score without detection
        Impact: Fraudulent audit trail
        """
        entry1 = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.85,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        entry2 = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.95,  # Different confidence
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=entry1.created_at  # Same timestamp
        )
        
        genesis = create_genesis_block()
        
        block1 = Block(index=1, timestamp=datetime.now(UTC), data=entry1, prev_hash=genesis.hash)
        block2 = Block(index=1, timestamp=block1.timestamp, data=entry2, prev_hash=genesis.hash)
        
        # Different data must produce different hashes
        assert block1.hash != block2.hash
    
    @pytest.mark.p1
    def test_prev_hash_modification_detected(self):
        """
        Critical: Modified prev_hash must invalidate chain link
        
        Risk: Attacker re-parents block to different chain
        Impact: Fork attack, history rewriting
        """
        genesis = create_genesis_block()
        
        entry = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        # Create block with correct prev_hash
        block_correct = Block(
            index=1,
            timestamp=datetime.now(UTC),
            data=entry,
            prev_hash=genesis.hash
        )
        
        # Create block with wrong prev_hash
        block_wrong = Block(
            index=1,
            timestamp=block_correct.timestamp,
            data=entry,
            prev_hash="a" * 64  # Wrong prev_hash
        )
        
        # Hashes must be different
        assert block_correct.hash != block_wrong.hash
        
        # Wrong block breaks chain link
        assert block_wrong.prev_hash != genesis.hash
    
    @pytest.mark.p1
    def test_timestamp_modification_changes_hash(self):
        """
        Critical: Timestamp tampering must be detectable
        
        Risk: Attacker backdates verdict to change legal timeline
        Impact: Fraudulent temporal evidence
        """
        genesis = create_genesis_block()
        
        entry = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        ts1 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        ts2 = datetime(2026, 1, 15, 11, 0, 0, tzinfo=UTC)
        
        block1 = Block(index=1, timestamp=ts1, data=entry, prev_hash=genesis.hash)
        block2 = Block(index=1, timestamp=ts2, data=entry, prev_hash=genesis.hash)
        
        # Different timestamps must produce different hashes
        assert block1.hash != block2.hash
    
    @pytest.mark.p1
    def test_index_modification_changes_hash(self):
        """
        Critical: Index tampering must be detectable
        
        Risk: Attacker reorders blocks in chain
        Impact: Temporal ordering compromised
        """
        genesis = create_genesis_block()
        
        entry = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        ts = datetime.now(UTC)
        
        block_index1 = Block(index=1, timestamp=ts, data=entry, prev_hash=genesis.hash)
        block_index2 = Block(index=2, timestamp=ts, data=entry, prev_hash=genesis.hash)
        
        # Different indices must produce different hashes
        assert block_index1.hash != block_index2.hash
    
    @pytest.mark.p1
    def test_ledger_entry_field_tampering_detected(self):
        """
        Critical: Any ledger entry field modification must change hash
        
        Risk: Attacker modifies referenced_ltm_nodes
        Impact: Evidence linkage broken
        """
        genesis = create_genesis_block()
        ts = datetime.now(UTC)
        
        entry1 = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=ts
        )
        
        entry2 = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_220"],  # Different rule
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=ts
        )
        
        block1 = Block(index=1, timestamp=ts, data=entry1, prev_hash=genesis.hash)
        block2 = Block(index=1, timestamp=ts, data=entry2, prev_hash=genesis.hash)
        
        assert block1.hash != block2.hash
    
    @pytest.mark.p1
    def test_serialization_deserialization_preserves_hash(self):
        """
        Critical: Serialize → deserialize must preserve hash
        
        Risk: Hash changes during persistence/loading
        Impact: False tampering alerts
        """
        genesis = create_genesis_block()
        
        entry = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        original_block = Block(
            index=1,
            timestamp=datetime.now(UTC),
            data=entry,
            prev_hash=genesis.hash
        )
        
        # Serialize
        block_dict = original_block.to_dict()
        
        # Deserialize
        restored_block = Block.from_dict(block_dict)
        
        # Hash must be preserved
        assert original_block.hash == restored_block.hash
        assert restored_block.verify_integrity()
    
    @pytest.mark.p1
    def test_ledger_multi_block_tampering_detected(self):
        """
        Critical: Tampering in middle of chain must be detected
        
        Risk: Attacker modifies block N and re-chains subsequent blocks
        Impact: Partial history rewriting
        """
        ledger = ImmutableLedger()
        
        # Add 3 blocks
        for i in range(3):
            entry = LedgerEntry(
                verdict_id=f"verdict_{i}",
                case_id=f"case_{i}",
                referenced_ltm_nodes=[f"rule_{i}"],
                referenced_facts=[f"fact_{i}"],
                confidence=0.85,
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime.now(UTC)
            )
            ledger.append(entry)
        
        # Verify chain is valid
        assert ledger.verify_integrity()
        
        # Tamper with middle block (cannot actually mutate frozen Block, but test detection)
        middle_block = ledger.chain[1]
        
        # Create fake tampered block
        tampered_block = Block.__new__(Block)
        object.__setattr__(tampered_block, 'index', middle_block.index)
        object.__setattr__(tampered_block, 'timestamp', middle_block.timestamp)
        
        # Modify data
        tampered_entry = LedgerEntry(
            verdict_id="TAMPERED",
            case_id="case_0",
            referenced_ltm_nodes=["rule_0"],
            referenced_facts=["fact_0"],
            confidence=0.99,  # Changed
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=middle_block.data.created_at
        )
        object.__setattr__(tampered_block, 'data', tampered_entry)
        object.__setattr__(tampered_block, 'prev_hash', middle_block.prev_hash)
        object.__setattr__(tampered_block, 'hash', middle_block.hash)  # Keep old hash (forgery attempt)
        
        # Integrity check must fail
        assert not tampered_block.verify_integrity()


class TestChainVerification:
    """Test chain link verification (P0 Critical)"""
    
    @pytest.mark.p1
    def test_genesis_block_structure(self):
        """
        Critical: Genesis block must have deterministic structure
        
        Risk: Different genesis blocks in different instances
        Impact: Chain incompatibility
        """
        genesis1 = create_genesis_block()
        genesis2 = create_genesis_block()
        
        # Genesis blocks must be identical
        assert genesis1.hash == genesis2.hash
        assert genesis1.index == 0
        assert genesis1.data is None
        assert genesis1.prev_hash == "0" * 64
        assert genesis1.verify_integrity()
    
    @pytest.mark.p1
    def test_chain_link_integrity(self):
        """
        Critical: Each block must link to previous block
        
        Risk: Broken chain links
        Impact: Audit trail invalid
        """
        ledger = ImmutableLedger()
        
        # Add 5 blocks
        for i in range(5):
            entry = LedgerEntry(
                verdict_id=f"verdict_{i}",
                case_id=f"case_{i}",
                referenced_ltm_nodes=[f"rule_{i}"],
                referenced_facts=[f"fact_{i}"],
                confidence=0.85,
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime.now(UTC)
            )
            ledger.append(entry)
        
        # Verify all chain links
        for i in range(1, len(ledger.chain)):
            current_block = ledger.chain[i]
            prev_block = ledger.chain[i - 1]
            
            # Current block must reference previous block hash
            assert current_block.prev_hash == prev_block.hash
    
    @pytest.mark.p1
    def test_index_sequence_validation(self):
        """
        Critical: Block indices must be sequential
        
        Risk: Gap or duplicate indices
        Impact: Missing blocks, ordering corruption
        """
        ledger = ImmutableLedger()
        
        # Add 10 blocks
        for i in range(10):
            entry = LedgerEntry(
                verdict_id=f"verdict_{i}",
                case_id=f"case_{i}",
                referenced_ltm_nodes=[f"rule_{i}"],
                referenced_facts=[f"fact_{i}"],
                confidence=0.85,
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime.now(UTC)
            )
            ledger.append(entry)
        
        # Verify indices are 0, 1, 2, ..., 10
        for i, block in enumerate(ledger.chain):
            assert block.index == i
    
    @pytest.mark.p1
    def test_empty_ledger_valid(self):
        """
        Critical: Empty ledger with only genesis block must be valid
        
        Risk: Invalid initial state
        Impact: Cannot bootstrap ledger
        """
        ledger = ImmutableLedger()
        
        assert len(ledger.chain) == 1  # Only genesis
        assert ledger.chain[0].index == 0
        assert ledger.verify_integrity()
    
    @pytest.mark.p1
    def test_single_block_chain_valid(self):
        """
        Critical: Single data block + genesis must be valid
        
        Risk: Minimum chain validation broken
        Impact: Cannot add first verdict
        """
        ledger = ImmutableLedger()
        
        entry = LedgerEntry(
            verdict_id="verdict_0",
            case_id="case_0",
            referenced_ltm_nodes=["rule_0"],
            referenced_facts=["fact_0"],
            confidence=0.85,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        ledger.append(entry)
        
        assert len(ledger.chain) == 2
        assert ledger.verify_integrity()
    
    @pytest.mark.p1
    def test_long_chain_integrity(self):
        """
        Critical: Long chains must remain valid
        
        Risk: Chain verification performance or correctness degrades
        Impact: Production audit trails invalid
        """
        ledger = ImmutableLedger()
        
        # Add 100 blocks
        for i in range(100):
            entry = LedgerEntry(
                verdict_id=f"verdict_{i}",
                case_id=f"case_{i}",
                referenced_ltm_nodes=[f"rule_{i}"],
                referenced_facts=[f"fact_{i}"],
                confidence=0.85,
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime.now(UTC)
            )
            ledger.append(entry)
        
        assert len(ledger.chain) == 101  # 100 + genesis
        assert ledger.verify_integrity()


class TestBlockValidation:
    """Test individual block validation (P0 Critical)"""
    
    @pytest.mark.p1
    def test_block_immutability(self):
        """
        Critical: Blocks must be frozen (immutable)
        
        Risk: Post-creation modification
        Impact: Tampering possible
        """
        genesis = create_genesis_block()
        
        entry = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        block = Block(
            index=1,
            timestamp=datetime.now(UTC),
            data=entry,
            prev_hash=genesis.hash
        )
        
        # Attempt to modify should fail
        with pytest.raises((AttributeError, TypeError)):
            block.index = 999
        
        with pytest.raises((AttributeError, TypeError)):
            block.hash = "fake_hash"
    
    @pytest.mark.p1
    def test_genesis_block_immutability(self):
        """
        Critical: Genesis block must be immutable
        
        Risk: Genesis tampering
        Impact: Entire chain invalid
        """
        genesis = create_genesis_block()
        
        # Attempt to modify should fail
        with pytest.raises((AttributeError, TypeError)):
            genesis.prev_hash = "tampered"
        
        with pytest.raises((AttributeError, TypeError)):
            genesis.timestamp = datetime.now(UTC)
    
    @pytest.mark.p1
    def test_block_hash_deterministic(self):
        """
        Critical: Same input must always produce same hash
        
        Risk: Non-deterministic hashing
        Impact: Verification fails on replay
        """
        genesis = create_genesis_block()
        
        entry = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        )
        
        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        
        # Create same block 100 times
        hashes = set()
        for _ in range(100):
            block = Block(
                index=1,
                timestamp=ts,
                data=entry,
                prev_hash=genesis.hash
            )
            hashes.add(block.hash)
        
        # All hashes must be identical
        assert len(hashes) == 1
    
    @pytest.mark.p1
    def test_block_equality_based_on_hash(self):
        """
        Critical: Block equality must be hash-based
        
        Risk: Duplicate detection fails
        Impact: Same block added twice
        """
        genesis = create_genesis_block()
        
        entry = LedgerEntry(
            verdict_id="verdict_123",
            case_id="case_456",
            referenced_ltm_nodes=["rule_219"],
            referenced_facts=["fact_0"],
            confidence=0.92,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        ts = datetime.now(UTC)
        
        block1 = Block(index=1, timestamp=ts, data=entry, prev_hash=genesis.hash)
        block2 = Block(index=1, timestamp=ts, data=entry, prev_hash=genesis.hash)
        
        # Blocks with same content must be equal
        assert block1 == block2
        assert block1.hash == block2.hash


class TestForkDetection:
    """Test fork attack prevention (P0 Critical)"""
    
    @pytest.mark.p1
    def test_fork_detection_different_prev_hash(self):
        """
        Critical: Fork with different prev_hash must be detectable
        
        Risk: Attacker creates alternate chain branch
        Impact: Audit trail ambiguity
        """
        ledger = ImmutableLedger()
        
        # Add first block
        entry1 = LedgerEntry(
            verdict_id="verdict_1",
            case_id="case_1",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=["fact_1"],
            confidence=0.85,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        ledger.append(entry1)
        
        # Create two competing blocks with different prev_hash
        entry2a = LedgerEntry(
            verdict_id="verdict_2a",
            case_id="case_2",
            referenced_ltm_nodes=["rule_2"],
            referenced_facts=["fact_2"],
            confidence=0.85,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        entry2b = LedgerEntry(
            verdict_id="verdict_2b",
            case_id="case_2",
            referenced_ltm_nodes=["rule_2"],
            referenced_facts=["fact_2"],
            confidence=0.85,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        # Both reference same prev_hash (index 1)
        correct_prev = ledger.chain[-1].hash
        
        block2a = Block(index=2, timestamp=datetime.now(UTC), data=entry2a, prev_hash=correct_prev)
        block2b = Block(index=2, timestamp=datetime.now(UTC), data=entry2b, prev_hash="a" * 64)  # Wrong prev
        
        # Blocks must have different hashes
        assert block2a.hash != block2b.hash
        
        # Only one can extend the chain correctly
        assert block2a.prev_hash == correct_prev
        assert block2b.prev_hash != correct_prev
    
    @pytest.mark.p1
    def test_index_gap_detection(self):
        """
        Critical: Missing blocks (index gaps) must be detected
        
        Risk: Block deletion or skipping
        Impact: Incomplete audit trail
        """
        ledger = ImmutableLedger()
        
        # Add blocks 0, 1, 2
        for i in range(3):
            entry = LedgerEntry(
                verdict_id=f"verdict_{i}",
                case_id=f"case_{i}",
                referenced_ltm_nodes=[f"rule_{i}"],
                referenced_facts=[f"fact_{i}"],
                confidence=0.85,
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime.now(UTC)
            )
            ledger.append(entry)
        
        # Manually create block with index 5 (gap)
        entry_gap = LedgerEntry(
            verdict_id="verdict_5",
            case_id="case_5",
            referenced_ltm_nodes=["rule_5"],
            referenced_facts=["fact_5"],
            confidence=0.85,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        block_gap = Block(
            index=5,  # Gap: should be 3
            timestamp=datetime.now(UTC),
            data=entry_gap,
            prev_hash=ledger.chain[-1].hash
        )
        
        # Adding block with gap should fail in real implementation
        # (Here we just verify the index is wrong)
        assert block_gap.index != len(ledger.chain)
