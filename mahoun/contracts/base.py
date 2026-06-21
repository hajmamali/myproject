"""
MAHOUN Governance Contract DSL
==============================
Defines the base structure for all system-level invariants and state transitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class ContractState:
    """Represents the internal state of the system for contract evaluation."""
    context: Dict[str, Any]
    data: Any
    history: List[Any]

class GovernanceContract(ABC):
    """
    Base class for all Governance Contracts.
    
    A contract defines the 'Constitutional Guardrails' for a specific domain.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The formal name of the contract."""
        pass

    @property
    @abstractmethod
    def domain(self) -> str:
        """The system domain (e.g., 'GRAPH', 'REASONING', 'AUTH')."""
        pass

    @abstractmethod
    def precondition(self, state: ContractState, input_data: Any) -> bool:
        """Check if the system is in a valid state to perform the action."""
        return True

    @abstractmethod
    def invariant(self, state: ContractState) -> bool:
        """Check if the system state remains valid after a transition."""
        return True

    @abstractmethod
    def forbidden(self, state: ContractState, input_data: Any) -> bool:
        """Check if the input or action is explicitly prohibited."""
        return False

    def transition(self, state: ContractState, input_data: Any) -> ContractState:
        """Perform a state transition. (Optional implementation)"""
        return state
