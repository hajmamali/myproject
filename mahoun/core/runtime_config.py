"""
MAHOUN Runtime Configuration
=============================
Lightweight, import-safe runtime configuration for MAHOUN system.

This module provides mode-aware settings that control heavy operations
like Graph processing, LoRA training, and model backends.

Modes:
- desktop_minimal: CPU-only, minimal resource usage, remote/lightweight backends
- server_full: Full feature set, local GPU, all capabilities enabled

Environment Variables:
- MAHOUN_MODE: "desktop_minimal" | "server_full" (default: server_full)
- MAHOUN_GRAPH_ENABLED: Enable/disable graph operations (bool)
- MAHOUN_GRAPH_BACKEND: "disabled_fallback" | "local_small" | "local_full" | "remote"
- MAHOUN_LORA_TRAINING_ENABLED: Enable/disable LoRA training (bool)
- MAHOUN_LORA_INFERENCE_BACKEND: "remote" | "local_cpu_small" | "local_gpu"
- MAHOUN_LLM_BACKEND: "openai" | "local_cpu_small" | "local_gpu"
- MAHOUN_EMBEDDING_BACKEND: Backend for embeddings (e.g., "bge-small")
- MAHOUN_EMBEDDING_MODEL_PATH: Path to local embedding model (optional)
- MAHOUN_LLM_MODEL_PATH: Path to local LLM model (optional)
"""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MahounRuntimeSettings:
    """
    Immutable runtime settings for MAHOUN system.
    
    These settings control which heavy operations are enabled and
    which backends are used for various components.
    """
    mode: str
    graph_enabled: bool
    graph_backend: str  # "disabled_fallback" | "local_small" | "local_full" | "remote"
    lora_training_enabled: bool
    lora_inference_backend: str  # "remote" | "local_cpu_small" | "local_gpu"
    llm_backend: str  # "openai" | "local_cpu_small" | "local_gpu"
    embedding_backend: str  # e.g., "bge-small", "bge-default"
    embedding_model_path: str  # Optional: filesystem path to local embedding model
    llm_model_path: str  # Optional: filesystem path to local LLM model
    # Graph Enterprise Settings (from YAML)
    graph_neo4j_uri: str = "bolt://localhost:7687"
    graph_neo4j_user: str = "neo4j"
    graph_neo4j_password: str = ""
    graph_gat_checkpoint: str = "models/graph/gat_v1.pt"
    graph_mode: str = "read_write"
    retrieval_mode: str = "text_only"  # "text_only" | "hybrid_graph" | "graph_only"
    # Ollama Settings
    ollama_uri: str = "http://localhost:11434"
    ollama_model: str = "alkindivv/qwen2.5-id-legal-q4km:latest"
    # Optional Component Flags (for Desktop/Dev mode)
    enable_ollama: bool = False
    enable_postgres: bool = False
    enable_redis: bool = False
    enable_gaussian_process: bool = False


def _env_bool(name: str, default: bool) -> bool:
    """
    Parse environment variable as boolean.
    
    Recognizes: 1, true, yes, on (case-insensitive) as True.
    All other values or absence defaults to the provided default.
    """
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _load_yaml_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML config file (defaults to configs/runtime_profile.yaml)
    
    Returns:
        Dictionary with config values (empty dict if file not found or YAML unavailable)
    
    Environment Variables:
        MAHOUN_CONFIG_PATH: Override config file path
        MAHOUN_MODE: If "desktop_minimal", uses runtime_profile_desktop.yaml
    """
    if config_path is None:
        # Check for environment variable override
        env_config_path = os.getenv("MAHOUN_CONFIG_PATH")
        if env_config_path:
            config_path = Path(env_config_path)
        else:
            # Check MAHOUN_MODE to select appropriate config
            mode = os.getenv("MAHOUN_MODE", "")
            if mode == "desktop_minimal":
                desktop_config = Path(__file__).parent.parent / "configs" / "runtime_profile_desktop.yaml"
                if desktop_config.exists():
                    config_path = desktop_config
                else:
                    config_path = Path(__file__).parent.parent / "configs" / "runtime_profile.yaml"
            else:
                config_path = Path(__file__).parent.parent / "configs" / "runtime_profile.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        return {}
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # YAML not available, skip
        return {}
    except Exception as e:
        # Log but don't fail
        import logging
        logging.getLogger(__name__).warning(f"Failed to load YAML config: {e}")
        return {}


@lru_cache(maxsize=1)
def get_runtime_settings() -> MahounRuntimeSettings:
    """
    Get cached runtime settings based on environment variables and YAML config.
    
    Priority order:
    1. Environment variables (highest priority)
    2. YAML config file (configs/runtime_profile.yaml)
    3. Defaults
    
    This function is import-safe (no heavy dependencies) and can be
    called from any layer of the system without side effects.
    
    Returns:
        MahounRuntimeSettings: Immutable settings object
    """
    # Load YAML config (if available)
    yaml_config = _load_yaml_config()
    
    # Mode: env > yaml > default
    mode = os.getenv("MAHOUN_MODE") or yaml_config.get("mode") or "server_full"
    
    # Extract graph config from YAML
    graph_config = yaml_config.get("graph", {})
    retrieval_config = yaml_config.get("retrieval", {})
    
    # Graph settings: env > yaml > defaults
    graph_neo4j_uri = (
        os.getenv("NEO4J_URI") or 
        graph_config.get("neo4j_uri") or 
        "bolt://localhost:7687"
    )
    graph_neo4j_user = (
        os.getenv("NEO4J_USER") or 
        graph_config.get("user") or 
        "neo4j"
    )
    graph_neo4j_password = (
        os.getenv("NEO4J_PASSWORD") or 
        graph_config.get("password", "").replace("${NEO4J_PASSWORD}", os.getenv("NEO4J_PASSWORD", "")) or 
        ""
    )
    graph_gat_checkpoint = (
        os.getenv("GAT_CHECKPOINT") or 
        graph_config.get("gat_checkpoint") or 
        "models/graph/gat_v1.pt"
    )
    graph_mode = graph_config.get("mode", "read_write")
    retrieval_mode = retrieval_config.get("mode", "text_only")
    
    if mode == "desktop_minimal":
        # Desktop-Minimal mode: CPU-only, minimal resource usage
        # - Graph operations disabled by default (can be overridden)
        # - LoRA training disabled (inference may use remote API)
        # - LLM uses OpenAI API by default (or lightweight local model)
        # - Lightweight embedding model
        # - Optional components disabled by default
        return MahounRuntimeSettings(
            mode=mode,
            graph_enabled=_env_bool("MAHOUN_GRAPH_ENABLED", False),
            graph_backend=os.getenv("MAHOUN_GRAPH_BACKEND", "disabled_fallback"),
            lora_training_enabled=_env_bool("MAHOUN_LORA_TRAINING_ENABLED", False),
            lora_inference_backend=os.getenv("MAHOUN_LORA_INFERENCE_BACKEND", "remote"),
            llm_backend=os.getenv("MAHOUN_LLM_BACKEND", "openai"),
            embedding_backend=os.getenv("MAHOUN_EMBEDDING_BACKEND", "bge-small"),
            embedding_model_path=os.getenv("MAHOUN_EMBEDDING_MODEL_PATH", "models/paraphrase-multilingual-mpnet-base-277M-v2-Q8_0.gguf"),
            llm_model_path=os.getenv("MAHOUN_LLM_MODEL_PATH", ""),
            graph_neo4j_uri=graph_neo4j_uri,
            graph_neo4j_user=graph_neo4j_user,
            graph_neo4j_password=graph_neo4j_password,
            graph_gat_checkpoint=graph_gat_checkpoint,
            graph_mode=graph_mode,
            retrieval_mode=retrieval_mode,
            ollama_uri=os.getenv("MAHOUN_OLLAMA_URI", "http://localhost:11434"),
            ollama_model=os.getenv("MAHOUN_OLLAMA_MODEL", "alkindivv/qwen2.5-id-legal-q4km:latest"),
            enable_ollama=_env_bool("MAHOUN_ENABLE_OLLAMA", False),
            enable_postgres=_env_bool("MAHOUN_ENABLE_POSTGRES", False),
            enable_redis=_env_bool("MAHOUN_ENABLE_REDIS", False),
            enable_gaussian_process=_env_bool("MAHOUN_ENABLE_GAUSSIAN_PROCESS", False),
        )
    
    # Default: server_full or enterprise_graph mode - all features enabled
    # - Graph operations enabled with full local backend
    # - LoRA training enabled with local GPU
    # - Local GPU-accelerated LLM
    # - Default embedding model
    # - Optional components can be enabled via env (default: True for server mode)
    return MahounRuntimeSettings(
        mode="server_full",  # FORCED ENTERPRISE MODE
        graph_enabled=True,
        graph_backend="local_full",
        lora_training_enabled=True,
        lora_inference_backend="local_gpu",
        llm_backend="local_gpu",
        embedding_backend="bge-default",
        embedding_model_path=os.getenv("MAHOUN_EMBEDDING_MODEL_PATH", "models/paraphrase-multilingual-mpnet-base-277M-v2-Q8_0.gguf"),
        llm_model_path=os.getenv("MAHOUN_LLM_MODEL_PATH", ""),
        graph_neo4j_uri=graph_neo4j_uri,
        graph_neo4j_user=graph_neo4j_user,
        graph_neo4j_password=graph_neo4j_password,
        graph_gat_checkpoint=graph_gat_checkpoint,
        graph_mode=graph_mode,
        retrieval_mode="hybrid_graph",  # Default to hybrid graph
        ollama_uri=os.getenv("MAHOUN_OLLAMA_URI", "http://localhost:11434"),
        ollama_model=os.getenv("MAHOUN_OLLAMA_MODEL", "alkindivv/qwen2.5-id-legal-q4km:latest"),
        enable_ollama=_env_bool("MAHOUN_ENABLE_OLLAMA", True),
        enable_postgres=_env_bool("MAHOUN_ENABLE_POSTGRES", True),
        enable_redis=_env_bool("MAHOUN_ENABLE_REDIS", True),
        enable_gaussian_process=_env_bool("MAHOUN_ENABLE_GAUSSIAN_PROCESS", True),
    )


def is_desktop_minimal() -> bool:
    """Quick check if running in desktop_minimal mode."""
    return get_runtime_settings().mode == "desktop_minimal"


def should_skip_graph() -> bool:
    """Quick check if graph operations should be skipped."""
    settings = get_runtime_settings()
    return not settings.graph_enabled or settings.graph_backend == "disabled_fallback"


def should_skip_lora_training() -> bool:
    """Quick check if LoRA training should be skipped."""
    return not get_runtime_settings().lora_training_enabled


def is_enterprise_graph_mode() -> bool:
    """Quick check if running in enterprise_graph mode."""
    settings = get_runtime_settings()
    return (
        settings.mode == "enterprise_graph" or
        (settings.graph_enabled and settings.retrieval_mode == "hybrid_graph")
    )


def get_graph_config() -> Dict[str, Any]:
    """Get graph-specific configuration from runtime settings."""
    settings = get_runtime_settings()
    return {
        "neo4j_uri": settings.graph_neo4j_uri,
        "user": settings.graph_neo4j_user,
        "password": settings.graph_neo4j_password,
        "gat_checkpoint": settings.graph_gat_checkpoint,
        "mode": settings.graph_mode,
        "retrieval_mode": settings.retrieval_mode,
    }

