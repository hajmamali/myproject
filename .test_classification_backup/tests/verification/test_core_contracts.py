"""
File 1 / Class A — Core Contracts.

Verifies the public API surface of ``mahoun.core`` primitives that all
other subsystems rely on:

    * ``mahoun.core.exceptions``   — MahounError hierarchy.
    * ``mahoun.core.singleton``    — ThreadSafeSingleton.
    * ``mahoun.core.uid_generator``— deterministic UUID v5.
    * ``mahoun.core.serialization``— SafeSerializer (no pickle).

Tests are contract-level. They must survive additive changes but detect
renames, deletions, and semantic regressions.
"""

from __future__ import annotations

import threading
import uuid

import pytest


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

@pytest.mark.p2
def test_mahoun_error_is_root_exception(safe_import):
    exc = safe_import("mahoun.core.exceptions")
    assert issubclass(exc.MahounError, Exception)
    assert exc.MahounError.error_code == "MAHOUN_ERROR"


@pytest.mark.parametrize(
    "name",
    [
        "SerializationError",
        "LedgerError",
        "LedgerIntegrityError",
        "KnowledgeGraphError",
        "ConfigurationError",
        "ValidationError",
        "ReasoningError",
        "InvariantViolationError",
        "GovernanceError",
    ],
)
@pytest.mark.p2
def test_exception_subclasses_are_mahoun_errors(safe_import, name):
    exc = safe_import("mahoun.core.exceptions")
    cls = getattr(exc, name)
    assert issubclass(cls, exc.MahounError), f"{name} must inherit MahounError"
    assert isinstance(cls.error_code, str) and cls.error_code


@pytest.mark.p2
def test_mahoun_error_to_dict_shape(safe_import):
    exc = safe_import("mahoun.core.exceptions")
    e = exc.MahounError("boom", details={"k": 1})
    d = e.to_dict()
    assert set(d) >= {"error_code", "message", "details"}
    assert d["message"] == "boom"
    assert d["details"] == {"k": 1}


@pytest.mark.p2
def test_unsafe_serialization_error_is_serialization_error(safe_import):
    exc = safe_import("mahoun.core.exceptions")
    assert issubclass(exc.UnsafeSerializationError, exc.SerializationError)


# ---------------------------------------------------------------------------
# Singleton contract
# ---------------------------------------------------------------------------

@pytest.mark.p2
def test_singleton_returns_same_instance(safe_import):
    mod = safe_import("mahoun.core.singleton")
    s = mod.ThreadSafeSingleton(name="unit")
    a = s.get_instance(lambda: object())
    b = s.get_instance(lambda: object())
    assert a is b, "singleton must return the same instance"


@pytest.mark.p2
def test_singleton_reset_creates_new_instance(safe_import):
    mod = safe_import("mahoun.core.singleton")
    s = mod.ThreadSafeSingleton()
    a = s.get_instance(lambda: object())
    s.reset()
    b = s.get_instance(lambda: object())
    assert a is not b
    assert s.is_initialized()


@pytest.mark.p2
def test_singleton_is_thread_safe(safe_import):
    mod = safe_import("mahoun.core.singleton")
    s = mod.ThreadSafeSingleton()
    results = []

    def make():
        results.append(s.get_instance(lambda: object()))

    threads = [threading.Thread(target=make) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len({id(r) for r in results}) == 1, "concurrent get_instance must not race"


# ---------------------------------------------------------------------------
# UID generator contract
# ---------------------------------------------------------------------------

@pytest.mark.p2
def test_uid_is_deterministic(safe_import):
    mod = safe_import("mahoun.core.uid_generator")
    a = mod.UIDGenerator.generate_deterministic("NS", "abc")
    b = mod.UIDGenerator.generate_deterministic("NS", "abc")
    assert a == b, "same inputs must yield same UUID"


@pytest.mark.p2
def test_uid_is_a_valid_uuid_v5(safe_import):
    mod = safe_import("mahoun.core.uid_generator")
    s = mod.UIDGenerator.generate_entity_id("person", "Alice")
    parsed = uuid.UUID(s)
    assert parsed.version == 5


@pytest.mark.p2
def test_uid_differs_across_namespaces(safe_import):
    mod = safe_import("mahoun.core.uid_generator")
    a = mod.UIDGenerator.generate_entity_id("person", "Alice")
    b = mod.UIDGenerator.generate_entity_id("organization", "Alice")
    assert a != b, "namespace must participate in the hash"


@pytest.mark.p2
def test_uid_document_helper_stable(safe_import):
    mod = safe_import("mahoun.core.uid_generator")
    assert mod.generate_document_id("h1") == mod.generate_document_id("h1")
    assert mod.generate_document_id("h1") != mod.generate_document_id("h2")


# ---------------------------------------------------------------------------
# Safe serialization contract
# ---------------------------------------------------------------------------

@pytest.mark.p2
def test_serializer_round_trip(safe_import):
    mod = safe_import("mahoun.core.serialization")
    data = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
    blob = mod.SafeSerializer.serialize(data)
    assert isinstance(blob, (bytes, bytearray))
    restored = mod.SafeSerializer.deserialize(blob)
    assert restored == data


@pytest.mark.p2
def test_serializer_rejects_non_serializable(safe_import):
    mod = safe_import("mahoun.core.serialization")

    class NoDict:
        __slots__ = ("x",)
        def __init__(self): self.x = 1

    with pytest.raises(mod.SerializationError):
        mod.SafeSerializer.serialize({"bad": NoDict()})


@pytest.mark.p2
def test_serializer_deserialize_rejects_garbage(safe_import):
    mod = safe_import("mahoun.core.serialization")
    with pytest.raises(mod.SerializationError):
        mod.SafeSerializer.deserialize(b"\x00\x01\x02not-json")
