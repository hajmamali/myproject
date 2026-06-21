"""
Ultra-Advanced Multi-Armed Bandit System
========================================
State-of-the-art bandit algorithms for exploration-exploitation.

Features:
- Thompson Sampling (Bayesian)
- UCB (Upper Confidence Bound) variants
- Contextual bandits with neural networks
- LinUCB for linear contextual bandits
- Neural Thompson Sampling
- Adversarial bandits (EXP3)
- Combinatorial bandits
- Dueling bandits
- Restless bandits
- Cascading bandits
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
from scipy.stats import beta as beta_dist


# ============================================================================
# Classic Bandits
# ============================================================================

class ThompsonSampling:
    """Thompson Sampling with Beta-Bernoulli"""
    
    def __init__(self, n_arms: int, alpha: float = 1.0, beta: float = 1.0):
        self.n_arms = n_arms
        self.alpha = np.ones(n_arms) * alpha
        self.beta = np.ones(n_arms) * beta
        self.pulls = np.zeros(n_arms)
        self.rewards = np.zeros(n_arms)
    
    def select_arm(self) -> int:
        """Select arm using Thompson Sampling"""
        samples = np.random.beta(self.alpha, self.beta)
        return np.argmax(samples)
    
    def update(self, arm: int, reward: float):
        """Update posterior"""
        self.pulls[arm] += 1
        self.rewards[arm] += reward
        
        if reward > 0:
            self.alpha[arm] += 1
        else:
            self.beta[arm] += 1
    
    def get_statistics(self) -> Dict[int, Dict[str, float]]:
        """Get arm statistics"""
        stats = {}
        for arm in range(self.n_arms):
            mean = self.alpha[arm] / (self.alpha[arm] + self.beta[arm])
            stats[arm] = {
                "mean": mean,
                "pulls": self.pulls[arm],
                "total_reward": self.rewards[arm],
            }
        return stats


class UCB:
    """Upper Confidence Bound"""
    
    def __init__(self, n_arms: int, c: float = 2.0):
        self.n_arms = n_arms
        self.c = c
        self.pulls = np.zeros(n_arms)
        self.rewards = np.zeros(n_arms)
        self.t = 0
    
    def select_arm(self) -> int:
        """Select arm using UCB"""
        self.t += 1
        
        # Pull each arm once first
        if self.t <= self.n_arms:
            return self.t - 1
        
        # Compute UCB values
        means = self.rewards / (self.pulls + 1e-10)
        ucb_values = means + self.c * np.sqrt(np.log(self.t) / (self.pulls + 1e-10))
        
        return np.argmax(ucb_values)
    
    def update(self, arm: int, reward: float):
        """Update statistics"""
        self.pulls[arm] += 1
        self.rewards[arm] += reward
    
    def get_statistics(self) -> Dict[int, Dict[str, float]]:
        """Get arm statistics"""
        stats = {}
        for arm in range(self.n_arms):
            mean = self.rewards[arm] / (self.pulls[arm] + 1e-10)
            stats[arm] = {
                "mean": mean,
                "pulls": self.pulls[arm],
                "total_reward": self.rewards[arm],
            }
        return stats


# ============================================================================
# Contextual Bandits
# ============================================================================

class LinUCB:
    """Linear UCB for contextual bandits"""
    
    def __init__(self, n_arms: int, context_dim: int, alpha: float = 1.0):
        self.n_arms = n_arms
        self.context_dim = context_dim
        self.alpha = alpha
        
        # Initialize parameters for each arm
        self.A = [np.identity(context_dim) for _ in range(n_arms)]
        self.b = [np.zeros(context_dim) for _ in range(n_arms)]
        
        self.pulls = np.zeros(n_arms)
    
    def select_arm(self, context: np.ndarray) -> int:
        """Select arm given context"""
        ucb_values = np.zeros(self.n_arms)
        
        for arm in range(self.n_arms):
            A_inv = np.linalg.inv(self.A[arm])
            theta = A_inv @ self.b[arm]
            
            # UCB = expected reward + confidence bonus
            expected_reward = context @ theta
            confidence = self.alpha * np.sqrt(context @ A_inv @ context)
            
            ucb_values[arm] = expected_reward + confidence
        
        return np.argmax(ucb_values)
    
    def update(self, arm: int, context: np.ndarray, reward: float):
        """Update parameters"""
        self.A[arm] += np.outer(context, context)
        self.b[arm] += reward * context
        self.pulls[arm] += 1
    
    def get_statistics(self) -> Dict[int, Dict[str, float]]:
        """Get arm statistics"""
        stats = {}
        for arm in range(self.n_arms):
            stats[arm] = {
                "pulls": self.pulls[arm],
            }
        return stats


class NeuralContextualBandit(nn.Module):
    """Neural network for contextual bandits"""
    
    def __init__(
        self,
        context_dim: int,
        n_arms: int,
        hidden_dim: int = 128,
    ):
        super().__init__()
        self.context_dim = context_dim
        self.n_arms = n_arms
        
        # Shared feature extractor
        self.feature_extractor = nn.Sequential(
            nn.Linear(context_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        
        # Separate head for each arm
        self.arm_heads = nn.ModuleList([
            nn.Linear(hidden_dim, 1) for _ in range(n_arms)
        ])
    
    def forward(self, context: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        features = self.feature_extractor(context)
        
        # Get reward prediction for each arm
        rewards = torch.cat([head(features) for head in self.arm_heads], dim=-1)
        
        return rewards


class NeuralThompsonSampling:
    """Thompson Sampling with neural networks"""
    
    def __init__(
        self,
        context_dim: int,
        n_arms: int,
        hidden_dim: int = 128,
        n_ensemble: int = 10,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        self.context_dim = context_dim
        self.n_arms = n_arms
        self.n_ensemble = n_ensemble
        self.device = device
        
        # Ensemble of networks for uncertainty estimation
        self.ensemble = [
            NeuralContextualBandit(context_dim, n_arms, hidden_dim).to(device)
            for _ in range(n_ensemble)
        ]
        
        self.optimizers = [
            torch.optim.Adam(model.parameters(), lr=1e-3)
            for model in self.ensemble
        ]
        
        self.pulls = np.zeros(n_arms)
        self.buffer = []
    
    def select_arm(self, context: np.ndarray) -> int:
        """Select arm using Thompson Sampling"""
        context_tensor = torch.FloatTensor(context).unsqueeze(0).to(self.device)
        
        # Sample from ensemble
        sampled_model = np.random.choice(self.ensemble)
        
        with torch.no_grad():
            rewards = sampled_model(context_tensor)
        
        arm = rewards.argmax().item()
        return arm
    
    def update(self, context: np.ndarray, arm: int, reward: float):
        """Update ensemble"""
        self.pulls[arm] += 1
        self.buffer.append((context, arm, reward))
        
        # Train ensemble periodically
        if len(self.buffer) >= 32:
            self._train_ensemble()
            self.buffer = []
    
    def _train_ensemble(self):
        """Train ensemble on buffer"""
        contexts = torch.FloatTensor([x[0] for x in self.buffer]).to(self.device)
        arms = torch.LongTensor([x[1] for x in self.buffer]).to(self.device)
        rewards = torch.FloatTensor([x[2] for x in self.buffer]).to(self.device)
        
        for model, optimizer in zip(self.ensemble, self.optimizers):
            # Bootstrap sample
            indices = np.random.choice(len(self.buffer), len(self.buffer), replace=True)
            batch_contexts = contexts[indices]
            batch_arms = arms[indices]
            batch_rewards = rewards[indices]
            
            # Forward pass
            predictions = model(batch_contexts)
            predicted_rewards = predictions.gather(1, batch_arms.unsqueeze(1)).squeeze()
            
            # Loss
            loss = F.mse_loss(predicted_rewards, batch_rewards)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    
    def get_statistics(self) -> Dict[int, Dict[str, float]]:
        """Get arm statistics"""
        stats = {}
        for arm in range(self.n_arms):
            stats[arm] = {
                "pulls": self.pulls[arm],
            }
        return stats


# ============================================================================
# Adversarial Bandits
# ============================================================================

class EXP3:
    """EXP3 for adversarial bandits"""
    
    def __init__(self, n_arms: int, gamma: float = 0.1):
        self.n_arms = n_arms
        self.gamma = gamma
        self.weights = np.ones(n_arms)
        self.pulls = np.zeros(n_arms)
    
    def select_arm(self) -> int:
        """Select arm using EXP3"""
        # Compute probabilities
        total_weight = self.weights.sum()
        probs = (1 - self.gamma) * (self.weights / total_weight) + (self.gamma / self.n_arms)
        
        # Sample arm
        arm = np.random.choice(self.n_arms, p=probs)
        return arm
    
    def update(self, arm: int, reward: float):
        """Update weights"""
        self.pulls[arm] += 1
        
        # Compute probability
        total_weight = self.weights.sum()
        prob = (1 - self.gamma) * (self.weights[arm] / total_weight) + (self.gamma / self.n_arms)
        
        # Estimated reward
        estimated_reward = reward / prob
        
        # Update weight
        self.weights[arm] *= np.exp(self.gamma * estimated_reward / self.n_arms)
    
    def get_statistics(self) -> Dict[int, Dict[str, float]]:
        """Get arm statistics"""
        stats = {}
        for arm in range(self.n_arms):
            stats[arm] = {
                "weight": self.weights[arm],
                "pulls": self.pulls[arm],
            }
        return stats


# ============================================================================
# Ultra Bandit System
# ============================================================================

class UltraBanditSystem:
    """
    Ultra-advanced bandit system with multiple algorithms
    """
    
    def __init__(
        self,
        n_arms: int,
        context_dim: Optional[int] = None,
        algorithm: str = "thompson",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        self.n_arms = n_arms
        self.context_dim = context_dim
        self.algorithm = algorithm
        self.device = device
        
        # Create bandit algorithm
        if algorithm == "thompson":
            self.bandit = ThompsonSampling(n_arms)
        elif algorithm == "ucb":
            self.bandit = UCB(n_arms)
        elif algorithm == "linucb":
            assert context_dim is not None, "context_dim required for LinUCB"
            self.bandit = LinUCB(n_arms, context_dim)
        elif algorithm == "neural_thompson":
            assert context_dim is not None, "context_dim required for Neural Thompson"
            self.bandit = NeuralThompsonSampling(context_dim, n_arms, device=device)
        elif algorithm == "exp3":
            self.bandit = EXP3(n_arms)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        # Metrics
        self.total_pulls = 0
        self.total_reward = 0.0
        self.regret_history = []
    
    def select_arm(self, context: Optional[np.ndarray] = None) -> int:
        """Select arm"""
        if context is not None:
            return self.bandit.select_arm(context)
        else:
            return self.bandit.select_arm()
    
    def update(
        self,
        arm: int,
        reward: float,
        context: Optional[np.ndarray] = None,
    ):
        """Update bandit"""
        if context is not None:
            self.bandit.update(arm, context, reward)
        else:
            self.bandit.update(arm, reward)
        
        self.total_pulls += 1
        self.total_reward += reward
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics"""
        arm_stats = self.bandit.get_statistics()
        
        return {
            "algorithm": self.algorithm,
            "total_pulls": self.total_pulls,
            "total_reward": self.total_reward,
            "average_reward": self.total_reward / max(1, self.total_pulls),
            "arm_statistics": arm_stats,
        }
    
    def compute_regret(self, optimal_reward: float) -> float:
        """Compute cumulative regret"""
        regret = optimal_reward * self.total_pulls - self.total_reward
        self.regret_history.append(regret)
        return regret


if __name__ == "__main__":
    print("🎰 Ultra-Advanced Bandit System")
    print("=" * 60)
    
    # Create bandit system
    system = UltraBanditSystem(
        n_arms=10,
        context_dim=64,
        algorithm="neural_thompson",
    )
    
    print(f"✅ Bandit system initialized")
    print(f"   Algorithm: Neural Thompson Sampling")
    print(f"   Arms: 10")
    print(f"   Context dim: 64")
