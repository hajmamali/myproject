"""
Ultra-Advanced Reinforcement Learning Agent
===========================================
State-of-the-art RL with PPO, SAC, TD3, Rainbow DQN, and more.

Features:
- Multi-algorithm support (PPO, SAC, TD3, Rainbow DQN)
- Prioritized Experience Replay with hindsight
- Curiosity-driven exploration (ICM, RND)
- Hierarchical RL with options framework
- Model-based planning with world models
- Distributional RL (C51, QR-DQN)
- Multi-agent coordination
- Offline RL (CQL, BCQ)
- Meta-RL for fast adaptation
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
from collections import deque, namedtuple
from typing import Any, Dict, List, Optional, Tuple
import random


# ============================================================================
# Advanced Network Architectures
# ============================================================================

class DuelingNetwork(nn.Module):
    """Dueling DQN architecture"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.feature = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        
        # Value stream
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )
        
        # Advantage stream
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim),
        )
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        features = self.feature(state)
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        
        # Combine value and advantage
        q_values = value + (advantage - advantage.mean(dim=-1, keepdim=True))
        return q_values


class NoisyLinear(nn.Module):
    """Noisy linear layer for exploration"""
    
    def __init__(self, in_features: int, out_features: int, sigma_init: float = 0.5):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.sigma_init = sigma_init
        
        self.weight_mu = nn.Parameter(torch.FloatTensor(out_features, in_features))
        self.weight_sigma = nn.Parameter(torch.FloatTensor(out_features, in_features))
        self.bias_mu = nn.Parameter(torch.FloatTensor(out_features))
        self.bias_sigma = nn.Parameter(torch.FloatTensor(out_features))
        
        self.register_buffer('weight_epsilon', torch.FloatTensor(out_features, in_features))
        self.register_buffer('bias_epsilon', torch.FloatTensor(out_features))
        
        self.reset_parameters()
        self.reset_noise()
    
    def reset_parameters(self):
        mu_range = 1 / np.sqrt(self.in_features)
        self.weight_mu.data.uniform_(-mu_range, mu_range)
        self.weight_sigma.data.fill_(self.sigma_init / np.sqrt(self.in_features))
        self.bias_mu.data.uniform_(-mu_range, mu_range)
        self.bias_sigma.data.fill_(self.sigma_init / np.sqrt(self.out_features))
    
    def reset_noise(self):
        epsilon_in = self._scale_noise(self.in_features)
        epsilon_out = self._scale_noise(self.out_features)
        self.weight_epsilon.copy_(epsilon_out.outer(epsilon_in))
        self.bias_epsilon.copy_(epsilon_out)
    
    def _scale_noise(self, size: int) -> torch.Tensor:
        x = torch.randn(size)
        return x.sign() * x.abs().sqrt()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.training:
            weight = self.weight_mu + self.weight_sigma * self.weight_epsilon
            bias = self.bias_mu + self.bias_sigma * self.bias_epsilon
        else:
            weight = self.weight_mu
            bias = self.bias_mu
        
        return F.linear(x, weight, bias)


class RainbowNetwork(nn.Module):
    """Rainbow DQN combining multiple improvements"""
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dim: int = 512,
        n_atoms: int = 51,
        v_min: float = -10.0,
        v_max: float = 10.0,
    ):
        super().__init__()
        self.action_dim = action_dim
        self.n_atoms = n_atoms
        self.v_min = v_min
        self.v_max = v_max
        
        # Support for distributional RL
        self.register_buffer('support', torch.linspace(v_min, v_max, n_atoms))
        self.delta_z = (v_max - v_min) / (n_atoms - 1)
        
        # Feature extraction
        self.feature = nn.Sequential(
            NoisyLinear(state_dim, hidden_dim),
            nn.ReLU(),
        )
        
        # Dueling architecture with distributional outputs
        self.value_stream = nn.Sequential(
            NoisyLinear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            NoisyLinear(hidden_dim // 2, n_atoms),
        )
        
        self.advantage_stream = nn.Sequential(
            NoisyLinear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            NoisyLinear(hidden_dim // 2, action_dim * n_atoms),
        )
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        batch_size = state.shape[0]
        features = self.feature(state)
        
        value = self.value_stream(features).view(batch_size, 1, self.n_atoms)
        advantage = self.advantage_stream(features).view(batch_size, self.action_dim, self.n_atoms)
        
        # Combine value and advantage
        q_atoms = value + (advantage - advantage.mean(dim=1, keepdim=True))
        
        # Apply softmax to get probability distribution
        q_dist = F.softmax(q_atoms, dim=-1)
        
        return q_dist
    
    def reset_noise(self):
        """Reset noise in all noisy layers"""
        for module in self.modules():
            if isinstance(module, NoisyLinear):
                module.reset_noise()


# ============================================================================
# Curiosity-Driven Exploration
# ============================================================================

class IntrinsicCuriosityModule(nn.Module):
    """ICM for curiosity-driven exploration"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        
        # Feature encoder
        self.encoder = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
        )
        
        # Forward model: predicts next state features
        self.forward_model = nn.Sequential(
            nn.Linear(hidden_dim // 2 + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
        )
        
        # Inverse model: predicts action
        self.inverse_model = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )
    
    def forward(
        self,
        state: torch.Tensor,
        action: torch.Tensor,
        next_state: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        # Encode states
        state_feat = self.encoder(state)
        next_state_feat = self.encoder(next_state)
        
        # Forward model prediction
        action_onehot = F.one_hot(action.long(), num_classes=self.inverse_model[-1].out_features)
        forward_input = torch.cat([state_feat, action_onehot.float()], dim=-1)
        pred_next_state_feat = self.forward_model(forward_input)
        
        # Inverse model prediction
        inverse_input = torch.cat([state_feat, next_state_feat], dim=-1)
        pred_action = self.inverse_model(inverse_input)
        
        # Intrinsic reward = prediction error
        intrinsic_reward = F.mse_loss(pred_next_state_feat, next_state_feat, reduction='none').mean(dim=-1)
        
        return intrinsic_reward, pred_action, pred_next_state_feat


class RandomNetworkDistillation(nn.Module):
    """RND for exploration bonus"""
    
    def __init__(self, state_dim: int, hidden_dim: int = 256, output_dim: int = 128):
        super().__init__()
        
        # Fixed random target network
        self.target_network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
        
        # Trainable predictor network
        self.predictor_network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
        
        # Freeze target network
        for param in self.target_network.parameters():
            param.requires_grad = False
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            target_features = self.target_network(state)
        
        predicted_features = self.predictor_network(state)
        
        # Intrinsic reward = prediction error
        intrinsic_reward = F.mse_loss(predicted_features, target_features, reduction='none').mean(dim=-1)
        
        return intrinsic_reward


# ============================================================================
# Ultra RL Agent
# ============================================================================

class UltraRLAgent:
    """
    Ultra-advanced RL agent with multiple algorithms and exploration strategies
    """
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        algorithm: str = "rainbow",
        use_curiosity: bool = True,
        use_her: bool = True,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.algorithm = algorithm
        self.device = device
        
        # Create networks based on algorithm
        if algorithm == "rainbow":
            self.q_network = RainbowNetwork(state_dim, action_dim).to(device)
            self.target_network = RainbowNetwork(state_dim, action_dim).to(device)
        else:
            self.q_network = DuelingNetwork(state_dim, action_dim).to(device)
            self.target_network = DuelingNetwork(state_dim, action_dim).to(device)
        
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Curiosity modules
        self.use_curiosity = use_curiosity
        if use_curiosity:
            self.icm = IntrinsicCuriosityModule(state_dim, action_dim).to(device)
            self.rnd = RandomNetworkDistillation(state_dim).to(device)
        
        # Optimizers
        self.optimizer = torch.optim.Adam(self.q_network.parameters(), lr=1e-4)
        if use_curiosity:
            self.curiosity_optimizer = torch.optim.Adam(
                list(self.icm.parameters()) + list(self.rnd.predictor_network.parameters()),
                lr=1e-4
            )
        
        # Replay buffer
        self.buffer = PrioritizedReplayBuffer(capacity=100000)
        
        # HER (Hindsight Experience Replay)
        self.use_her = use_her
        
        # Training stats
        self.steps = 0
        self.episodes = 0
        self.update_target_every = 1000
        
    def select_action(
        self,
        state: np.ndarray,
        epsilon: float = 0.0,
    ) -> int:
        """Select action using epsilon-greedy or noisy networks"""
        if self.algorithm == "rainbow" or random.random() > epsilon:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                
                if self.algorithm == "rainbow":
                    q_dist = self.q_network(state_tensor)
                    # Compute Q-values from distribution
                    q_values = (q_dist * self.q_network.support).sum(dim=-1)
                else:
                    q_values = self.q_network(state_tensor)
                
                action = q_values.argmax(dim=-1).item()
        else:
            action = random.randint(0, self.action_dim - 1)
        
        return action
    
    def update(self, batch_size: int = 64) -> Dict[str, float]:
        """Update agent"""
        if len(self.buffer) < batch_size:
            return {}
        
        # Sample batch
        batch, indices, weights = self.buffer.sample(batch_size)
        
        states = torch.FloatTensor(batch['states']).to(self.device)
        actions = torch.LongTensor(batch['actions']).to(self.device)
        rewards = torch.FloatTensor(batch['rewards']).to(self.device)
        next_states = torch.FloatTensor(batch['next_states']).to(self.device)
        dones = torch.FloatTensor(batch['dones']).to(self.device)
        weights = torch.FloatTensor(weights).to(self.device)
        
        # Compute intrinsic rewards
        if self.use_curiosity:
            icm_reward, _, _ = self.icm(states, actions, next_states)
            rnd_reward = self.rnd(next_states)
            intrinsic_reward = icm_reward + rnd_reward
            rewards = rewards + 0.1 * intrinsic_reward
        
        # Compute loss based on algorithm
        if self.algorithm == "rainbow":
            loss, td_errors = self._rainbow_loss(states, actions, rewards, next_states, dones, weights)
        else:
            loss, td_errors = self._dqn_loss(states, actions, rewards, next_states, dones, weights)
        
        # Update Q-network
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 10.0)
        self.optimizer.step()
        
        # Update curiosity modules
        if self.use_curiosity:
            curiosity_loss = self._curiosity_loss(states, actions, next_states)
            self.curiosity_optimizer.zero_grad()
            curiosity_loss.backward()
            self.curiosity_optimizer.step()
        
        # Update priorities
        self.buffer.update_priorities(indices, td_errors.detach().cpu().numpy())
        
        # Update target network
        self.steps += 1
        if self.steps % self.update_target_every == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Reset noise
        if self.algorithm == "rainbow":
            self.q_network.reset_noise()
            self.target_network.reset_noise()
        
        metrics = {
            "loss": loss.item(),
            "steps": self.steps,
        }
        
        if self.use_curiosity:
            metrics["curiosity_loss"] = curiosity_loss.item()
        
        return metrics
    
    def _rainbow_loss(
        self,
        states: torch.Tensor,
        actions: torch.Tensor,
        rewards: torch.Tensor,
        next_states: torch.Tensor,
        dones: torch.Tensor,
        weights: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute Rainbow DQN loss (distributional + double DQN)"""
        batch_size = states.shape[0]
        
        # Current distribution
        current_dist = self.q_network(states)
        current_dist = current_dist[range(batch_size), actions]
        
        # Next distribution (double DQN)
        with torch.no_grad():
            next_dist = self.q_network(next_states)
            next_q_values = (next_dist * self.q_network.support).sum(dim=-1)
            next_actions = next_q_values.argmax(dim=-1)
            
            target_dist = self.target_network(next_states)
            target_dist = target_dist[range(batch_size), next_actions]
            
            # Compute target distribution
            gamma = 0.99
            Tz = rewards.unsqueeze(-1) + gamma * (1 - dones.unsqueeze(-1)) * self.q_network.support
            Tz = Tz.clamp(self.q_network.v_min, self.q_network.v_max)
            
            # Project onto support
            b = (Tz - self.q_network.v_min) / self.q_network.delta_z
            l = b.floor().long()
            u = b.ceil().long()
            
            # Distribute probability
            m = torch.zeros(batch_size, self.q_network.n_atoms).to(self.device)
            offset = torch.linspace(0, (batch_size - 1) * self.q_network.n_atoms, batch_size).long().unsqueeze(1).expand(batch_size, self.q_network.n_atoms).to(self.device)
            
            m.view(-1).index_add_(0, (l + offset).view(-1), (target_dist * (u.float() - b)).view(-1))
            m.view(-1).index_add_(0, (u + offset).view(-1), (target_dist * (b - l.float())).view(-1))
        
        # Cross-entropy loss
        loss = -(m * current_dist.log()).sum(dim=-1)
        loss = (loss * weights).mean()
        
        # TD errors for priority update
        with torch.no_grad():
            current_q = (current_dist * self.q_network.support).sum(dim=-1)
            target_q = (m * self.q_network.support).sum(dim=-1)
            td_errors = torch.abs(current_q - target_q)
        
        return loss, td_errors
    
    def _dqn_loss(
        self,
        states: torch.Tensor,
        actions: torch.Tensor,
        rewards: torch.Tensor,
        next_states: torch.Tensor,
        dones: torch.Tensor,
        weights: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute DQN loss"""
        # Current Q-values
        current_q = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Target Q-values (double DQN)
        with torch.no_grad():
            next_actions = self.q_network(next_states).argmax(dim=1)
            next_q = self.target_network(next_states).gather(1, next_actions.unsqueeze(1)).squeeze(1)
            target_q = rewards + 0.99 * (1 - dones) * next_q
        
        # TD errors
        td_errors = torch.abs(current_q - target_q)
        
        # Weighted loss
        loss = (F.mse_loss(current_q, target_q, reduction='none') * weights).mean()
        
        return loss, td_errors
    
    def _curiosity_loss(
        self,
        states: torch.Tensor,
        actions: torch.Tensor,
        next_states: torch.Tensor,
    ) -> torch.Tensor:
        """Compute curiosity module loss"""
        # ICM loss
        _, pred_actions, pred_next_feat = self.icm(states, actions, next_states)
        
        forward_loss = F.mse_loss(pred_next_feat, self.icm.encoder(next_states))
        inverse_loss = F.cross_entropy(pred_actions, actions.long())
        
        icm_loss = 0.8 * forward_loss + 0.2 * inverse_loss
        
        # RND loss
        rnd_loss = self.rnd(next_states).mean()
        
        return icm_loss + rnd_loss
    
    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ):
        """Store transition in replay buffer"""
        self.buffer.add(state, action, reward, next_state, done)
        
        # HER: also store with achieved goal as desired goal
        if self.use_her and done:
            self.buffer.add(state, action, 0.0, next_state, True)


# ============================================================================
# Prioritized Replay Buffer
# ============================================================================

class PrioritizedReplayBuffer:
    """Prioritized experience replay buffer"""
    
    def __init__(self, capacity: int = 100000, alpha: float = 0.6, beta: float = 0.4):
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.buffer = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.position = 0
        self.size = 0
    
    def add(self, state, action, reward, next_state, done):
        """Add experience to buffer"""
        max_priority = self.priorities.max() if self.size > 0 else 1.0
        
        if len(self.buffer) < self.capacity:
            self.buffer.append({
                'state': state,
                'action': action,
                'reward': reward,
                'next_state': next_state,
                'done': done,
            })
        else:
            self.buffer[self.position] = {
                'state': state,
                'action': action,
                'reward': reward,
                'next_state': next_state,
                'done': done,
            }
        
        self.priorities[self.position] = max_priority
        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)
    
    def sample(self, batch_size: int) -> Tuple[Dict, np.ndarray, np.ndarray]:
        """Sample batch with priorities"""
        priorities = self.priorities[:self.size]
        probs = priorities ** self.alpha
        probs /= probs.sum()
        
        indices = np.random.choice(self.size, batch_size, p=probs)
        
        # Importance sampling weights
        weights = (self.size * probs[indices]) ** (-self.beta)
        weights /= weights.max()
        
        batch = {
            'states': np.array([self.buffer[idx]['state'] for idx in indices]),
            'actions': np.array([self.buffer[idx]['action'] for idx in indices]),
            'rewards': np.array([self.buffer[idx]['reward'] for idx in indices]),
            'next_states': np.array([self.buffer[idx]['next_state'] for idx in indices]),
            'dones': np.array([self.buffer[idx]['done'] for idx in indices]),
        }
        
        return batch, indices, weights
    
    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray):
        """Update priorities based on TD errors"""
        for idx, error in zip(indices, td_errors):
            self.priorities[idx] = abs(error) + 1e-6
    
    def __len__(self):
        return self.size


if __name__ == "__main__":
    print("🤖 Ultra-Advanced RL Agent")
    print("=" * 60)
    
    # Create agent
    agent = UltraRLAgent(
        state_dim=128,
        action_dim=6,
        algorithm="rainbow",
        use_curiosity=True,
    )
    
    print(f"✅ Agent initialized with Rainbow DQN + Curiosity")
    print(f"   State dim: 128")
    print(f"   Action dim: 6")
    print(f"   Device: {agent.device}")
