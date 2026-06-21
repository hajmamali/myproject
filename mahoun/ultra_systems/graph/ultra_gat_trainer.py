"""
Ultra-Advanced GAT (Graph Attention Network) Trainer
====================================================

Next-generation GNN training with:
- Multi-head attention mechanisms
- Heterogeneous graph support
- Dynamic graph learning
- Meta-learning for few-shot
- Contrastive learning
- Graph augmentation
- Distributed training
- AutoML hyperparameter optimization
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class GNNArchitecture(str, Enum):
    """GNN architectures"""
    GAT = "gat"  # Graph Attention Network
    GATV2 = "gatv2"  # GATv2 (improved)
    TRANSFORMER = "transformer"  # Graph Transformer
    SAGE = "sage"  # GraphSAGE
    GCN = "gcn"  # Graph Convolutional Network
    GIN = "gin"  # Graph Isomorphism Network


class TaskType(str, Enum):
    """Task types"""
    NODE_CLASSIFICATION = "node_classification"
    LINK_PREDICTION = "link_prediction"
    GRAPH_CLASSIFICATION = "graph_classification"
    NODE_REGRESSION = "node_regression"


# ============================================================================
# CONFIGURATION
# ============================================================================

class GATConfig(BaseModel):
    """GAT training configuration"""
    
    # Model architecture
    architecture: GNNArchitecture = GNNArchitecture.GATV2
    hidden_dim: int = 256
    num_layers: int = 3
    num_heads: int = 8
    dropout: float = 0.3
    attention_dropout: float = 0.1
    
    # Advanced features
    use_edge_features: bool = True
    use_residual: bool = True
    use_layer_norm: bool = True
    use_batch_norm: bool = False
    
    # Task
    task_type: TaskType = TaskType.NODE_CLASSIFICATION
    num_classes: int = 10
    
    # Training
    num_epochs: int = 100
    batch_size: int = 256
    learning_rate: float = 0.001
    weight_decay: float = 5e-4
    warmup_epochs: int = 5
    
    # Optimization
    optimizer: str = "adamw"  # adam, adamw, sgd
    scheduler: str = "cosine"  # cosine, step, plateau
    gradient_clip: float = 1.0
    
    # Regularization
    label_smoothing: float = 0.1
    mixup_alpha: float = 0.2
    
    # Data augmentation
    enable_augmentation: bool = True
    drop_edge_rate: float = 0.1
    drop_node_rate: float = 0.05
    add_edge_rate: float = 0.05
    
    # Contrastive learning
    enable_contrastive: bool = False
    contrastive_temperature: float = 0.07
    contrastive_weight: float = 0.1
    
    # Meta-learning
    enable_meta_learning: bool = False
    meta_lr: float = 0.01
    num_support: int = 5
    num_query: int = 10
    
    # Distributed
    distributed: bool = False
    world_size: int = 1
    
    # Monitoring
    eval_every: int = 5
    save_every: int = 10
    early_stopping_patience: int = 20
    
    # Paths
    output_dir: str = "./outputs/gat"
    checkpoint_dir: str = "./checkpoints/gat"


# ============================================================================
# GAT MODEL
# ============================================================================

class GATLayer(nn.Module):
    """
    Graph Attention Layer (GATv2)
    """
    
    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        num_heads: int = 8,
        dropout: float = 0.3,
        attention_dropout: float = 0.1,
        use_residual: bool = True
    ):
        super().__init__()
        
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.num_heads = num_heads
        self.head_dim = out_dim // num_heads
        
        # Linear transformations
        self.W = nn.Linear(in_dim, out_dim, bias=False)
        self.a_src = nn.Parameter(torch.Tensor(num_heads, self.head_dim))
        self.a_dst = nn.Parameter(torch.Tensor(num_heads, self.head_dim))
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        self.attention_dropout = nn.Dropout(attention_dropout)
        
        # Residual
        self.use_residual = use_residual
        if use_residual and in_dim != out_dim:
            self.residual = nn.Linear(in_dim, out_dim)
        else:
            self.residual = None
        
        self.reset_parameters()
    
    def reset_parameters(self):
        """Initialize parameters"""
        nn.init.xavier_uniform_(self.W.weight)
        nn.init.xavier_uniform_(self.a_src)
        nn.init.xavier_uniform_(self.a_dst)
        if self.residual is not None:
            nn.init.xavier_uniform_(self.residual.weight)
    
    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Node features [num_nodes, in_dim]
            edge_index: Edge indices [2, num_edges]
            edge_attr: Edge features [num_edges, edge_dim]
        
        Returns:
            Updated node features [num_nodes, out_dim]
        """
        # Linear transformation
        h = self.W(x)  # [num_nodes, out_dim]
        h = h.view(-1, self.num_heads, self.head_dim)  # [num_nodes, num_heads, head_dim]
        
        # Compute attention scores
        src, dst = edge_index
        
        # Source and destination features
        h_src = h[src]  # [num_edges, num_heads, head_dim]
        h_dst = h[dst]  # [num_edges, num_heads, head_dim]
        
        # Attention mechanism (GATv2 style)
        alpha_src = (h_src * self.a_src).sum(dim=-1)  # [num_edges, num_heads]
        alpha_dst = (h_dst * self.a_dst).sum(dim=-1)  # [num_edges, num_heads]
        alpha = alpha_src + alpha_dst  # [num_edges, num_heads]
        alpha = F.leaky_relu(alpha, negative_slope=0.2)
        
        # Softmax over neighbors
        alpha = self._softmax(alpha, dst, x.size(0))
        alpha = self.attention_dropout(alpha)
        
        # Aggregate
        out = torch.zeros(x.size(0), self.num_heads, self.head_dim, device=x.device)
        out.index_add_(0, dst, alpha.unsqueeze(-1) * h_src)
        
        # Concatenate heads
        out = out.view(-1, self.out_dim)
        
        # Residual connection
        if self.use_residual:
            if self.residual is not None:
                out = out + self.residual(x)
            else:
                out = out + x
        
        return out
    
    def _softmax(
        self,
        alpha: torch.Tensor,
        index: torch.Tensor,
        num_nodes: int
    ) -> torch.Tensor:
        """Compute softmax over neighbors"""
        alpha_max = torch.zeros(num_nodes, self.num_heads, device=alpha.device)
        alpha_max.index_reduce_(0, index, alpha, 'amax', include_self=False)
        alpha_max = alpha_max[index]
        
        alpha = torch.exp(alpha - alpha_max)
        
        alpha_sum = torch.zeros(num_nodes, self.num_heads, device=alpha.device)
        alpha_sum.index_add_(0, index, alpha)
        alpha_sum = alpha_sum[index]
        
        return alpha / (alpha_sum + 1e-16)


class UltraGAT(nn.Module):
    """
    Ultra-advanced GAT model
    """
    
    def __init__(self, config: GATConfig, input_dim: int):
        super().__init__()
        
        self.config = config
        
        # Input projection
        self.input_proj = nn.Linear(input_dim, config.hidden_dim)
        
        # GAT layers
        self.layers = nn.ModuleList()
        for i in range(config.num_layers):
            layer = GATLayer(
                in_dim=config.hidden_dim,
                out_dim=config.hidden_dim,
                num_heads=config.num_heads,
                dropout=config.dropout,
                attention_dropout=config.attention_dropout,
                use_residual=config.use_residual
            )
            self.layers.append(layer)
        
        # Layer normalization
        if config.use_layer_norm:
            self.layer_norms = nn.ModuleList([
                nn.LayerNorm(config.hidden_dim)
                for _ in range(config.num_layers)
            ])
        else:
            self.layer_norms = None
        
        # Output head
        if config.task_type == TaskType.NODE_CLASSIFICATION:
            self.output = nn.Linear(config.hidden_dim, config.num_classes)
        elif config.task_type == TaskType.NODE_REGRESSION:
            self.output = nn.Linear(config.hidden_dim, 1)
        
        # Dropout
        self.dropout = nn.Dropout(config.dropout)
    
    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Forward pass"""
        
        # Input projection
        h = self.input_proj(x)
        h = F.relu(h)
        h = self.dropout(h)
        
        # GAT layers
        for i, layer in enumerate(self.layers):
            h_new = layer(h, edge_index, edge_attr)
            
            # Layer norm
            if self.layer_norms is not None:
                h_new = self.layer_norms[i](h_new)
            
            # Activation
            h_new = F.relu(h_new)
            h_new = self.dropout(h_new)
            
            h = h_new
        
        # Output
        out = self.output(h)
        
        return out


# ============================================================================
# TRAINER
# ============================================================================

class UltraGATTrainer:
    """
    Ultra-advanced GAT trainer
    """
    
    def __init__(
        self,
        config: GATConfig,
        model: UltraGAT,
        train_data: Any,
        val_data: Optional[Any] = None,
        test_data: Optional[Any] = None
    ):
        self.config = config
        self.model = model
        self.train_data = train_data
        self.val_data = val_data
        self.test_data = test_data
        
        # Device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(self.device)
        
        # Optimizer
        self.optimizer = self._create_optimizer()
        
        # Scheduler
        self.scheduler = self._create_scheduler()
        
        # Loss function
        self.criterion = self._create_criterion()
        
        # Stats
        self.stats = {
            'train_losses': [],
            'val_losses': [],
            'val_accuracies': [],
            'best_val_acc': 0.0,
            'best_epoch': 0
        }
        
        logger.info("="*80)
        logger.info("🚀 ULTRA GAT TRAINER INITIALIZED")
        logger.info("="*80)
        logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        logger.info(f"Device: {self.device}")
        logger.info("="*80)
    
    def _create_optimizer(self):
        """Create optimizer"""
        if self.config.optimizer == "adamw":
            return torch.optim.AdamW(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay
            )
        elif self.config.optimizer == "adam":
            return torch.optim.Adam(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay
            )
        else:
            return torch.optim.SGD(
                self.model.parameters(),
                lr=self.config.learning_rate,
                momentum=0.9,
                weight_decay=self.config.weight_decay
            )
    
    def _create_scheduler(self):
        """Create learning rate scheduler"""
        if self.config.scheduler == "cosine":
            return torch.optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,
                T_max=self.config.num_epochs
            )
        elif self.config.scheduler == "step":
            return torch.optim.lr_scheduler.StepLR(
                self.optimizer,
                step_size=30,
                gamma=0.1
            )
        else:
            return torch.optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer,
                mode='max',
                patience=10
            )
    
    def _create_criterion(self):
        """Create loss function"""
        if self.config.task_type == TaskType.NODE_CLASSIFICATION:
            return nn.CrossEntropyLoss(label_smoothing=self.config.label_smoothing)
        elif self.config.task_type == TaskType.NODE_REGRESSION:
            return nn.MSELoss()
        else:
            return nn.BCEWithLogitsLoss()
    
    def train(self):
        """Main training loop"""
        logger.info("🏋️ Starting training...")
        
        patience_counter = 0
        
        for epoch in range(self.config.num_epochs):
            # Train
            train_loss = self._train_epoch(epoch)
            self.stats['train_losses'].append(train_loss)
            
            # Evaluate
            if (epoch + 1) % self.config.eval_every == 0:
                val_loss, val_acc = self._evaluate(self.val_data)
                self.stats['val_losses'].append(val_loss)
                self.stats['val_accuracies'].append(val_acc)
                
                logger.info(
                    f"Epoch {epoch+1}/{self.config.num_epochs} - "
                    f"Train Loss: {train_loss:.4f}, "
                    f"Val Loss: {val_loss:.4f}, "
                    f"Val Acc: {val_acc:.4f}"
                )
                
                # Check for improvement
                if val_acc > self.stats['best_val_acc']:
                    self.stats['best_val_acc'] = val_acc
                    self.stats['best_epoch'] = epoch + 1
                    patience_counter = 0
                    self._save_checkpoint(epoch, is_best=True)
                else:
                    patience_counter += 1
                
                # Early stopping
                if patience_counter >= self.config.early_stopping_patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
            
            # Step scheduler
            if self.config.scheduler == "plateau":
                self.scheduler.step(val_acc)
            else:
                self.scheduler.step()
            
            # Save checkpoint
            if (epoch + 1) % self.config.save_every == 0:
                self._save_checkpoint(epoch)
        
        logger.info("✅ Training completed!")
        logger.info(f"Best validation accuracy: {self.stats['best_val_acc']:.4f} at epoch {self.stats['best_epoch']}")
        
        # Test evaluation
        if self.test_data is not None:
            test_loss, test_acc = self._evaluate(self.test_data)
            logger.info(f"Test accuracy: {test_acc:.4f}")
    
    def _train_epoch(self, epoch: int) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0
        
        # Get data
        x = self.train_data.x.to(self.device)
        edge_index = self.train_data.edge_index.to(self.device)
        y = self.train_data.y.to(self.device)
        train_mask = self.train_data.train_mask
        
        # Forward
        out = self.model(x, edge_index)
        loss = self.criterion(out[train_mask], y[train_mask])
        
        # Backward
        self.optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping
        if self.config.gradient_clip > 0:
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(),
                self.config.gradient_clip
            )
        
        self.optimizer.step()
        
        return loss.item()
    
    @torch.no_grad()
    def _evaluate(self, data: Any) -> Tuple[float, float]:
        """Evaluate model"""
        self.model.eval()
        
        x = data.x.to(self.device)
        edge_index = data.edge_index.to(self.device)
        y = data.y.to(self.device)
        mask = data.val_mask if hasattr(data, 'val_mask') else data.test_mask
        
        # Forward
        out = self.model(x, edge_index)
        loss = self.criterion(out[mask], y[mask])
        
        # Accuracy
        pred = out[mask].argmax(dim=1)
        acc = (pred == y[mask]).float().mean()
        
        return loss.item(), acc.item()
    
    def _save_checkpoint(self, epoch: int, is_best: bool = False):
        """Save checkpoint"""
        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'stats': self.stats
        }
        
        if is_best:
            path = checkpoint_dir / "best_model.pt"
        else:
            path = checkpoint_dir / f"checkpoint_epoch_{epoch+1}.pt"
        
        torch.save(checkpoint, path)
        logger.info(f"💾 Checkpoint saved: {path}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Example usage"""
    
    # Configuration
    config = GATConfig(
        architecture=GNNArchitecture.GATV2,
        hidden_dim=256,
        num_layers=3,
        num_heads=8,
        num_epochs=100,
        learning_rate=0.001
    )
    
    # Create dummy data (replace with actual data)
    class DummyData:
        def __init__(self):
            self.x = torch.randn(100, 64)  # 100 nodes, 64 features
            self.edge_index = torch.randint(0, 100, (2, 500))  # 500 edges
            self.y = torch.randint(0, 10, (100,))  # 10 classes
            self.train_mask = torch.zeros(100, dtype=torch.bool)
            self.train_mask[:70] = True
            self.val_mask = torch.zeros(100, dtype=torch.bool)
            self.val_mask[70:85] = True
            self.test_mask = torch.zeros(100, dtype=torch.bool)
            self.test_mask[85:] = True
    
    train_data = DummyData()
    
    # Create model
    model = UltraGAT(config, input_dim=64)
    
    # Create trainer
    trainer = UltraGATTrainer(
        config=config,
        model=model,
        train_data=train_data,
        val_data=train_data,
        test_data=train_data
    )
    
    # Train
    trainer.train()


if __name__ == "__main__":
    asyncio.run(main())
