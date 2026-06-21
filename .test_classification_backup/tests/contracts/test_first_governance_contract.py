"""
Verification test for NoUnauthorizedGraphMutationContract.
"""

import pytest
from mahoun.contracts.base import ContractState
from mahoun.contracts.engine import ContractEngine
from mahoun.contracts.implementations.graph_contracts import NoUnauthorizedGraphMutationContract

def test_graph_mutation_contract_verification():
    """
    Demonstrate contract-based verification for graph mutations.
    """
    engine = ContractEngine()
    contract = NoUnauthorizedGraphMutationContract()
    engine.register_contract(contract)
    
    # 1. AUTHORIZED SCENARIO
    initial_state = ContractState(
        context={"execution_mode": "STRICT", "governance_active": True},
        data={},
        history=[]
    )
    
    safe_mutation = "CREATE (n:Fact {id: 1})"
    violations = engine.run_validation(initial_state, safe_mutation)
    
    assert len(violations) == 0, "Authorized mutation erroneously flagged as violation"
    
    # 2. UNAUTHORIZED SCENARIO (Adversarial)
    malicious_state = ContractState(
        context={"execution_mode": "STRICT", "governance_active": False}, # BYPASS ATTEMPT
        data={},
        history=[]
    )
    
    bad_mutation = "SET n.property = 'hacked'"
    violations = engine.run_validation(malicious_state, bad_mutation)
    
    assert len(violations) > 0, "Security Failure: Unauthorized mutation was NOT blocked by contract"
    assert violations[0]["type"] == "FORBIDDEN_ACTION"
    assert violations[0]["contract"] == "NoUnauthorizedGraphMutation"

if __name__ == "__main__":
    pytest.main([__file__])
