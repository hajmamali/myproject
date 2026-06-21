"""
Portable Path Management
========================
Provides safe, portable path resolution using environment variables
with repo-relative defaults. NO hardcoded absolute paths.

Environment Variables:
- MAHOUN_MODEL_DIR: Directory containing LLM models
- MAHOUN_DATA_DIR: Directory for input data
- MAHOUN_OUTPUT_DIR: Directory for outputs
- MAHOUN_CACHE_DIR: Directory for caches (optional)
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Repository Root Detection
# ============================================================================

def get_repo_root() -> Path:
    """
    Get repository root directory.
    
    Returns:
        Path: Absolute path to repository root
    """
    # Start from this file's location and walk up to find repo root
    current = Path(__file__).resolve()
    
    # Walk up until we find .git or reach filesystem root
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
        # Also check for pyproject.toml or setup.py as fallback
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent
    
    # If nothing found, assume 2 levels up from this file (mahoun/core/paths.py)
    return current.parents[1]


# ============================================================================
# Environment-Based Path Resolution
# ============================================================================

def get_model_dir() -> Path:
    """
    Get model directory from environment or default.
    
    Environment: MAHOUN_MODEL_DIR
    Default: <repo_root>/models
    
    Returns:
        Path: Absolute path to model directory
    """
    env_path = os.getenv("MAHOUN_MODEL_DIR")
    
    if env_path:
        path = Path(env_path).expanduser().resolve()
        logger.debug(f"Using MAHOUN_MODEL_DIR from environment: {path}")
        return path
    
    # Default: repo_root/models
    repo_root = get_repo_root()
    default_path = repo_root / "models"
    logger.debug(f"Using default model directory: {default_path}")
    return default_path


def get_data_dir() -> Path:
    """
    Get data directory from environment or default.
    
    Environment: MAHOUN_DATA_DIR
    Default: <repo_root>/data
    
    Returns:
        Path: Absolute path to data directory
    """
    env_path = os.getenv("MAHOUN_DATA_DIR")
    
    if env_path:
        path = Path(env_path).expanduser().resolve()
        logger.debug(f"Using MAHOUN_DATA_DIR from environment: {path}")
        return path
    
    # Default: repo_root/data
    repo_root = get_repo_root()
    default_path = repo_root / "data"
    logger.debug(f"Using default data directory: {default_path}")
    return default_path


def get_output_dir() -> Path:
    """
    Get output directory from environment or default.
    
    Environment: MAHOUN_OUTPUT_DIR
    Default: <repo_root>/output
    
    Returns:
        Path: Absolute path to output directory
    """
    env_path = os.getenv("MAHOUN_OUTPUT_DIR")
    
    if env_path:
        path = Path(env_path).expanduser().resolve()
        logger.debug(f"Using MAHOUN_OUTPUT_DIR from environment: {path}")
        return path
    
    # Default: repo_root/output
    repo_root = get_repo_root()
    default_path = repo_root / "output"
    logger.debug(f"Using default output directory: {default_path}")
    return default_path


def get_cache_dir() -> Path:
    """
    Get cache directory from environment or default.
    
    Environment: MAHOUN_CACHE_DIR
    Default: <repo_root>/.cache
    
    Returns:
        Path: Absolute path to cache directory
    """
    env_path = os.getenv("MAHOUN_CACHE_DIR")
    
    if env_path:
        path = Path(env_path).expanduser().resolve()
        logger.debug(f"Using MAHOUN_CACHE_DIR from environment: {path}")
        return path
    
    # Default: repo_root/.cache
    repo_root = get_repo_root()
    default_path = repo_root / ".cache"
    logger.debug(f"Using default cache directory: {default_path}")
    return default_path


# ============================================================================
# Safe Path Utilities
# ============================================================================

def ensure_dir(path: Path) -> Path:
    """
    Ensure directory exists (create if needed).
    
    Args:
        path: Directory path to ensure
        
    Returns:
        Path: Absolute path to directory
    """
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_path(path_str: str, base_dir: Optional[Path] = None) -> Path:
    """
    Resolve a path string to absolute path.
    
    Args:
        path_str: Path string (can be relative or absolute)
        base_dir: Base directory for relative paths (default: repo root)
        
    Returns:
        Path: Absolute resolved path
    """
    path = Path(path_str).expanduser()
    
    if path.is_absolute():
        return path.resolve()
    
    # Relative path - resolve against base_dir
    if base_dir is None:
        base_dir = get_repo_root()
    
    return (base_dir / path).resolve()


# ============================================================================
# Path Validation
# ============================================================================

def validate_model_path(model_path: Path, model_name: Optional[str] = None) -> bool:
    """
    Validate that a model path exists.
    
    Args:
        model_path: Path to model file or directory
        model_name: Optional specific model file name
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not model_path.exists():
        return False
    
    if model_name and model_path.is_dir():
        # Check if specific model file exists in directory
        model_file = model_path / model_name
        return model_file.exists()
    
    return True


def get_safe_model_path(model_name: str, raise_on_missing: bool = False) -> Optional[Path]:
    """
    Get safe model path with existence check.
    
    Args:
        model_name: Name of model file or directory
        raise_on_missing: If True, raise FileNotFoundError when missing
        
    Returns:
        Optional[Path]: Path to model if exists, None otherwise
        
    Raises:
        FileNotFoundError: If raise_on_missing=True and model not found
    """
    model_dir = get_model_dir()
    model_path = model_dir / model_name
    
    if not model_path.exists():
        if raise_on_missing:
            raise FileNotFoundError(
                f"Model not found: {model_name}\n"
                f"Searched in: {model_dir}\n"
                f"Set MAHOUN_MODEL_DIR environment variable to specify custom location"
            )
        return None
    
    return model_path


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "get_repo_root",
    "get_model_dir",
    "get_data_dir",
    "get_output_dir",
    "get_cache_dir",
    "ensure_dir",
    "resolve_path",
    "validate_model_path",
    "get_safe_model_path",
]
