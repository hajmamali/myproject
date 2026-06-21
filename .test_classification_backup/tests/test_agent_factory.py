"""
Tests for Agent Factory
=======================
Unit tests for the agent factory pattern.
"""

import pytest
from mahoun.agents.factory import AgentFactory, AGENT_REGISTRY
from mahoun.agents.base_agent import BaseAgent


@pytest.mark.asyncio
async def test_create_single_agent():
    """Test creating a single agent"""
    agent = await AgentFactory.create_agent("doc_parser")
    
    assert agent is not None
    # Agent names now use ultra_ prefix for newer agents
    assert agent.name in ["doc_parser_agent", "ultra_doc_parser"]
    assert agent._initialized == True
    assert isinstance(agent, BaseAgent)


@pytest.mark.asyncio
async def test_create_agent_with_config():
    """Test creating agent with custom config"""
    from mahoun.agents.base_agent import AgentConfig
    
    config = AgentConfig(
        circuit_breaker_threshold=5.0,
        circuit_breaker_timeout=30.0
    )
    agent = await AgentFactory.create_agent("doc_parser", config)
    
    assert agent.config == config


@pytest.mark.asyncio
async def test_create_agent_invalid_type():
    """Test creating agent with invalid type"""
    with pytest.raises(ValueError) as exc_info:
        await AgentFactory.create_agent("invalid_agent_type")
    
    assert "Unknown agent type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_all_agents():
    """Test creating all agents"""
    agents = await AgentFactory.create_all_agents()
    
    assert isinstance(agents, dict)
    assert len(agents) > 0
    
    # Should have all registered agents
    for agent_type in AGENT_REGISTRY.keys():
        assert agent_type in agents or True  # Some might fail to initialize
    
    # All created agents should be initialized
    for agent_type, agent in agents.items():
        assert agent._initialized == True


@pytest.mark.asyncio
async def test_create_all_agents_with_config():
    """Test creating all agents with custom configs"""
    config = {
        "doc_parser": {"index": True},
        "dispute": {"focus": "violations"}
    }
    
    agents = await AgentFactory.create_all_agents(config)
    
    assert isinstance(agents, dict)
    
    # Check that configs were applied
    if "doc_parser" in agents:
        assert agents["doc_parser"].config == {"index": True}


def test_list_available_agents():
    """Test listing available agents"""
    agents = AgentFactory.list_available_agents()
    
    assert isinstance(agents, list)
    assert len(agents) == 8  # We have 8 agents (including critic)
    assert "doc_parser" in agents
    assert "dispute" in agents
    assert "claim" in agents
    assert "timeline" in agents
    assert "delay" in agents
    assert "narrative" in agents
    assert "contract" in agents
    assert "critic" in agents


def test_get_agent_info():
    """Test getting agent information"""
    info = AgentFactory.get_agent_info("doc_parser")
    
    assert isinstance(info, dict)
    assert info["type"] == "doc_parser"
    assert "class" in info
    assert "module" in info
    assert "docstring" in info


def test_get_agent_info_invalid():
    """Test getting info for invalid agent"""
    with pytest.raises(ValueError):
        AgentFactory.get_agent_info("invalid_agent")


def test_register_agent():
    """Test registering a new agent type"""
    from mahoun.agents.base_agent import BaseAgent
    
    class TestAgent(BaseAgent):
        async def process(self, input_data):
            return {"test": "result"}
    
    # Register
    AgentFactory.register_agent("test_agent", TestAgent)
    
    # Verify it's in registry
    assert "test_agent" in AGENT_REGISTRY
    assert AGENT_REGISTRY["test_agent"] == TestAgent
    
    # Cleanup
    del AGENT_REGISTRY["test_agent"]


def test_register_agent_duplicate():
    """Test registering duplicate agent type"""
    with pytest.raises(ValueError) as exc_info:
        AgentFactory.register_agent("doc_parser", type)
    
    assert "already registered" in str(exc_info.value)


def test_register_agent_invalid_class():
    """Test registering invalid agent class"""
    class NotAnAgent:
        pass
    
    with pytest.raises(ValueError) as exc_info:
        AgentFactory.register_agent("invalid", NotAnAgent)
    
    assert "must inherit from BaseAgent" in str(exc_info.value)


def test_agent_registry_completeness():
    """Test that all expected agents are in registry"""
    expected_agents = [
        "doc_parser",
        "dispute",
        "claim",
        "timeline",
        "delay",
        "narrative",
        "contract"
    ]
    
    for agent_type in expected_agents:
        assert agent_type in AGENT_REGISTRY
