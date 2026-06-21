"""
GAT Trainer Job - Official Entrypoint
=====================================
Offline job for training Graph Attention Network models.

This script:
1. Reads config from configs/graph/training.yaml (or defaults)
2. Loads training data
3. Trains GAT model
4. Saves checkpoint to models/graph/gat_*.pt
5. Produces training reports to logs/graph_training/

Usage:
    python -m graph.training.run_gat_trainer
    
    # With custom config
    python -m graph.training.run_gat_trainer --config configs/graph/custom_training.yaml
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_training_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load training configuration from YAML file.
    
    Args:
        config_path: Path to config file (defaults to configs/graph/training.yaml)
    
    Returns:
        Dictionary with training config
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "configs" / "runtime_profile.yaml"
    else:
        config_path = Path(config_path)
    
    defaults = {
        "hidden_dim": 768,
        "num_heads": 8,
        "num_layers": 3,
        "dropout": 0.1,
        "learning_rate": 0.0001,
        "batch_size": 32,
        "epochs": 100,
        "checkpoint_dir": "models/graph",
        "log_dir": "logs/graph_training"
    }
    
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return defaults
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f) or {}
        
        training_config = yaml_config.get("training", {}).get("gat_trainer", {})
        
        # Merge with defaults
        config = {**defaults, **training_config}
        return config
    except ImportError:
        logger.warning("YAML not available, using defaults")
        return defaults
    except Exception as e:
        logger.warning(f"Failed to load config: {e}, using defaults")
        return defaults


def main():
    """Main entrypoint for GAT training job"""
    parser = argparse.ArgumentParser(description="Train GAT model for graph reranking")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to training config YAML file"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default=None,
        help="Directory to save checkpoints"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Directory for training logs"
    )
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("GAT Trainer Job - Starting")
    logger.info("="*80)
    
    # Load config
    config = load_training_config(args.config)
    
    # Override with CLI args
    if args.checkpoint_dir:
        config["checkpoint_dir"] = args.checkpoint_dir
    if args.log_dir:
        config["log_dir"] = args.log_dir
    
    # Ensure directories exist
    checkpoint_dir = Path(config["checkpoint_dir"])
    log_dir = Path(config["log_dir"])
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Checkpoint directory: {checkpoint_dir}")
    logger.info(f"Log directory: {log_dir}")
    
    # Import and run trainer
    try:
        from mahoun.graph.ultra_gat_trainer import UltraGATTrainer
        
        trainer = UltraGATTrainer(
            hidden_dim=config["hidden_dim"],
            num_heads=config["num_heads"],
            num_layers=config["num_layers"],
            dropout=config["dropout"],
            learning_rate=config["learning_rate"],
            batch_size=config["batch_size"],
            checkpoint_dir=str(checkpoint_dir),
            log_dir=str(log_dir)
        )
        
        logger.info("Starting GAT training...")
        trainer.train(epochs=config["epochs"])
        
        # Save final checkpoint
        final_checkpoint = checkpoint_dir / "gat_v1.pt"
        trainer.save_checkpoint(str(final_checkpoint))
        
        logger.info(f"✅ Training complete! Checkpoint saved to {final_checkpoint}")
        logger.info("="*80)
        
        return 0
        
    except ImportError as e:
        logger.error(f"Failed to import GAT trainer: {e}")
        logger.error("Make sure torch and torch-geometric are installed")
        return 1
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

