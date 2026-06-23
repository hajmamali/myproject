# Minimal shim for filelock.FileLock used in tests/environment
# Provides a simple process-local lock to satisfy ImmutableLedger usage in tests.

import threading

class FileLock:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self.path = path

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._lock.release()

    def acquire(self, timeout=None):
        return self._lock.acquire(timeout=timeout) if timeout is not None else self._lock.acquire()

    def release(self):
        return self._lock.release()
