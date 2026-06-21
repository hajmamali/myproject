"""
API Module
==========

REST API for MAHOUN self-improvement system.
"""

# Lazy import to avoid heavy dependencies at module import time
# The actual app is in api.main, not self_improve.api.main
def __getattr__(name):
    """Lazy loading to avoid import-time side effects"""
    if name == "app":
        try:
            # Try importing from self_improve if available
            from mahoun.self_improve.api.main import app
            return app
        except ImportError:
            # Fallback: use the local api.main
            from api.main import app
            return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["app"]
