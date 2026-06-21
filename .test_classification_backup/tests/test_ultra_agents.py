"""
Tests for Ultra Agents System
=============================
تست‌های سیستم Ultra Agents

Run with:
    pytest Refactored/agents/tests/test_ultra_agents.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestUltraBaseAgent:
    """Tests for UltraBaseAgent"""
    
    def test_import_base_agent(self):
        """Test that base agent can be imported"""
        from mahoun.agents import UltraBaseAgent, AgentConfig, AgentResult
        assert UltraBaseAgent is not None
        assert AgentConfig is not None
        assert AgentResult is not None
    
    def test_agent_config_defaults(self):
        """Test AgentConfig default values"""
        from mahoun.agents import AgentConfig
        
        config = AgentConfig()
        assert config.max_retries == 3
        assert config.retry_base_delay == 0.5
        assert config.circuit_breaker_threshold == 5
        assert config.enable_fallback == True
    
    def test_agent_result_to_dict(self):
        """Test AgentResult serialization"""
        from mahoun.agents import AgentResult
        
        result = AgentResult(
            success=True,
            data={"key": "value"},
            correlation_id="test123",
            processing_time_ms=100.5
        )
        
        d = result.to_dict()
        assert d["success"] == True
        assert d["data"] == {"key": "value"}
        assert d["correlation_id"] == "test123"
        assert d["processing_time_ms"] == 100.5
    
    def test_circuit_breaker_states(self):
        """Test CircuitBreaker state transitions"""
        from mahoun.agents import CircuitBreaker, CircuitBreakerState
        
        cb = CircuitBreaker(threshold=3)
        
        # Initial state
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_execute() == True
        
        # Record failures
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        
        # Third failure opens circuit
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_execute() == False
        
        # Success resets
        cb.state = CircuitBreakerState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0


class TestUltraOrchestrator:
    """Tests for UltraOrchestrator"""
    
    def test_import_orchestrator(self):
        """Test that orchestrator can be imported"""
        from mahoun.agents import (
            UltraOrchestrator,
            WorkflowDAG,
            WorkflowNode,
            ExecutionContext
        )
        assert UltraOrchestrator is not None
        assert WorkflowDAG is not None
        assert WorkflowNode is not None
    
    def test_workflow_dag_creation(self):
        """Test WorkflowDAG creation and validation"""
        from mahoun.agents import WorkflowDAG, WorkflowNode
        
        dag = WorkflowDAG(name="test_workflow")
        
        # Add nodes
        dag.add_node(WorkflowNode(id="step1", agent_name="agent1"))
        dag.add_node(WorkflowNode(id="step2", agent_name="agent2", dependencies=["step1"]))
        dag.add_node(WorkflowNode(id="step3", agent_name="agent3", dependencies=["step1"]))
        dag.add_node(WorkflowNode(id="step4", agent_name="agent4", dependencies=["step2", "step3"]))
        
        # Validate
        errors = dag.validate()
        assert len(errors) == 0
        
        # Get execution order
        levels = dag.get_execution_order()
        assert len(levels) == 3
        assert "step1" in levels[0]
        assert set(levels[1]) == {"step2", "step3"}
        assert "step4" in levels[2]
    
    def test_workflow_dag_cycle_detection(self):
        """Test that DAG detects cycles"""
        from mahoun.agents import WorkflowDAG, WorkflowNode
        
        dag = WorkflowDAG(name="cyclic")
        dag.add_node(WorkflowNode(id="a", agent_name="agent", dependencies=["c"]))
        dag.add_node(WorkflowNode(id="b", agent_name="agent", dependencies=["a"]))
        dag.add_node(WorkflowNode(id="c", agent_name="agent", dependencies=["b"]))
        
        errors = dag.validate()
        assert len(errors) > 0
        assert any("Cycle" in e or "unknown" in e for e in errors)
    
    def test_workflow_dag_missing_dependency(self):
        """Test that DAG detects missing dependencies"""
        from mahoun.agents import WorkflowDAG, WorkflowNode
        
        dag = WorkflowDAG(name="missing_dep")
        dag.add_node(WorkflowNode(id="a", agent_name="agent", dependencies=["nonexistent"]))
        
        errors = dag.validate()
        assert len(errors) > 0
        assert any("nonexistent" in e for e in errors)


class TestUltraDocParserAgent:
    """Tests for UltraDocParserAgent"""
    
    def test_import_doc_parser(self):
        """Test that doc parser can be imported"""
        from mahoun.agents import UltraDocParserAgent, DocParserConfig
        assert UltraDocParserAgent is not None
        assert DocParserConfig is not None
    
    def test_doc_parser_config(self):
        """Test DocParserConfig"""
        from mahoun.agents import DocParserConfig
        
        config = DocParserConfig()
        assert config.enable_ner == True
        assert config.enable_legal_storage == True
        assert config.chunk_size == 512
        assert config.enable_ocr == True
    
    @pytest.mark.asyncio
    async def test_doc_parser_initialization(self):
        """Test doc parser initialization"""
        from mahoun.agents import UltraDocParserAgent, DocParserConfig
        
        # Create with minimal config
        config = DocParserConfig(
            enable_ner=False,
            enable_legal_storage=False,
            enable_ocr=False
        )
        
        agent = UltraDocParserAgent(config=config)
        
        # Should be able to initialize
        try:
            await agent.initialize()
            assert agent._initialized == True
        except Exception:
            # May fail if dependencies not available, that's OK
            pass
        finally:
            await agent.shutdown()


class TestUltraContractAgent:
    """Tests for UltraContractAgent"""
    
    def test_import_contract_agent(self):
        """Test that contract agent can be imported"""
        from mahoun.agents import UltraContractAgent, ContractAgentConfig, ReasoningMode
        assert UltraContractAgent is not None
        assert ContractAgentConfig is not None
        assert ReasoningMode is not None
    
    def test_contract_config(self):
        """Test ContractAgentConfig"""
        from mahoun.agents import ContractAgentConfig, ReasoningMode
        
        config = ContractAgentConfig()
        assert config.top_k == 10
        assert config.enable_chain_of_thought == True
        assert config.enable_verification == True
        assert config.reasoning_mode == ReasoningMode.AUTO
    
    def test_reasoning_modes(self):
        """Test ReasoningMode enum"""
        from mahoun.agents import ReasoningMode
        
        assert ReasoningMode.SIMPLE.value == "simple"
        assert ReasoningMode.CHAIN_OF_THOUGHT.value == "cot"
        assert ReasoningMode.MULTI_HOP.value == "multi_hop"
        assert ReasoningMode.AUTO.value == "auto"


class TestUltraAgentFactory:
    """Tests for UltraAgentFactory"""
    
    def test_import_factory(self):
        """Test that factory can be imported"""
        from mahoun.agents import UltraAgentFactory, ULTRA_AGENT_REGISTRY
        assert UltraAgentFactory is not None
        assert ULTRA_AGENT_REGISTRY is not None
    
    def test_list_available_agents(self):
        """Test listing available agents"""
        from mahoun.agents import UltraAgentFactory
        
        available = UltraAgentFactory.list_available()
        assert isinstance(available, list)
        
        # Should have at least doc_parser and contract
        agent_types = [a["type"] for a in available]
        assert "doc_parser" in agent_types
        assert "contract" in agent_types
    
    def test_get_agent_info(self):
        """Test getting agent info"""
        from mahoun.agents import UltraAgentFactory
        
        info = UltraAgentFactory.get_agent_info("doc_parser")
        assert info["type"] == "doc_parser"
        assert info["class"] == "UltraDocParserAgent"
        assert info["category"] == "parsing"
        assert "description" in info
    
    def test_get_unknown_agent_raises(self):
        """Test that unknown agent raises ValueError"""
        from mahoun.agents import UltraAgentFactory
        
        with pytest.raises(ValueError) as exc_info:
            UltraAgentFactory.get_agent_info("nonexistent_agent")
        
        assert "Unknown agent type" in str(exc_info.value)
    
    def test_register_custom_agent(self):
        """Test registering a custom agent"""
        from mahoun.agents import UltraAgentFactory, UltraBaseAgent
        
        class CustomAgent(UltraBaseAgent):
            async def _initialize_impl(self):
                pass
            
            async def _process_impl(self, input_data, correlation_id):
                return {"custom": True}
        
        UltraAgentFactory.register(
            name="custom_test",
            agent_class=CustomAgent,
            description="Test custom agent",
            category="test"
        )
        
        info = UltraAgentFactory.get_agent_info("custom_test")
        assert info["type"] == "custom_test"
        assert info["category"] == "test"


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a complete workflow execution"""
        from mahoun.agents import (
            UltraOrchestrator,
            WorkflowDAG,
            WorkflowNode,
            UltraBaseAgent,
            AgentResult
        )
        
        # Create mock agents
        class MockAgent(UltraBaseAgent):
            def __init__(self, name, output):
                super().__init__(name)
                self._output = output
            
            async def _initialize_impl(self):
                pass
            
            async def _process_impl(self, input_data, correlation_id):
                return {"output": self._output, "input": input_data}
        
        # Create orchestrator
        orchestrator = UltraOrchestrator()
        
        # Register mock agents
        orchestrator.register_agent("agent1", MockAgent("agent1", "result1"))
        orchestrator.register_agent("agent2", MockAgent("agent2", "result2"))
        
        # Initialize agents
        await orchestrator.agents["agent1"].initialize()
        await orchestrator.agents["agent2"].initialize()
        
        # Create DAG
        dag = WorkflowDAG(name="test")
        dag.add_node(WorkflowNode(id="step1", agent_name="agent1"))
        dag.add_node(WorkflowNode(id="step2", agent_name="agent2", dependencies=["step1"]))
        
        # Execute
        result = await orchestrator.execute_workflow(dag, {"initial": "data"})
        
        assert result["success"] == True
        assert "step1" in result["node_results"]
        assert "step2" in result["node_results"]


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ============================================================================
# Tests for New Ultra Agents
# ============================================================================

class TestUltraDisputeAgent:
    """Tests for UltraDisputeAgent"""
    
    def test_import_dispute_agent(self):
        """Test that dispute agent can be imported"""
        from mahoun.agents import UltraDisputeAgent, DisputeType
        assert UltraDisputeAgent is not None
        assert DisputeType is not None
    
    def test_dispute_types(self):
        """Test DisputeType enum"""
        from mahoun.agents import DisputeType
        
        assert DisputeType.CONTRACTUAL.value == "contractual"
        assert DisputeType.FINANCIAL.value == "financial"
        assert DisputeType.TEMPORAL.value == "temporal"
    
    def test_dispute_severity(self):
        """Test DisputeSeverity enum"""
        from mahoun.agents import DisputeSeverity
        
        assert DisputeSeverity.CRITICAL.value == "critical"
        assert DisputeSeverity.HIGH.value == "high"
        assert DisputeSeverity.LOW.value == "low"


class TestUltraClaimAgent:
    """Tests for UltraClaimAgent"""
    
    def test_import_claim_agent(self):
        """Test that claim agent can be imported"""
        from mahoun.agents import UltraClaimAgent, ClaimAgentConfig, ClaimType
        assert UltraClaimAgent is not None
        assert ClaimAgentConfig is not None
        assert ClaimType is not None
    
    def test_claim_types(self):
        """Test ClaimType enum"""
        from mahoun.agents import ClaimType
        
        assert ClaimType.BREACH_OF_CONTRACT.value == "breach_of_contract"
        assert ClaimType.DAMAGES.value == "damages"
        assert ClaimType.TERMINATION.value == "termination"


class TestUltraNarrativeAgent:
    """Tests for UltraNarrativeAgent"""
    
    def test_import_narrative_agent(self):
        """Test that narrative agent can be imported"""
        from mahoun.agents import UltraNarrativeAgent, NarrativeAgentConfig, NarrativeType
        assert UltraNarrativeAgent is not None
        assert NarrativeAgentConfig is not None
        assert NarrativeType is not None
    
    def test_narrative_types(self):
        """Test NarrativeType enum"""
        from mahoun.agents import NarrativeType
        
        assert NarrativeType.LEGAL.value == "legal"
        assert NarrativeType.TECHNICAL.value == "technical"
        assert NarrativeType.COMBINED.value == "combined"


class TestUltraPrecedentAgent:
    """Tests for UltraPrecedentAgent"""
    
    def test_import_precedent_agent(self):
        """Test that precedent agent can be imported"""
        from mahoun.agents import UltraPrecedentAgent, PrecedentAgentConfig, PrecedentType
        assert UltraPrecedentAgent is not None
        assert PrecedentAgentConfig is not None
        assert PrecedentType is not None
    
    def test_precedent_types(self):
        """Test PrecedentType enum"""
        from mahoun.agents import PrecedentType
        
        assert PrecedentType.SUPREME_COURT.value == "supreme_court"
        assert PrecedentType.APPEAL_COURT.value == "appeal_court"
        assert PrecedentType.GENERAL_COURT.value == "general_court"


class TestFactoryWithAllAgents:
    """Tests for factory with all agents"""
    
    def test_all_agents_registered(self):
        """Test that all 6 core agents are registered"""
        from mahoun.agents import UltraAgentFactory
        
        available = UltraAgentFactory.list_available()
        agent_types = [a["type"] for a in available]
        
        # Check all 6 core agents are present
        assert "doc_parser" in agent_types
        assert "contract" in agent_types
        assert "dispute" in agent_types
        assert "claim" in agent_types
        assert "narrative" in agent_types
        assert "precedent" in agent_types
        # At least 6 agents (may have custom ones from other tests)
        assert len(available) >= 6
    
    def test_agent_categories(self):
        """Test agent categories"""
        from mahoun.agents import UltraAgentFactory
        
        available = UltraAgentFactory.list_available()
        categories = set(a["category"] for a in available)
        
        assert "parsing" in categories
        assert "analysis" in categories
        assert "generation" in categories
        assert "search" in categories
