import pytest
pytest.importorskip("hypothesis")
"""
Property-Based Tests for Safe Serialization
============================================
Tests universal properties of serialization system.

Property 1: Serialization Round-Trip
For any valid data object, serializing then deserializing SHALL produce equivalent object.
"""

import pytest
from hypothesis import given, strategies as st
from pathlib import Path
import tempfile
import json

from mahoun.core.serialization import SafeSerializer, SerializationError


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# JSON-safe primitive types
json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1e10, max_value=1e10),
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e10, max_value=1e10),
    st.text(max_size=1000),
)

# Recursive JSON structures
json_values = st.recursive(
    json_primitives,
    lambda children: st.one_of(
        st.lists(children, max_size=10),
        st.dictionaries(st.text(min_size=1, max_size=50), children, max_size=10),
    ),
    max_leaves=20,
)


# =============================================================================
# Property 1: Serialization Round-Trip
# =============================================================================

@given(data=st.dictionaries(st.text(min_size=1, max_size=50), json_values, max_size=20))
def test_property_serialization_roundtrip(data):
    """
    Property 1: Serialization Round-Trip
    
    For any valid data dict, serialize → deserialize SHALL produce equivalent object.
    """
    # Serialize
    serialized = SafeSerializer.serialize(data)
    assert isinstance(serialized, bytes)
    
    # Deserialize
    restored = SafeSerializer.deserialize(serialized)
    
    # Check equivalence
    assert restored == data


@given(data=st.dictionaries(st.text(min_size=1, max_size=50), json_values, max_size=20))
def test_property_file_roundtrip(data):
    """
    Property: File save/load round-trip preserves data.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.json"
        
        # Save
        SafeSerializer.save(data, path)
        assert path.exists()
        
        # Load
        restored = SafeSerializer.load(path)
        
        # Check equivalence
        assert restored == data


def test_property_pickle_rejection():
    """
    Property: Pickle files SHALL be rejected with clear error.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        pickle_path = Path(tmpdir) / "test.pkl"
        pickle_path.write_bytes(b"fake pickle data")
        
        with pytest.raises(SerializationError) as exc_info:
            SafeSerializer.load(pickle_path)
        
        assert "pickle" in str(exc_info.value).lower()
        assert "security" in str(exc_info.value).lower()


@given(data=st.dictionaries(st.text(min_size=1, max_size=50), json_values, max_size=20))
def test_property_hash_deterministic(data):
    """
    Property: Hash of same data SHALL be deterministic.
    """
    hash1 = SafeSerializer.compute_hash(data)
    hash2 = SafeSerializer.compute_hash(data)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex


@given(
    data1=st.dictionaries(st.text(min_size=1, max_size=50), json_values, max_size=10),
    data2=st.dictionaries(st.text(min_size=1, max_size=50), json_values, max_size=10),
)
def test_property_different_data_different_hash(data1, data2):
    """
    Property: Different data SHALL produce different hashes (with high probability).
    """
    if data1 == data2:
        return  # Skip if randomly same
    
    hash1 = SafeSerializer.compute_hash(data1)
    hash2 = SafeSerializer.compute_hash(data2)
    
    assert hash1 != hash2
