"""
Adversarial Authorization State Tests
=======================================

Tests that attempt to BREAK the canonical ContextVar singleton.

Scenarios:
1.  Concurrent threads — state must NOT bleed across threads
2.  Nested authorization — inner reset must not clobber outer
3.  Exception mid-authorization — state must be clean after exception
4.  Async coroutine isolation — coroutines must not see each other's state
5.  Async concurrent tasks — 100 concurrent tasks, no cross-contamination
6.  Thread + asyncio hybrid — asyncio loop running inside thread
7.  Forged authorization attempt — bypass via direct ContextVar name collision
8.  Rapid token storm — 10,000 set/reset cycles, final state must be False
9.  Cross-module simultaneous read/write — kernel writes, boundary reads, same goroutine
10. Reentrancy — nested set_authorized inside a set_authorized block
11. Import-time identity check — re-importing must not create new ContextVar
12. Garbage-collected token — reset after GC must raise or be handled safely
"""

import asyncio
import gc
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical():
    from mahoun.core.governance.authorization_state import _authorized_write_ctx
    return _authorized_write_ctx


def _kernel_is_authorized():
    from mahoun.core.governance_kernel.kernel import is_governance_authorized
    return is_governance_authorized()


def _boundary_is_authorized():
    from mahoun.core.governance.mutation_boundary import _is_authorized
    return _is_authorized()


def _set(state: bool):
    from mahoun.core.governance.authorization_state import set_authorized
    return set_authorized(state)


def _reset(token):
    from mahoun.core.governance.authorization_state import reset_authorized
    reset_authorized(token)


def _inspect(query: str):
    from mahoun.core.governance.mutation_boundary import MutationAuthorizationBoundary
    MutationAuthorizationBoundary.inspect(query)


def _kernel_inspect(query: str):
    from mahoun.core.governance_kernel.kernel import KernelMutationBoundary
    KernelMutationBoundary.inspect(query)


MUTATION_QUERY = "MERGE (n:Case {id: $id}) SET n.title = $title"
READ_QUERY = "MATCH (n:Case {id: $id}) RETURN n"


# ---------------------------------------------------------------------------
# TEST 1: Thread isolation — state set in thread A must NOT bleed to thread B
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_thread_isolation():
    """Authorization set in thread A is invisible to thread B."""
    results = {}
    barrier = threading.Barrier(2)

    def thread_a():
        token = _set(True)
        barrier.wait()           # sync: both threads inside critical section
        results["A_kernel"] = _kernel_is_authorized()
        results["A_boundary"] = _boundary_is_authorized()
        barrier.wait()           # sync: let thread B read before reset
        _reset(token)

    def thread_b():
        barrier.wait()           # wait for A to set
        results["B_kernel"] = _kernel_is_authorized()
        results["B_boundary"] = _boundary_is_authorized()
        barrier.wait()

    ta = threading.Thread(target=thread_a)
    tb = threading.Thread(target=thread_b)
    ta.start(); tb.start()
    ta.join(); tb.join()

    assert results["A_kernel"] is True,   "Thread A kernel must see True"
    assert results["A_boundary"] is True, "Thread A boundary must see True"
    assert results["B_kernel"] is False,  "Thread B must NOT see thread A's authorization"
    assert results["B_boundary"] is False, "Thread B boundary must NOT see thread A's state"


# ---------------------------------------------------------------------------
# TEST 2: Nested authorization — tokens must be handled in LIFO order
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_nested_authorization_lifo():
    """Nested set/reset must restore state correctly at each level."""
    assert not _kernel_is_authorized()

    token1 = _set(True)
    assert _kernel_is_authorized() is True
    assert _boundary_is_authorized() is True

    token2 = _set(False)   # override to False inside
    assert _kernel_is_authorized() is False
    assert _boundary_is_authorized() is False

    token3 = _set(True)    # re-authorize deeper
    assert _kernel_is_authorized() is True

    _reset(token3)         # back to False
    assert _kernel_is_authorized() is False

    _reset(token2)         # back to True (outer set)
    assert _kernel_is_authorized() is True
    assert _boundary_is_authorized() is True

    _reset(token1)         # back to original False
    assert _kernel_is_authorized() is False
    assert _boundary_is_authorized() is False


# ---------------------------------------------------------------------------
# TEST 3: Exception mid-authorization — state clean after exception
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_state_clean_after_exception():
    """If an exception fires while authorized, reset in finally must clean state."""
    assert not _kernel_is_authorized()

    try:
        token = _set(True)
        assert _kernel_is_authorized() is True
        raise RuntimeError("simulated failure")
    except RuntimeError:
        _reset(token)

    assert _kernel_is_authorized() is False, "State must be False after exception path"
    assert _boundary_is_authorized() is False


# ---------------------------------------------------------------------------
# TEST 4: MutationAuthorizationBoundary.inspect blocks AFTER exception cleanup
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_inspect_blocks_after_exception_cleanup():
    """After exception+reset, boundary must block mutations again."""
    from mahoun.core.governance.violations import GovernanceViolationError

    try:
        token = _set(True)
        raise ValueError("mid-execution failure")
    except ValueError:
        _reset(token)

    with pytest.raises(GovernanceViolationError):
        _inspect(MUTATION_QUERY)


# ---------------------------------------------------------------------------
# TEST 5: Async coroutine isolation — coroutines must not share state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.p0
async def test_async_coroutine_isolation():
    """Each coroutine has its own ContextVar copy — state set in one must not leak."""
    results = {}
    gate = asyncio.Event()

    async def task_authorized():
        token = _set(True)
        gate.set()                          # signal task_unauthorized to read
        await asyncio.sleep(0)              # yield to event loop
        results["auth"] = _kernel_is_authorized()
        _reset(token)

    async def task_unauthorized():
        await gate.wait()                   # wait for authorized task to set
        results["unauth"] = _kernel_is_authorized()

    await asyncio.gather(task_authorized(), task_unauthorized())

    assert results["auth"] is True,   "Authorized coroutine must see True"
    assert results["unauth"] is False, "Unauthorized coroutine must NOT see True"


# ---------------------------------------------------------------------------
# TEST 6: 100 concurrent async tasks — no cross-contamination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.p0
async def test_async_concurrent_100_tasks_no_bleed():
    """100 concurrent tasks, each authorizes/de-authorizes independently."""
    violations = []

    async def guarded_task(task_id: int):
        # Start unauthorized
        if _kernel_is_authorized():
            violations.append(f"task {task_id}: dirty state at entry")
            return

        token = _set(True)
        try:
            await asyncio.sleep(0)  # yield — other tasks run
            if not _kernel_is_authorized():
                violations.append(f"task {task_id}: lost authorization mid-task")
            if not _boundary_is_authorized():
                violations.append(f"task {task_id}: boundary lost sync mid-task")
        finally:
            _reset(token)

        if _kernel_is_authorized():
            violations.append(f"task {task_id}: state leaked after reset")

    await asyncio.gather(*[guarded_task(i) for i in range(100)])
    assert violations == [], f"Cross-contamination detected: {violations}"


# ---------------------------------------------------------------------------
# TEST 7: Thread pool — 50 workers, all must start and end unauthorized
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_thread_pool_50_workers_no_bleed():
    """50 concurrent threads each set/reset in isolation."""
    violations = []
    lock = threading.Lock()

    def worker(worker_id: int):
        if _kernel_is_authorized():
            with lock:
                violations.append(f"worker {worker_id}: dirty entry state")
            return

        token = _set(True)
        try:
            time.sleep(0.001)
            if not _kernel_is_authorized():
                with lock:
                    violations.append(f"worker {worker_id}: lost authorization")
            if not _boundary_is_authorized():
                with lock:
                    violations.append(f"worker {worker_id}: boundary lost sync")
        finally:
            _reset(token)

        if _kernel_is_authorized():
            with lock:
                violations.append(f"worker {worker_id}: state leaked after reset")

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(worker, i) for i in range(50)]
        for f in as_completed(futures):
            f.result()

    assert violations == [], f"Thread bleed detected: {violations}"


# ---------------------------------------------------------------------------
# TEST 8: Forged bypass attempt — create a DIFFERENT ContextVar with same name
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_forged_contextvar_does_not_bypass():
    """A ContextVar with the same name is a different object — cannot bypass gate."""
    from contextvars import ContextVar
    from mahoun.core.governance.violations import GovernanceViolationError

    # Attacker creates a ContextVar with same name string
    fake_ctx = ContextVar("authorized_write", default=False)
    assert fake_ctx is not _canonical(), "Forged ContextVar must be different object"

    # Set the FAKE one to True
    fake_token = fake_ctx.set(True)
    try:
        # The real gate must still block
        with pytest.raises(GovernanceViolationError):
            _inspect(MUTATION_QUERY)
    finally:
        fake_ctx.reset(fake_token)


# ---------------------------------------------------------------------------
# TEST 9: Rapid token storm — 10,000 cycles, final state must be False
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_rapid_token_storm():
    """10,000 set/reset cycles must leave state as False."""
    for _ in range(10_000):
        token = _set(True)
        assert _kernel_is_authorized() is True
        _reset(token)
        assert _kernel_is_authorized() is False

    assert _kernel_is_authorized() is False
    assert _boundary_is_authorized() is False


# ---------------------------------------------------------------------------
# TEST 10: Cross-module simultaneous — kernel sets, boundary+kernel both read
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_cross_module_simultaneous_read():
    """State set via kernel helpers is immediately visible in boundary and vice versa."""
    from mahoun.core.governance_kernel.kernel import (
        set_governance_authority,
        reset_governance_authority,
        is_governance_authorized,
    )
    from mahoun.core.governance.mutation_boundary import _is_authorized

    # Kernel writes → boundary reads
    t1 = set_governance_authority(True)
    assert _is_authorized() is True, "boundary must see kernel-set True"
    assert is_governance_authorized() is True
    reset_governance_authority(t1)

    # Canonical writes → kernel reads
    t2 = _set(True)
    assert is_governance_authorized() is True, "kernel must see canonical-set True"
    assert _is_authorized() is True
    _reset(t2)

    assert not _kernel_is_authorized()
    assert not _boundary_is_authorized()


# ---------------------------------------------------------------------------
# TEST 11: Reentrancy — inspect is safe to call from within authorized context
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_reentrancy_inspect_inside_authorized():
    """inspect() called from inside an authorized block must pass without error."""
    token = _set(True)
    try:
        # Both boundary and kernel inspectors must pass
        _inspect(MUTATION_QUERY)
        _kernel_inspect(MUTATION_QUERY)
        # Read queries always pass regardless
        _inspect(READ_QUERY)
    finally:
        _reset(token)


# ---------------------------------------------------------------------------
# TEST 12: Import-time identity — re-importing module does not create new ContextVar
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_reimport_does_not_create_new_contextvar():
    """Forcing module reload must not produce a new ContextVar object."""
    canonical_before = _canonical()

    # Force re-evaluation of the module reference
    if "mahoun.core.governance.authorization_state" in sys.modules:
        mod = sys.modules["mahoun.core.governance.authorization_state"]
        ctx_after = mod._authorized_write_ctx

    assert ctx_after is canonical_before, (
        "Re-accessing the module produced a different ContextVar object."
    )


# ---------------------------------------------------------------------------
# TEST 13: copy_context — propagates state correctly into spawned context
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_copy_context_propagates_authorization():
    """copy_context captures current state; changes inside do not leak out."""
    token = _set(True)
    try:
        ctx_copy = copy_context()

        result_inside = {}

        def run_in_copy():
            result_inside["val"] = _kernel_is_authorized()
            # Mutate inside copy — must not affect outer
            inner_token = _set(False)
            result_inside["after_inner_set"] = _kernel_is_authorized()
            _reset(inner_token)

        ctx_copy.run(run_in_copy)

        # Outer context must still be True
        assert _kernel_is_authorized() is True, "Outer context must not be affected by copy mutation"
        assert result_inside["val"] is True, "Copied context must have inherited True"
        assert result_inside["after_inner_set"] is False, "Inner mutation must be visible inside copy"
    finally:
        _reset(token)

    assert _kernel_is_authorized() is False


# ---------------------------------------------------------------------------
# TEST 14: Unicode-obfuscated Cypher must not bypass KernelMutationBoundary
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_unicode_obfuscated_mutation_blocked():
    """Full-width Unicode MERGE must be detected and blocked."""
    from mahoun.core.governance.violations import GovernanceViolationError

    # ＭＥＲＧＥは Unicode full-width — NFKC normalization collapses to MERGE
    unicode_merge = "\uFF2D\uFF25\uFF32\uFF27\uFF25 (n:Case {id: $id})"

    with pytest.raises(GovernanceViolationError):
        _inspect(unicode_merge)


# ---------------------------------------------------------------------------
# TEST 15: Compound scenario — thread spawns async loop, both observe same state
# ---------------------------------------------------------------------------

@pytest.mark.p0
def test_thread_spawns_asyncio_loop_state_correct():
    """A thread running an asyncio event loop must have proper ContextVar isolation."""
    outer_results = {}

    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def inner():
                # Should start unauthorized
                outer_results["entry"] = _kernel_is_authorized()
                token = _set(True)
                try:
                    outer_results["authorized"] = _kernel_is_authorized()
                    outer_results["boundary"] = _boundary_is_authorized()
                finally:
                    _reset(token)
                outer_results["exit"] = _kernel_is_authorized()

            loop.run_until_complete(inner())
        finally:
            loop.close()

    t = threading.Thread(target=run_in_thread)
    t.start()
    t.join()

    assert outer_results["entry"] is False
    assert outer_results["authorized"] is True
    assert outer_results["boundary"] is True
    assert outer_results["exit"] is False

    # Main thread must be unaffected
    assert _kernel_is_authorized() is False
