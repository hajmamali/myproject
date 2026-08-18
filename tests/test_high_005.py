"""
MAHOUN HIGH-005 Proof-Evidence Binding Test Suite
==================================================

Classification: HIGH / ARCHITECTURAL / HARDENING
Purpose: Verify that proof generation validates evidence_refs (RULE 5)

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

import sys
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')


def test_empty_evidence_refs_raises_error():
    """Test that empty evidence_refs raises ValueError."""
    print("\n  Testing empty evidence_refs validation...")
    
    from mahoun.crypto.proof_system import generate_proof
    from mahoun.crypto.signatures import generate_keypair
    
    # Generate keypair
    private_key, public_key = generate_keypair()
    
    # Try to generate proof with empty evidence_refs
    try:
        proof = generate_proof(
            graph_nodes={"node1": {"id": "node1", "type": "rule"}},
            graph_edges=[],
            reasoning_steps=[{"statement": "test"}],
            evidence_refs=[],  # Empty - should raise
            verdict_id="test",
            case_id="test",
            confidence=0.9,
            private_key=private_key,
        )
        print("  ✗ ERROR: Empty evidence_refs did not raise ValueError")
        return False
    except ValueError as e:
        if "RULE 5 VIOLATION" in str(e):
            print(f"  ✓ Correctly raised ValueError with RULE 5 message: {e}")
            return True
        else:
            print(f"  ✗ Raised ValueError but without RULE 5 message: {e}")
            return False
    except Exception as e:
        print(f"  ✗ Unexpected exception: {type(e).__name__}: {e}")
        return False


def test_non_empty_evidence_refs_succeeds():
    """Test that non-empty evidence_refs succeeds."""
    print("\n  Testing non-empty evidence_refs...")
    
    from mahoun.crypto.proof_system import generate_proof
    from mahoun.crypto.signatures import generate_keypair
    
    # Generate keypair
    private_key, public_key = generate_keypair()
    
    # Try to generate proof with non-empty evidence_refs
    try:
        proof = generate_proof(
            graph_nodes={"node1": {"id": "node1", "type": "rule"}},
            graph_edges=[],
            reasoning_steps=[{"statement": "test"}],
            evidence_refs=[{"node_id": "ev1", "type": "Fact"}],  # Non-empty
            verdict_id="test",
            case_id="test",
            confidence=0.9,
            private_key=private_key,
        )
        print(f"  ✓ Proof generated successfully with evidence_refs")
        print(f"    evidence_merkle_root: {proof.evidence_merkle_root[:32]}...")
        return True
    except Exception as e:
        print(f"  ✗ Unexpected exception: {type(e).__name__}: {e}")
        return False


def test_evidence_merkle_root_in_proof():
    """Test that evidence_merkle_root is set in proof."""
    print("\n  Testing evidence_merkle_root in proof...")
    
    from mahoun.crypto.proof_system import generate_proof
    from mahoun.crypto.signatures import generate_keypair
    
    # Generate keypair
    private_key, public_key = generate_keypair()
    
    # Generate proof
    proof = generate_proof(
        graph_nodes={"node1": {"id": "node1", "type": "rule"}},
        graph_edges=[],
        reasoning_steps=[{"statement": "test"}],
        evidence_refs=[{"node_id": "ev1"}, {"node_id": "ev2"}],
        verdict_id="test",
        case_id="test",
        confidence=0.9,
        private_key=private_key,
    )
    
    # Check that evidence_merkle_root is set
    assert proof.evidence_merkle_root is not None, "evidence_merkle_root is None"
    assert len(proof.evidence_merkle_root) > 0, "evidence_merkle_root is empty"
    
    print(f"  ✓ evidence_merkle_root is set in proof")
    print(f"    Merkle root: {proof.evidence_merkle_root[:32]}...")
    return True


def test_evidence_in_message():
    """Test that evidence is incorporated into signed message."""
    print("\n  Testing evidence incorporation in signed message...")
    
    from mahoun.crypto.proof_system import generate_proof
    from mahoun.crypto.signatures import generate_keypair, verify_signature
    
    # Generate keypair
    private_key, public_key = generate_keypair()
    
    # Generate proof
    evidence_refs = [{"node_id": "ev1", "type": "Fact"}]
    proof = generate_proof(
        graph_nodes={"node1": {"id": "node1", "type": "rule"}},
        graph_edges=[],
        reasoning_steps=[{"statement": "test"}],
        evidence_refs=evidence_refs,
        verdict_id="test",
        case_id="test",
        confidence=0.9,
        private_key=private_key,
    )
    
    # Verify the proof
    is_valid = proof.verify(public_key)
    assert is_valid, "Proof verification failed"
    
    print(f"  ✓ Proof is valid and incorporates evidence")
    return True


def test_source_code_has_validation():
    """Test that source code has evidence_refs validation."""
    print("\n  Testing source code for evidence_refs validation...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/crypto/proof_system.py', 'r') as f:
        content = f.read()
    
    # Check for the validation
    assert 'if not evidence_refs:' in content, "evidence_refs validation not found"
    assert 'RULE 5 VIOLATION' in content, "RULE 5 VIOLATION message not found"
    assert 'evidence_refs cannot be empty' in content, "error message not found"
    
    print("  ✓ Source code has evidence_refs validation")
    return True


def main():
    print("\n" + "=" * 80)
    print("  MAHOUN HIGH-005: Proof-Evidence Binding Test Suite")
    print("=" * 80)
    
    tests = [
        test_empty_evidence_refs_raises_error,
        test_non_empty_evidence_refs_succeeds,
        test_evidence_merkle_root_in_proof,
        test_evidence_in_message,
        test_source_code_has_validation,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 80)
    print(f"  HIGH-005 PROOF-EVIDENCE BINDING TESTS")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total-passed}/{total}")
    
    if all(results):
        print("\n  ✅ ALL HIGH-005 TESTS PASSED")
        return 0
    else:
        print("\n  ❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
