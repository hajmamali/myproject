"""
Safe Serialization Module
=========================
Provides secure serialization using JSON format.

SECURITY: NO pickle, NO eval, NO exec.
All serialization uses JSON which cannot execute arbitrary code.
"""

from typing import Any, Dict, TypeVar, Type, Union, List
from pathlib import Path
from datetime import datetime, date
import json
import hashlib
import logging
import numpy as np

logger = logging.getLogger(__name__)


class SerializationError(Exception):
    """Error during serialization/deserialization."""


def _json_encoder(obj: Any) -> Any:
    """
    Custom JSON encoder for complex types.
    
    Handles:
    - datetime/date objects
    - numpy arrays and scalars
    - Path objects
    - Sets (converted to lists)
    - Objects with __dict__
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.bool_):
        return bool(obj)
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class SafeSerializer:
    """
    Safe serialization using JSON format.
    
    SECURITY GUARANTEES:
    - NO pickle usage (prevents arbitrary code execution)
    - NO eval/exec (prevents code injection)
    - Only JSON-safe primitives are serialized
    
    Usage:
        # Serialize to bytes
        data = {"key": "value", "numbers": [1, 2, 3]}
        serialized = SafeSerializer.serialize(data)
        
        # Deserialize from bytes
        restored = SafeSerializer.deserialize(serialized)
        
        # Save to file
        SafeSerializer.save(data, Path("data.json"))
        
        # Load from file
        loaded = SafeSerializer.load(Path("data.json"))
    """
    
    @staticmethod
    def serialize(data: Dict[str, Any]) -> bytes:
        """
        Serialize data to JSON bytes.
        
        Args:
            data: Dictionary with JSON-serializable values
            
        Returns:
            UTF-8 encoded JSON bytes
            
        Raises:
            SerializationError: If data cannot be serialized
        """
        try:
            json_str = json.dumps(
                data, 
                default=_json_encoder, 
                ensure_ascii=False,
                separators=(',', ':')  # Compact format
            )
            return json_str.encode('utf-8')
        except (TypeError, ValueError) as e:
            raise SerializationError(f"Failed to serialize data: {e}") from e
    
    @staticmethod
    def deserialize(data: bytes) -> Dict[str, Any]:
        """
        Deserialize JSON bytes to dict.
        
        Args:
            data: UTF-8 encoded JSON bytes
            
        Returns:
            Deserialized dictionary
            
        Raises:
            SerializationError: If data cannot be deserialized
        """
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise SerializationError(f"Failed to deserialize data: {e}") from e
    
    @staticmethod
    def save(data: Dict[str, Any], path: Path, pretty: bool = True) -> None:
        """
        Save data to JSON file.
        
        Args:
            data: Dictionary with JSON-serializable values
            path: Path to save file
            pretty: If True, format with indentation (default True)
            
        Raises:
            SerializationError: If save fails
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(
                    data, 
                    f, 
                    default=_json_encoder, 
                    ensure_ascii=False,
                    indent=2 if pretty else None
                )
            logger.debug(f"Saved data to {path}")
        except (TypeError, ValueError, OSError) as e:
            raise SerializationError(f"Failed to save to {path}: {e}") from e
    
    @staticmethod
    def load(path: Path) -> Dict[str, Any]:
        """
        Load data from JSON file.
        
        SECURITY: Refuses to load pickle files.
        
        Args:
            path: Path to JSON file
            
        Returns:
            Loaded dictionary
            
        Raises:
            SerializationError: If load fails or file is pickle
        """
        # Security check: refuse pickle files
        if path.suffix.lower() in ('.pkl', '.pickle'):
            logger.warning(f"SECURITY: Refused to load pickle file: {path}")
            raise SerializationError(
                f"Pickle files not supported for security reasons: {path}. "
                f"Use JSON format instead."
            )
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Loaded data from {path}")
            return data
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise SerializationError(f"Failed to load from {path}: {e}") from e
        except FileNotFoundError:
            raise SerializationError(f"File not found: {path}")
        except OSError as e:
            raise SerializationError(f"Failed to read {path}: {e}") from e
    
    @staticmethod
    def compute_hash(data: Dict[str, Any]) -> str:
        """
        Compute SHA-256 hash of serialized data.
        
        Useful for integrity verification.
        
        Args:
            data: Dictionary to hash
            
        Returns:
            Hex-encoded SHA-256 hash
        """
        # Use sorted keys for deterministic hashing
        json_str = json.dumps(data, default=_json_encoder, sort_keys=True)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


class NumpyArraySerializer:
    """
    Specialized serializer for numpy arrays.
    
    Converts numpy arrays to/from JSON-safe format while preserving:
    - Shape
    - Dtype
    - Data values
    """
    
    @staticmethod
    def to_dict(arr: np.ndarray) -> Dict[str, Any]:
        """Convert numpy array to JSON-safe dict."""
        return {
            "__numpy_array__": True,
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
            "data": arr.tolist()
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> np.ndarray:
        """Restore numpy array from dict."""
        if not d.get("__numpy_array__"):
            raise ValueError("Not a numpy array dict")
        return np.array(d["data"], dtype=d["dtype"]).reshape(d["shape"])
    
    @staticmethod
    def is_numpy_dict(d: Any) -> bool:
        """Check if dict represents a numpy array."""
        return isinstance(d, dict) and d.get("__numpy_array__") is True


def migrate_pickle_to_json(pickle_path: Path, json_path: Path) -> bool:
    """
    Migrate a pickle file to JSON format.
    
    ⚠️ **SECURITY WARNING** ⚠️
    This function uses pickle.load() which is UNSAFE for untrusted data.
    pickle can execute arbitrary code during deserialization.
    
    **ONLY USE THIS FUNCTION IF:**
    - You created the pickle file yourself
    - The pickle file is from a trusted source
    - You are performing a one-time migration to JSON format
    
    **DO NOT USE IN PRODUCTION for user-supplied files.**
    
    For new code, always use SafeSerializer with JSON format instead.
    
    Args:
        pickle_path: Path to existing pickle file (TRUSTED SOURCE ONLY)
        json_path: Path for new JSON file
        
    Returns:
        True if migration successful, False otherwise
    """
    import pickle
    
    # SECURITY: Log warning for audit trail
    logger.warning(
        f"⚠️ SECURITY: Loading pickle file {pickle_path} for migration. "
        f"This operation uses pickle.load() which can execute arbitrary code. "
        f"Ensure this file is from a trusted source."
    )
    
    try:
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
        
        # Convert numpy arrays
        def convert_numpy(obj: Any) -> Any:
            if isinstance(obj, np.ndarray):
                return NumpyArraySerializer.to_dict(obj)
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_numpy(v) for v in obj]
            return obj
        
        converted = convert_numpy(data)
        SafeSerializer.save(converted, json_path)
        
        logger.info(f"MIGRATION: Successfully migrated {pickle_path} -> {json_path}")
        return True
        
    except Exception as e:
        logger.error(f"MIGRATION FAILED: {e}")
        return False
