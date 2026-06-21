"""
MAHOUN Graph Governance Contracts
=================================
Formal contracts for Knowledge Graph mutation and integrity.
"""

from mahoun.contracts.base import GovernanceContract, ContractState
from typing import Any, Dict

class NoUnauthorizedGraphMutationContract(GovernanceContract):
    """
    Contract: G6 - Mutation Authorization Boundary
    Domain: GRAPH
    
    Invariant: No state mutation (Neo4j SET/CREATE) may occur outside a 
    GovernedNeo4jSession and MUST produce a cryptographically signed audit receipt.
    """
    
    @property
    def name(self) -> str:
        return "NoUnauthorizedGraphMutation"

    @property
    def domain(self) -> str:
        return "GRAPH"

    def precondition(self, state: ContractState, input_data: Any) -> bool:
        """System must be initialized in a valid execution mode."""
        return "execution_mode" in state.context

    def invariant(self, state: ContractState) -> bool:
        """
        Check: Every 'mutation' in history must have a corresponding 'audit_receipt'.
        """
        mutations = [h for h in state.history if h.get("event") == "graph_mutation"]
        receipts = [h for h in state.history if h.get("event") == "audit_receipt"]
        
        # Every mutation event MUST have a preceding or concurrent receipt event
        # (Simplified for state-space validation)
        return len(receipts) >= len(mutations)

    def forbidden(self, state: ContractState, input_data: Any) -> bool:
        """
        Prohibit mutations if the input query is not wrapped in a governed context.
        """
        # If input is a query string, check if it's a mutation
        if isinstance(input_data, str):
            from mahoun.core.governance.mutation_boundary import classify_cypher
            is_mutation = classify_cypher(input_data)
            
            # If it IS a mutation but context is missing, it's FORBIDDEN
            if is_mutation and not state.context.get("governance_active", False):
                return True
                
        return False

    def transition(self, state: ContractState, input_data: Any) -> ContractState:
        """
        Record the mutation event and the audit receipt if authorized.
        """
        new_history = list(state.history)
        
        if isinstance(input_data, str):
            from mahoun.core.governance.mutation_boundary import classify_cypher
            if classify_cypher(input_data):
                # Authorized path: Add mutation and receipt
                if state.context.get("governance_active", False):
                    new_history.append({"event": "audit_receipt", "data": "signed_hash_v1"})
                    new_history.append({"event": "graph_mutation", "query": input_data})
                else:
                    # Unauthorized path: (Should be blocked by 'forbidden' but we record it for tracing)
                    new_history.append({"event": "violation_attempt", "query": input_data})
                    
        return ContractState(state.context, state.data, new_history)
