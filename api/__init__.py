"""
API Module
==========

REST API for MAHOUN legal reasoning system.
"""

# Lazy import to avoid heavy dependencies at module import time
def __getattr__(name):
    """Lazy loading to avoid import-time side effects"""
    if name == "app":
        from api.main import app
        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["app"]
