import pytest
pytest.importorskip("hypothesis")
"""
Property-Based Tests for Evidence Ledger
=========================================
Tests universal properties of ledger system.

Property 3: Ledger Entry Completeness
Property 4: Ledger Hash Chain Integrity
"""

import pytest
from hypothesis import given, strategies as st, assume
from pathlib import Path
import tempfile
from datetime import datetime, timezone

from mahoun.ledger.writer import (
    EvidenceLedgerWriter,
    JSONLLedgerBackend,
    SQLiteLedgerBackend,
    NoOpLedgerBackend,
)
from mahoun.ledger.models import LedgerEntry


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def ledger_entry_strategy(draw):
    """Generate valid LedgerEntry instances."""
    verdict_id = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters="\x00")))
    case_id = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters="\x00")))
    
    # At least one of ltm_nodes or facts must be non-empty
    has_ltm = draw(st.booleans())
    has_facts = draw(st.booleans())
    assume(has_ltm or has_facts)  # At least one must be true
    
    ltm_nodes = draw(st.lists(st.text(min_size=1, max_size=20), min_size=1 if has_ltm else 0, max_size=5))
    facts = draw(st.lists(st.text(min_size=1, max_size=50), min_size=1 if has_facts else 0, max_size=5))
    
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    guard_mode = draw(st.sampled_from(["OFF", "WARN", "STRICT", "AUDIT"]))
    
    return LedgerEntry(
        verdict_id=verdict_id,
        case_id=case_id,
        referenced_ltm_nodes=ltm_nodes,
        referenced_facts=facts,
        confidence=confidence,
        invariant_version="1.0.0",
        guard_mode=guard_mode,
        created_at=datetime.now(timezone.utc),
        event_type="verdict",
        request_id=f"req_{draw(st.integers(min_value=1000, max_value=9999))}"
    )


# =============================================================================
# Property 3: Ledger Entry Completeness
# =============================================================================

@given(entry=ledger_entry_strategy())
def test_property_entry_completeness(entry):
    """
    Property 3: Ledger Entry Completeness
    
    For any ledger entry written, the entry SHALL contain all required fields.
    """
    # Required fields
    assert entry.verdict_id
    assert entry.case_id
    assert entry.confidence >= 0.0 and entry.confidence <= 1.0
    assert entry.invariant_version
    assert entry.guard_mode in ["OFF", "WARN", "STRICT", "AUDIT"]
    assert entry.created_at
    
    # At least one evidence source
    assert len(entry.referenced_ltm_nodes) > 0 or len(entry.referenced_facts) > 0


@given(entry=ledger_entry_strategy())
def test_property_entry_write_success_jsonl(entry):
    """
    Property: Entry can be written to JSONL backend.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = JSONLLedgerBackend(Path(tmpdir) / "ledger.jsonl")
        writer = EvidenceLedgerWriter(backend)
        
        # Write should succeed
        entry_hash = writer.write(entry)
        
        assert entry_hash
        assert len(entry_hash) == 64  # SHA-256 hex


@given(entry=ledger_entry_strategy())
def test_property_entry_write_success_sqlite(entry):
    """
    Property: Entry can be written to SQLite backend.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteLedgerBackend(Path(tmpdir) / "ledger.db")
        writer = EvidenceLedgerWriter(backend)
        
        # Write should succeed
        entry_hash = writer.write(entry)
        
        assert entry_hash
        assert len(entry_hash) == 64  # SHA-256 hex


# =============================================================================
# Property 4: Ledger Hash Chain Integrity
# =============================================================================

@given(entries=st.lists(ledger_entry_strategy(), min_size=2, max_size=10))
def test_property_hash_chain_integrity_jsonl(entries):
    """
    Property 4: Ledger Hash Chain Integrity
    
    For any sequence of entries, each entry's hash SHALL depend on previous hash.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = JSONLLedgerBackend(Path(tmpdir) / "ledger.jsonl")
        writer = EvidenceLedgerWriter(backend)
        
        # Write all entries
        hashes = []
        for entry in entries:
            entry_hash = writer.write(entry)
            hashes.append(entry_hash)
        
        # Verify chain integrity
        assert backend.verify_chain()
        
        # Each hash should be unique
        assert len(set(hashes)) == len(hashes)


@given(entries=st.lists(ledger_entry_strategy(), min_size=2, max_size=10))
def test_property_hash_chain_integrity_sqlite(entries):
    """
    Property: Hash chain integrity holds for SQLite backend.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteLedgerBackend(Path(tmpdir) / "ledger.db")
        writer = EvidenceLedgerWriter(backend)
        
        # Write all entries
        hashes = []
        for entry in entries:
            entry_hash = writer.write(entry)
            hashes.append(entry_hash)
        
        # Verify chain integrity
        assert backend.verify_chain()
        
        # Each hash should be unique
        assert len(set(hashes)) == len(hashes)


@given(entries=st.lists(ledger_entry_strategy(), min_size=3, max_size=10))
def test_property_tamper_detection(entries):
    """
    Property: Tampering with an entry SHALL break the chain.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = JSONLLedgerBackend(Path(tmpdir) / "ledger.jsonl")
        writer = EvidenceLedgerWriter(backend)
        
        # Write all entries
        for entry in entries:
            writer.write(entry)
        
        # Verify chain is valid
        assert backend.verify_chain()
        
        # Tamper with middle entry
        all_entries = backend.read_all()
        if len(all_entries) >= 2:
            # Modify the second entry's verdict_id
            all_entries[1]["entry"]["verdict_id"] = "TAMPERED"
            
            # Write tampered data back
            import json
            with open(backend.path, 'w') as f:
                for record in all_entries:
                    f.write(json.dumps(record, default=str) + '\n')
            
            # Chain should now be broken
            assert not backend.verify_chain()


@given(entry=ledger_entry_strategy())
def test_property_hash_includes_prev_hash(entry):
    """
    Property: Entry hash SHALL include previous hash in computation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = JSONLLedgerBackend(Path(tmpdir) / "ledger.jsonl")
        writer = EvidenceLedgerWriter(backend)
        
        # Write first entry
        hash1 = writer.write(entry)
        
        # Write same entry again (should have different hash due to prev_hash)
        hash2 = writer.write(entry)
        
        # Hashes should be different even though entry is same
        assert hash1 != hash2
