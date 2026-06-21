"""
Model Loading Utilities for GAT Reranker
=========================================

Utilities for loading GAT models from local paths or W&B artifacts.
"""

import torch
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from mahoun.graph.gnn.gat_reranker import GATReranker, GATRerankerService

log = logging.getLogger(__name__)


def load_gat_model(
    model_path: str,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    validate: bool = True
) -> GATReranker:
    """
    Load GAT model from checkpoint
    
    Args:
        model_path: Path to model checkpoint
        device: Device to load model on
        validate: Whether to validate model architecture
        
    Returns:
        Loaded GAT model
    """
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    log.info(f"Loading GAT model from {model_path}")
    
    checkpoint = torch.load(model_path, map_location=device)
    
    # Get model config
    config = checkpoint.get("config", {})
    
    # Validate config
    if validate:
        required_keys = ["in_channels", "hidden_channels", "out_channels"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
    
    # Create model
    model = GATReranker(
        in_channels=config.get("in_channels", 1024),
        hidden_channels=config.get("hidden_channels", 256),
        out_channels=config.get("out_channels", 128),
        num_heads=config.get("num_heads", 4),
        num_layers=config.get("num_layers", 2),
        dropout=config.get("dropout", 0.1),
        edge_dim=config.get("edge_dim", 1),
    )
    
    # Load state dict
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    
    log.info(f"Model loaded successfully on {device}")
    
    return model


def load_gat_reranker_service(
    model_path: Optional[str] = None,
    graph_path: Optional[str] = None,
    config_path: Optional[str] = None,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    **kwargs
) -> GATRerankerService:
    """
    Load complete GAT reranker service
    
    Args:
        model_path: Path to model checkpoint
        graph_path: Path to graph data
        config_path: Path to config file (optional)
        device: Device for inference
        **kwargs: Additional arguments for GATRerankerService
        
    Returns:
        Initialized GATRerankerService
    """
    log.info("Loading GAT Reranker Service")
    
    # Load config if provided
    config = {}
    if config_path and Path(config_path).exists():
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
    
    # Merge with kwargs
    config.update(kwargs)
    
    # Create service
    service = GATRerankerService(
        model_path=model_path,
        graph_path=graph_path,
        device=device,
        fallback_to_pagerank=config.get("fallback_to_pagerank", True),
        enable_uncertainty=config.get("enable_uncertainty", True),
    )
    
    log.info("GAT Reranker Service loaded successfully")
    
    return service


def validate_model_checkpoint(model_path: str) -> Dict[str, Any]:
    """
    Validate model checkpoint and return info
    
    Args:
        model_path: Path to model checkpoint
        
    Returns:
        Dictionary with model info
    """
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    checkpoint = torch.load(model_path, map_location="cpu")
    
    info = {
        "epoch": checkpoint.get("epoch", "unknown"),
        "metrics": checkpoint.get("metrics", {}),
        "config": checkpoint.get("config", {}),
        "has_optimizer": "optimizer_state_dict" in checkpoint,
        "has_model": "model_state_dict" in checkpoint,
    }
    
    return info


def download_model_from_wandb(
    artifact_name: str,
    project: str,
    entity: Optional[str] = None,
    version: str = "latest",
    download_dir: str = "models/downloaded"
) -> str:
    """
    Download model from W&B artifacts
    
    Args:
        artifact_name: Name of W&B artifact
        project: W&B project name
        entity: W&B entity (optional)
        version: Artifact version
        download_dir: Directory to download to
        
    Returns:
        Path to downloaded model
    """
    try:
        import wandb
        
        # Initialize W&B
        api = wandb.Api()
        
        # Construct artifact path
        if entity:
            artifact_path = f"{entity}/{project}/{artifact_name}:{version}"
        else:
            artifact_path = f"{project}/{artifact_name}:{version}"
        
        log.info(f"Downloading artifact: {artifact_path}")
        
        # Download artifact
        artifact = api.artifact(artifact_path)
        download_path = artifact.download(root=download_dir)
        
        # Find model file
        model_files = list(Path(download_path).glob("*.pt"))
        if not model_files:
            raise FileNotFoundError("No .pt file found in artifact")
        
        model_path = str(model_files[0])
        log.info(f"Model downloaded to: {model_path}")
        
        return model_path
        
    except ImportError:
        raise ImportError("wandb package required for downloading from W&B")
    except Exception as e:
        log.error(f"Failed to download model from W&B: {e}")
        raise
