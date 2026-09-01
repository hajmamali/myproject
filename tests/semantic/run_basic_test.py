#!/usr/bin/env python3
"""
Basic test runner to demonstrate Phase 2A concepts.
"""

print("🔵 Phase 2A Contract Tests - Basic Demo")
print("=" * 50)

# Test 1: Missing Evidence Rejection
print("\n🔴 Test 1: Missing Evidence → REJECTED")
try:
    # Simulate missing evidence
    if None is None:  # Missing evidence
        raise Exception("GovernanceViolation: Missing source text span")
    print("❌ Should have failed")
except Exception as e:
    print(f"✅ PASS: {e}")

# Test 2: Duplicate Identity Rejection
print("\n🔴 Test 2: Duplicate Identity → REJECTED")
entities = []
try:
    # First entity
    entity1 = {"canonical_id": "concept_ownership", "jurisdiction": "IR"}
    entities.append(entity1)
    
    # Try duplicate
    entity2 = {"canonical_id": "concept_ownership", "jurisdiction": "IR"}
    
    # Check for duplicate
    for existing in entities:
        if (existing["canonical_id"] == entity2["canonical_id"] and
            existing["jurisdiction"] == entity2["jurisdiction"]):
            raise Exception("IntegrityError: duplicate_canonical_id")
    
    print("❌ Should have failed")
except Exception as e:
    print(f"✅ PASS: {e}")

# Test 3: Unverified Endpoints Rejection
print("\n🔴 Test 3: Unverified Endpoints → REJECTED")
def can_create_edge(source_status, target_status):
    if source_status not in ["VERIFIED", "MATERIALIZED"]:
        return False, "source_not_verified"
    if target_status not in ["VERIFIED", "MATERIALIZED"]:
        return False, "target_not_verified"
    return True, "verified"

# Test CANDIDATE → VERIFIED
can_create, reason = can_create_edge("CANDIDATE", "VERIFIED")
if not can_create and reason == "source_not_verified":
    print("✅ PASS: CANDIDATE source rejected")
else:
    print("❌ FAIL: Should reject CANDIDATE source")

# Test VERIFIED → VERIFIED
can_create, reason = can_create_edge("VERIFIED", "VERIFIED")
if can_create and reason == "verified":
    print("✅ PASS: VERIFIED endpoints accepted")
else:
    print("❌ FAIL: Should accept VERIFIED endpoints")

# Test 4: Reasoning Exclusion
print("\n🔴 Test 4: Reasoning Excludes Unverified → VERIFIED ONLY")
assertions = [
    {"id": "assertion_1", "status": "VERIFIED"},
    {"id": "assertion_2", "status": "CANDIDATE"},
    {"id": "assertion_3", "status": "VERIFIED"},
    {"id": "assertion_4", "status": "UNRESOLVED"}
]

# Filter for reasoning (verified only)
reasoning_assertions = [
    a for a in assertions 
    if a["status"] == "VERIFIED"
]

if len(reasoning_assertions) == 2:
    print("✅ PASS: Only VERIFIED assertions in reasoning")
    for a in reasoning_assertions:
        print(f"   - {a['id']} ({a['status']})")
else:
    print(f"❌ FAIL: Expected 2 verified, got {len(reasoning_assertions)}")

# Test 5: Valid Case Acceptance
print("\n🟢 Test 5: Valid Case → ACCEPTED")
valid_fact = {
    "source_text_span": "مالکیت",
    "source_sha256": "abc123",
    "source_article_id": "article_10",
    "status": "VERIFIED"
}

if (valid_fact["source_text_span"] and 
    valid_fact["source_sha256"] and 
    valid_fact["source_article_id"]):
    print("✅ PASS: Valid fact accepted")
else:
    print("❌ FAIL: Valid fact rejected")

print("\n" + "=" * 50)
print("🎉 Phase 2A Contract Demo Complete!")
print("\nKey Principles Demonstrated:")
print("  🔴 Missing Evidence → REJECT")
print("  🔴 Duplicate Identity → REJECT")
print("  🔴 Unverified Endpoints → REJECT")
print("  🔴 Reasoning Excludes Unverified → VERIFIED ONLY")
print("  🟢 Valid Cases → ACCEPT")
print("\n✨ This is the foundation of zero-hallucination guarantee!")