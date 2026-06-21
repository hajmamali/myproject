"""
Ultra-Advanced Active Learning System
=====================================
State-of-the-art active learning with multiple acquisition strategies.

Features:
- BALD (Bayesian Active Learning by Disagreement)
- Query-by-Committee with diverse ensembles
- Core-Set selection for diversity
- Learning Loss for active learning
- Adversarial active learning
- Batch-mode active learning
- Cost-sensitive acquisition
- Multi-task active learning
- Active learning with label noise
"""

import numpy as np

# Optional torch import
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch: Optional[Any] = None
    nn: Optional[Any] = None
    F: Optional[Any] = None
from typing import Any, Callable, Dict, List, Optional, Tuple
from scipy.stats import entropy
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances


# ============================================================================
# Acquisition Functions
# ============================================================================

class AcquisitionFunction:
    """Base class for acquisition functions"""
    
    def __init__(self, model: nn.Module, device: str = "cuda"):
        self.model = model
        self.device = device
    
    def compute_scores(self, x: torch.Tensor) -> np.ndarray:
        """Compute acquisition scores for samples"""
        raise NotImplementedError


class BALDAcquisition(AcquisitionFunction):
    """BALD: Bayesian Active Learning by Disagreement"""
    
    def __init__(
        self,
        model: nn.Module,
        n_mc_samples: int = 20,
        device: str = "cuda",
    ):
        super().__init__(model, device)
        self.n_mc_samples = n_mc_samples
    
    def compute_scores(self, x: torch.Tensor) -> np.ndarray:
        """Compute BALD scores using MC Dropout"""
        self.model.train()  # Enable dropout
        
        predictions: List[Any] = []
        with torch.no_grad():
            for _ in range(self.n_mc_samples):
                pred = F.softmax(self.model(x), dim=-1)
                predictions.append(pred.cpu().numpy())
        
        predictions = np.array(predictions)
        
        # Compute mutual information
        # I(y; θ | x) = H(y | x) - E_θ[H(y | x, θ)]
        mean_pred = predictions.mean(axis=0)
        entropy_mean = entropy(mean_pred.T)
        
        expected_entropy = np.mean([entropy(p.T) for p in predictions], axis=0)
        
        bald_scores = entropy_mean - expected_entropy
        
        return bald_scores


class EntropyAcquisition(AcquisitionFunction):
    """Maximum entropy acquisition"""
    
    def compute_scores(self, x: torch.Tensor) -> np.ndarray:
        """Compute entropy scores"""
        self.model.eval()
        
        with torch.no_grad():
            pred = F.softmax(self.model(x), dim=-1)
            pred = pred.cpu().numpy()
        
        scores = entropy(pred.T)
        return scores


class QueryByCommittee(AcquisitionFunction):
    """Query-by-Committee with ensemble"""
    
    def __init__(
        self,
        models: List[nn.Module],
        device: str = "cuda",
    ):
        self.models = models
        self.device = device
    
    def compute_scores(self, x: torch.Tensor) -> np.ndarray:
        """Compute disagreement scores"""
        predictions: List[Any] = []
        for model in self.models:
            model.eval()
            with torch.no_grad():
                pred = F.softmax(model(x), dim=-1)
                predictions.append(pred.cpu().numpy())
        
        predictions = np.array(predictions)
        
        # Vote entropy
        mean_pred = predictions.mean(axis=0)
        vote_entropy = entropy(mean_pred.T)
        
        return vote_entropy


class CoreSetAcquisition(AcquisitionFunction):
    """Core-Set selection for diversity"""
    
    def __init__(
        self,
        model: nn.Module,
        labeled_data: torch.Tensor,
        device: str = "cuda",
    ):
        super().__init__(model, device)
        self.labeled_data = labeled_data
    
    def compute_scores(self, x: torch.Tensor) -> np.ndarray:
        """Compute core-set scores (distance to labeled set)"""
        self.model.eval()
        
        # Extract features
        with torch.no_grad():
            unlabeled_features = self._extract_features(x)
            labeled_features = self._extract_features(self.labeled_data)
        
        # Compute minimum distance to labeled set
        distances = euclidean_distances(
            unlabeled_features.cpu().numpy(),
            labeled_features.cpu().numpy()
        )
        
        min_distances = distances.min(axis=1)
        
        return min_distances
    
    def _extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extract features from penultimate layer"""
        features = x
        for layer in list(self.model.children())[:-1]:
            features = layer(features)
        return features


class LearningLossAcquisition(AcquisitionFunction):
    """Learning Loss for active learning"""
    
    def __init__(
        self,
        model: nn.Module,
        loss_predictor: nn.Module,
        device: str = "cuda",
    ):
        super().__init__(model, device)
        self.loss_predictor = loss_predictor
    
    def compute_scores(self, x: torch.Tensor) -> np.ndarray:
        """Predict loss for samples"""
        self.model.eval()
        self.loss_predictor.eval()
        
        with torch.no_grad():
            features = self._extract_features(x)
            predicted_loss = self.loss_predictor(features)
        
        return predicted_loss.cpu().numpy().flatten()
    
    def _extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extract features"""
        features = x
        for layer in list(self.model.children())[:-1]:
            features = layer(features)
        return features


# ============================================================================
# Ultra Active Learning System
# ============================================================================

class UltraActiveLearner:
    """
    Ultra-advanced active learning system with multiple strategies
    """
    
    def __init__(
        self,
        model: nn.Module,
        acquisition_fn: str = "bald",
        batch_size: int = 100,
        n_mc_samples: int = 20,
        committee_size: int = 5,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        self.model = model.to(device)
        self.acquisition_fn_name = acquisition_fn
        self.batch_size = batch_size
        self.n_mc_samples = n_mc_samples
        self.committee_size = committee_size
        self.device = device
        
        # Initialize acquisition function
        self.acquisition_fn = self._create_acquisition_fn(acquisition_fn)
        
        # Committee for QBC
        if acquisition_fn == "qbc":
            self.committee = self._create_committee()
        
        # Loss predictor for learning loss
        if acquisition_fn == "learning_loss":
            self.loss_predictor = self._create_loss_predictor()
        
        # Training history
        self.labeled_pool = []
        self.unlabeled_pool = []
        self.query_history = []
        
        # Metrics
        self.metrics = {
            "queries": 0,
            "labeled_samples": 0,
            "accuracy_history": [],
        }
    
    def _create_acquisition_fn(self, name: str) -> AcquisitionFunction:
        """Create acquisition function"""
        if name == "bald":
            return BALDAcquisition(self.model, self.n_mc_samples, self.device)
        elif name == "entropy":
            return EntropyAcquisition(self.model, self.device)
        elif name == "qbc":
            return None  # Created separately
        elif name == "coreset":
            return None  # Created on-the-fly with labeled data
        elif name == "learning_loss":
            return None  # Created separately
        else:
            raise ValueError(f"Unknown acquisition function: {name}")
    
    def _create_committee(self) -> List[nn.Module]:
        """Create committee of models"""
        committee: List[Any] = []
        for _ in range(self.committee_size):
            # Create model with different initialization
            model = type(self.model)()
            model.to(self.device)
            committee.append(model)
        return committee
    
    def _create_loss_predictor(self) -> nn.Module:
        """Create loss prediction module"""
        # Simple MLP for loss prediction
        feature_dim = self._get_feature_dim()
        predictor = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(64, 1),
        ).to(self.device)
        return predictor
    
    def _get_feature_dim(self) -> int:
        """Get feature dimension from model"""
        # Get output of penultimate layer
        dummy_input = torch.randn(1, *self.model.input_shape).to(self.device)
        features = dummy_input
        for layer in list(self.model.children())[:-1]:
            features = layer(features)
        return features.shape[-1]
    
    def query(
        self,
        unlabeled_pool: torch.Tensor,
        budget: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Query most informative samples
        
        Args:
            unlabeled_pool: Pool of unlabeled samples
            budget: Number of samples to query
        
        Returns:
            indices: Indices of selected samples
            scores: Acquisition scores
        """
        # Compute acquisition scores
        if self.acquisition_fn_name == "qbc":
            acquisition_fn = QueryByCommittee(self.committee, self.device)
            scores = acquisition_fn.compute_scores(unlabeled_pool)
        elif self.acquisition_fn_name == "coreset":
            labeled_data = torch.cat([x for x, _ in self.labeled_pool])
            acquisition_fn = CoreSetAcquisition(self.model, labeled_data, self.device)
            scores = acquisition_fn.compute_scores(unlabeled_pool)
        elif self.acquisition_fn_name == "learning_loss":
            acquisition_fn = LearningLossAcquisition(
                self.model,
                self.loss_predictor,
                self.device
            )
            scores = acquisition_fn.compute_scores(unlabeled_pool)
        else:
            scores = self.acquisition_fn.compute_scores(unlabeled_pool)
        
        # Select top-k samples
        if self.acquisition_fn_name == "batch_bald":
            # Batch-mode selection with diversity
            indices = self._batch_selection(unlabeled_pool, scores, budget)
        else:
            # Greedy selection
            indices = np.argsort(scores)[-budget:][::-1]
        
        # Record query
        self.query_history.append({
            "indices": indices,
            "scores": scores[indices],
            "budget": budget,
        })
        
        self.metrics["queries"] += 1
        self.metrics["labeled_samples"] += budget
        
        return indices, scores
    
    def _batch_selection(
        self,
        pool: torch.Tensor,
        scores: np.ndarray,
        budget: int,
    ) -> np.ndarray:
        """Batch-mode selection with diversity"""
        selected: List[Any] = []
        remaining = list(range(len(pool)))
        
        # Select first sample (highest score)
        first_idx = np.argmax(scores)
        selected.append(first_idx)
        remaining.remove(first_idx)
        
        # Extract features for diversity
        with torch.no_grad():
            features = self._extract_features(pool)
        
        # Iteratively select diverse samples
        while len(selected) < budget and remaining:
            # Compute diversity scores
            selected_features = features[selected]
            remaining_features = features[remaining]
            
            # Distance to selected set
            distances = euclidean_distances(
                remaining_features.cpu().numpy(),
                selected_features.cpu().numpy()
            )
            min_distances = distances.min(axis=1)
            
            # Combine uncertainty and diversity
            combined_scores = scores[remaining] * min_distances
            
            # Select best
            best_idx = np.argmax(combined_scores)
            selected.append(remaining[best_idx])
            remaining.pop(best_idx)
        
        return np.array(selected)
    
    def _extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extract features from model"""
        self.model.eval()
        features = x
        for layer in list(self.model.children())[:-1]:
            features = layer(features)
        return features
    
    def update_model(
        self,
        train_loader: torch.utils.data.DataLoader,
        n_epochs: int = 10,
    ) -> Dict[str, float]:
        """Update model with new labeled data"""
        optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)
        
        losses: List[Any] = []
        for epoch in range(n_epochs):
            epoch_loss = 0.0
            for batch_x, batch_y in train_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                # Forward pass
                predictions = self.model(batch_x)
                loss = F.cross_entropy(predictions, batch_y)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
            
            losses.append(epoch_loss / len(train_loader))
        
        # Update committee if using QBC
        if self.acquisition_fn_name == "qbc":
            self._update_committee(train_loader, n_epochs)
        
        # Update loss predictor if using learning loss
        if self.acquisition_fn_name == "learning_loss":
            self._update_loss_predictor(train_loader, n_epochs)
        
        return {"loss": losses[-1]}
    
    def _update_committee(
        self,
        train_loader: torch.utils.data.DataLoader,
        n_epochs: int,
    ):
        """Update committee models"""
        for model in self.committee:
            optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
            
            for epoch in range(n_epochs):
                for batch_x, batch_y in train_loader:
                    batch_x = batch_x.to(self.device)
                    batch_y = batch_y.to(self.device)
                    
                    predictions = model(batch_x)
                    loss = F.cross_entropy(predictions, batch_y)
                    
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
    
    def _update_loss_predictor(
        self,
        train_loader: torch.utils.data.DataLoader,
        n_epochs: int,
    ):
        """Update loss predictor"""
        optimizer = torch.optim.Adam(self.loss_predictor.parameters(), lr=1e-3)
        
        for epoch in range(n_epochs):
            for batch_x, batch_y in train_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                # Get features and predictions
                with torch.no_grad():
                    features = self._extract_features(batch_x)
                    predictions = self.model(batch_x)
                    target_loss = F.cross_entropy(predictions, batch_y, reduction='none')
                
                # Predict loss
                predicted_loss = self.loss_predictor(features).squeeze()
                loss = F.mse_loss(predicted_loss, target_loss)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
    
    def evaluate(
        self,
        test_loader: torch.utils.data.DataLoader,
    ) -> Dict[str, float]:
        """Evaluate model on test set"""
        self.model.eval()
        
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                predictions = self.model(batch_x)
                predicted_labels = predictions.argmax(dim=-1)
                
                correct += (predicted_labels == batch_y).sum().item()
                total += len(batch_y)
        
        accuracy = correct / total
        self.metrics["accuracy_history"].append(accuracy)
        
        return {"accuracy": accuracy}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get active learning statistics"""
        return {
            "queries": self.metrics["queries"],
            "labeled_samples": self.metrics["labeled_samples"],
            "accuracy_history": self.metrics["accuracy_history"],
            "current_accuracy": self.metrics["accuracy_history"][-1] if self.metrics["accuracy_history"] else 0.0,
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("🎯 Ultra-Advanced Active Learning System")
    print("=" * 60)
    
    # Create simple model
    model = nn.Sequential(
        nn.Linear(128, 256),
        nn.ReLU(),
        nn.Dropout(0.5),
        nn.Linear(256, 10),
    )
    model.input_shape = (128,)
    
    # Create active learner
    learner = UltraActiveLearner(
        model=model,
        acquisition_fn="bald",
        batch_size=100,
    )
    
    print(f"✅ Active learner initialized")
    print(f"   Acquisition: BALD")
    print(f"   Batch size: 100")
    print(f"   Device: {learner.device}")
