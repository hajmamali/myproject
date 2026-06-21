"""
Comprehensive Health Check System
==================================
Centralized health checking for all system components.

این ماژول سلامت تمام کامپوننت‌های سیستم را بررسی می‌کند:
- Ollama LLM Service
- ChromaDB/VectorStore
- Neo4j/Graph (اگر فعال باشد)
- Registered Agents
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import asyncio
import logging
import os

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"  # Component is intentionally disabled


@dataclass
class ComponentHealth:
    """Health status for a component"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    checked_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at
        }


class HealthChecker:
    """
    Central health checker for all components
    
    Usage:
        checker = HealthChecker()
        results = await checker.check_all()
    """
    
    def __init__(self) -> None:
        """Initialize health checker"""
        self.logger = logging.getLogger(__name__)
    
    async def check_health(self) -> Dict[str, Any]:
        """Alias for check_all"""
        return await self.check_all()

    async def check_ollama(self) -> ComponentHealth:
        """
        Check Ollama LLM service health
        
        Returns:
            ComponentHealth with status
        """
        # Check if Ollama is enabled
        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()
        
        if not settings.enable_ollama:
            return ComponentHealth(
                component="ollama",
                status=HealthStatus.DISABLED,
                message="Ollama integration is disabled in this runtime mode",
                details={
                    "enabled": False,
                    "mode": settings.mode
                },
                checked_at=datetime.now().isoformat()
            )
        
        try:
            from mahoun.pipelines.llm.ollama_llm import OllamaLLMService
            
            # Try to create service and check availability
            service = OllamaLLMService()
            is_available = await service._check_ollama_available()
            
            if is_available:
                # Try to list models
                models = await service.list_models()
                
                return ComponentHealth(
                    component="ollama",
                    status=HealthStatus.HEALTHY,
                    message="Ollama service is running",
                    details={
                        "available_models": models,
                        "model_count": len(models),
                        "base_url": service.base_url,
                        "enabled": True
                    },
                    checked_at=datetime.now().isoformat()
                )
            else:
                return ComponentHealth(
                    component="ollama",
                    status=HealthStatus.UNHEALTHY,
                    message="Ollama service is not available",
                    details={"base_url": service.base_url, "enabled": True},
                    checked_at=datetime.now().isoformat()
                )
                
        except Exception as e:
            self.logger.error(f"Error checking Ollama: {e}", exc_info=True)
            return ComponentHealth(
                component="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check Ollama: {str(e)}",
                details={"error": str(e), "enabled": True},
                checked_at=datetime.now().isoformat()
            )
    
    async def check_vector_store(self) -> ComponentHealth:
        """
        Check VectorStore/ChromaDB health
        
        Returns:
            ComponentHealth with status
        """
        try:
            from mahoun.pipelines.vector_store.manager import VectorStoreManager
            
            # Create manager and check
            manager = VectorStoreManager()
            
            # Try to get stats
            stats = manager.get_stats()
            
            if stats:
                return ComponentHealth(
                    component="vector_store",
                    status=HealthStatus.HEALTHY,
                    message="VectorStore is operational",
                    details={
                        "backend": manager.config.backend,
                        "collection": manager.config.collection_name,
                        "stats": stats
                    },
                    checked_at=datetime.now().isoformat()
                )
            else:
                return ComponentHealth(
                    component="vector_store",
                    status=HealthStatus.DEGRADED,
                    message="VectorStore is running but stats unavailable",
                    details={"backend": manager.config.backend},
                    checked_at=datetime.now().isoformat()
                )
                
        except Exception as e:
            self.logger.error(f"Error checking VectorStore: {e}", exc_info=True)
            return ComponentHealth(
                component="vector_store",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check VectorStore: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.now().isoformat()
            )
    
    async def check_graph(self) -> ComponentHealth:
        """
        Check Neo4j/Graph system health
        
        Returns:
            ComponentHealth with status
        """
        try:
            from mahoun.core.runtime_config import get_runtime_settings, should_skip_graph
            
            settings = get_runtime_settings()
            
            if should_skip_graph():
                return ComponentHealth(
                    component="graph",
                    status=HealthStatus.DISABLED,
                    message="Graph system is disabled (expected in desktop_minimal mode)",
                    details={
                        "enabled": False,
                        "mode": settings.mode,
                        "backend": settings.graph_backend
                    },
                    checked_at=datetime.now().isoformat()
                )
            
            # If graph is enabled, try to check Neo4j
            try:
                from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
                
                # This is a basic check - actual Neo4j connection would need more
                return ComponentHealth(
                    component="graph",
                    status=HealthStatus.HEALTHY,
                    message="Graph system is enabled",
                    details={
                        "enabled": True,
                        "backend": settings.graph_backend,
                        "neo4j_uri": settings.graph_neo4j_uri
                    },
                    checked_at=datetime.now().isoformat()
                )
            except Exception as e:
                return ComponentHealth(
                    component="graph",
                    status=HealthStatus.DEGRADED,
                    message=f"Graph enabled but not fully operational: {str(e)}",
                    details={"error": str(e)},
                    checked_at=datetime.now().isoformat()
                )
                
        except Exception as e:
            self.logger.error(f"Error checking Graph: {e}", exc_info=True)
            return ComponentHealth(
                component="graph",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check Graph: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.now().isoformat()
            )
    
    async def check_reasoning(self) -> ComponentHealth:
        """
        Check UltraReasoningService health
        
        Returns:
            ComponentHealth with status
        """
        try:
            from mahoun.reasoning.ultra_reasoning_service import UltraReasoningService
            
            # Try to create service
            service = UltraReasoningService(use_cot=False)
            
            return ComponentHealth(
                component="reasoning",
                status=HealthStatus.HEALTHY,
                message="Reasoning service is available",
                details={
                    "service": "UltraReasoningService",
                    "cot_enabled": service.use_cot,
                    "self_consistency_enabled": service.use_self_consistency
                },
                checked_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"Error checking Reasoning: {e}", exc_info=True)
            return ComponentHealth(
                component="reasoning",
                status=HealthStatus.UNHEALTHY,
                message=f"Reasoning service unavailable: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.now().isoformat()
            )
    
    async def check_agents(self) -> Dict[str, ComponentHealth]:
        """
        Check all registered agents
        
        Returns:
            Dictionary of agent_name -> ComponentHealth
        """
        results: Dict[str, Any] = {}
        try:
            from mahoun.agents import (
                UltraDocParserAgent,
                DisputeAgent,
                UltraClaimAgent,
                TimelineAgent,
                DelayAgent,
                NarrativeAgent,
                UltraContractAgent
            )
            
            agents_to_check = {
                "doc_parser": UltraDocParserAgent,
                "dispute": DisputeAgent,
                "claim": UltraClaimAgent,
                "timeline": TimelineAgent,
                "delay": DelayAgent,
                "narrative": NarrativeAgent,
                "contract": UltraContractAgent
            }
            
            for agent_name, agent_class in agents_to_check.items():
                try:
                    # Try to instantiate
                    agent = agent_class()
                    
                    results[agent_name] = ComponentHealth(
                        component=f"agent.{agent_name}",
                        status=HealthStatus.HEALTHY,
                        message=f"{agent_name} agent is available",
                        details={
                            "class": agent_class.__name__,
                            "initialized": agent._initialized
                        },
                        checked_at=datetime.now().isoformat()
                    )
                except Exception as e:
                    results[agent_name] = ComponentHealth(
                        component=f"agent.{agent_name}",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Failed to create {agent_name} agent: {str(e)}",
                        details={"error": str(e)},
                        checked_at=datetime.now().isoformat()
                    )
                    
        except Exception as e:
            self.logger.error(f"Error checking agents: {e}", exc_info=True)
            results["agents"] = ComponentHealth(
                component="agents",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check agents: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.now().isoformat()
            )
        
        return results
    
    async def check_refactored_modules(self) -> Dict[str, ComponentHealth]:
        """
        Check health of Refactored modules
        
        Returns:
            Dictionary of module_name -> ComponentHealth
        """
        results: Dict[str, Any] = {}
        # Check Hybrid Search
        try:
            from mahoun.retrieval.ultra_hybrid_search import UltraHybridSearch
            DEFAULT_DENSE_WEIGHT = 0.7  # Default value
            
            # Try to create instance
            search = UltraHybridSearch()
            # Initialize if method exists
            if hasattr(search, 'initialize'):
                await search.initialize()
            
            # Check basic functionality
            results["refactored.hybrid_search"] = ComponentHealth(
                component="refactored.hybrid_search",
                status=HealthStatus.HEALTHY,
                message="UltraHybridSearch module is operational",
                details={
                    "class": "UltraHybridSearch",
                    "module": "mahoun.retrieval.ultra_hybrid_search",
                },
                checked_at=datetime.now().isoformat()
            )
        except Exception as e:
            self.logger.error(f"Error checking HybridSearch: {e}", exc_info=True)
            results["refactored.hybrid_search"] = ComponentHealth(
                component="refactored.hybrid_search",
                status=HealthStatus.UNHEALTHY,
                message=f"HybridSearch check failed: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.now().isoformat()
            )
        
        # Check Gaussian Process
        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()
        
        if not settings.enable_gaussian_process:
            results["refactored.gaussian_process"] = ComponentHealth(
                component="refactored.gaussian_process",
                status=HealthStatus.DISABLED,
                message="GaussianProcess module is disabled in this runtime mode",
                details={"enabled": False, "mode": settings.mode},
                checked_at=datetime.now().isoformat()
            )
        else:
            try:
                from mahoun.uncertainty.gaussian_process import GaussianProcessUncertainty
                
                # Try to create instance (no need for GPConfig import)
                gp = GaussianProcessUncertainty()
                metrics = gp.get_metrics()
                
                results["refactored.gaussian_process"] = ComponentHealth(
                    component="refactored.gaussian_process",
                    status=HealthStatus.HEALTHY,
                    message="GaussianProcess module is operational",
                    details={
                        "backend": metrics.get("backend", "unknown"),
                        "is_fitted": metrics.get("is_fitted", False),
                        "using_svgp": metrics.get("using_svgp", False),
                        "fallback_active": metrics.get("fallback_active", False),
                        "enabled": True
                    },
                    checked_at=datetime.now().isoformat()
                )
            except Exception as e:
                self.logger.error(f"Error checking GaussianProcess: {e}", exc_info=True)
                results["refactored.gaussian_process"] = ComponentHealth(
                    component="refactored.gaussian_process",
                    status=HealthStatus.UNHEALTHY,
                    message=f"GaussianProcess check failed: {str(e)}",
                    details={"error": str(e), "enabled": True},
                    checked_at=datetime.now().isoformat()
                )
        
        # Check Self-Improvement (skip for health check - requires real model)
        try:
            # For health check, just verify import works
            from mahoun.self_improve.ultra_self_improvement_system import UltraSelfImprovementSystem
            
            # Mark as healthy if import succeeds (actual initialization requires real model)
            results["refactored.self_improvement"] = ComponentHealth(
                component="refactored.self_improvement",
                status=HealthStatus.HEALTHY,
                message="UltraSelfImprovementSystem import successful (requires real model for full functionality)",
                details={
                    "class": "UltraSelfImprovementSystem",
                    "module": "mahoun.self_improve.ultra_self_improvement_system",
                    "note": "Full initialization requires PyTorch model with parameters()"
                },
                checked_at=datetime.now().isoformat()
            )
        except Exception as e:
            self.logger.error(f"Error checking SelfImprovement: {e}", exc_info=True)
            results["refactored.self_improvement"] = ComponentHealth(
                component="refactored.self_improvement",
                status=HealthStatus.UNHEALTHY,
                message=f"SelfImprovement check failed: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.now().isoformat()
            )
        
        return results
    
    async def check_databases(self) -> Dict[str, ComponentHealth]:
        """
        Check database connections (PostgreSQL, Redis)
        
        Returns:
            Dictionary of db_name -> ComponentHealth
        """
        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()
        
        results: Dict[str, Any] = {}
        # Check PostgreSQL
        
        # Test mode / Disabled check
        if os.getenv("MAHOUN_MODE") == "test" or not settings.enable_postgres:
            results["postgresql"] = ComponentHealth(
                component="postgresql",
                status=HealthStatus.DISABLED,
                message="PostgreSQL is disabled (Test mode or explicitly off)",
                details={"enabled": False, "mode": settings.mode, "test_mode": os.getenv("MAHOUN_MODE") == "test"},
                checked_at=datetime.now().isoformat()
            )
        else:
            try:
                from api.database import postgres_pool
                
                if postgres_pool is None:
                    results["postgresql"] = ComponentHealth(
                        component="postgresql",
                        status=HealthStatus.UNHEALTHY,
                        message="PostgreSQL connection pool not initialized",
                        details={"enabled": True, "connected": False},
                        checked_at=datetime.now().isoformat()
                    )
                else:
                    # Use pool directly to avoid async generator issue
                    async with postgres_pool.acquire() as conn:
                        result = await conn.fetchval("SELECT 1")
                        if result == 1:
                            results["postgresql"] = ComponentHealth(
                                component="postgresql",
                                status=HealthStatus.HEALTHY,
                                message="PostgreSQL is connected",
                                details={"connected": True, "enabled": True},
                                checked_at=datetime.now().isoformat()
                            )
                        else:
                            results["postgresql"] = ComponentHealth(
                                component="postgresql",
                                status=HealthStatus.DEGRADED,
                                message="PostgreSQL connection issue",
                                details={"connected": True, "query_result": result, "enabled": True},
                                checked_at=datetime.now().isoformat()
                            )
            except Exception as e:
                self.logger.debug(f"PostgreSQL health check failed: {e}")
                results["postgresql"] = ComponentHealth(
                    component="postgresql",
                    status=HealthStatus.UNHEALTHY,
                    message=f"PostgreSQL check failed: {str(e)}",
                    details={"error": str(e), "enabled": True},
                    checked_at=datetime.now().isoformat()
                )
        
        # Check Redis
        if os.getenv("MAHOUN_MODE") == "test" or not settings.enable_redis:
            results["redis"] = ComponentHealth(
                component="redis",
                status=HealthStatus.DISABLED,
                message="Redis is disabled (Test mode or explicitly off)",
                details={"enabled": False, "mode": settings.mode, "test_mode": os.getenv("MAHOUN_MODE") == "test"},
                checked_at=datetime.now().isoformat()
            )
        else:
            try:
                import redis.asyncio as redis
                
                # Try to get Redis connection
                redis_url = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                
                r = redis.Redis(host=redis_url, port=redis_port, decode_responses=True)
                await r.ping()
                await r.close()
                
                results["redis"] = ComponentHealth(
                    component="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis is connected",
                    details={"connected": True, "host": redis_url, "port": redis_port, "enabled": True},
                    checked_at=datetime.now().isoformat()
                )
            except Exception as e:
                self.logger.debug(f"Redis health check failed: {e}")
                results["redis"] = ComponentHealth(
                    component="redis",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Redis check failed: {str(e)}",
                    details={"error": str(e), "enabled": True},
                    checked_at=datetime.now().isoformat()
                )
        
        return results
    
    async def check_all(self) -> Dict[str, Any]:
        """
        Run all health checks concurrently and format according to Contract
        
        Returns:
            Dictionary with health check results matching Contract schema
        """
        import time
        # Run checks concurrently
        ollama_task = asyncio.create_task(self.check_ollama())
        vector_task = asyncio.create_task(self.check_vector_store())
        graph_task = asyncio.create_task(self.check_graph())
        reasoning_task = asyncio.create_task(self.check_reasoning())
        agents_task = asyncio.create_task(self.check_agents())
        refactored_task = asyncio.create_task(self.check_refactored_modules())
        databases_task = asyncio.create_task(self.check_databases())
        
        # Wait for all
        ollama_health = await ollama_task
        vector_health = await vector_task
        graph_health = await graph_task
        reasoning_health = await reasoning_task
        agents_health = await agents_task
        refactored_health = await refactored_task
        databases_health = await databases_task

        # 1. Determine Overall Core Status
        # Core includes: Vector Store, Reasoning, Ollama (if critical)
        core_healthy = all(c.status == HealthStatus.HEALTHY for c in [vector_health, reasoning_health])
        
        if vector_health.status == HealthStatus.UNHEALTHY or reasoning_health.status == HealthStatus.UNHEALTHY:
            core_status = "FAILED"
        elif not core_healthy:
            core_status = "DEGRADED"
        else:
            core_status = "HEALTHY"

        # Check if agents health check itself failed (outer except)
        agents_failed = "agents" in agents_health and len(agents_health) == 1
        components_map: Dict[str, Any] = {
            "ollama": ollama_health.to_dict(),
            "vector_store": vector_health.to_dict(),
            "graph": graph_health.to_dict(),
            "reasoning": reasoning_health.to_dict(),
            "postgresql": databases_health.get("postgresql").to_dict() if databases_health.get("postgresql") else {"status": "unknown"},  # type: ignore[union-attr]
            "redis": databases_health.get("redis").to_dict() if databases_health.get("redis") else {"status": "unknown"}  # type: ignore[union-attr]
        }
        
        # Add agents and refactored modules
        for name, health in agents_health.items():
            components_map[f"agent.{name}"] = health.to_dict()
        for name, health in refactored_health.items():
            components_map[name] = health.to_dict()

        # 3. Build Contract-Compliant Response
        response = {
            "status": "HEALTHY", 
            "core": {
                "status": core_status,
                "import_safe": not agents_failed, 
                "uptime_sec": int(time.clock_gettime(time.CLOCK_MONOTONIC))
            },
            "graph": {
                 "status": graph_health.status.value.upper(),
                 "reason": graph_health.message
            },
            "agents": {
                "status": "READY" if not agents_failed and all(a.status == HealthStatus.HEALTHY for a in agents_health.values()) else "FAILED" if agents_failed else "DEGRADED",
                "count": 0 if agents_failed else len(agents_health)
            },
            "self_improve": {
                "status": "DISABLED",
                "reason": "Not verified or disabled"
            },
            "components": components_map # Added detailed breakdown for observability
        }
        
        # Self-improve status update
        si_health = refactored_health.get("refactored.self_improvement")
        if si_health is not None:
            response["self_improve"]["status"] = "ENABLED" if si_health.status == HealthStatus.HEALTHY else "DISABLED"  # type: ignore[index]
            response["self_improve"]["reason"] = si_health.message  # type: ignore[index]

        # 4. Calculate Global Status
        if core_status == "FAILED" or agents_failed:
            response["status"] = "FAILED"
        elif core_status == "DEGRADED" or response["agents"]["status"] != "READY":  # type: ignore[index]
            response["status"] = "DEGRADED"
        elif graph_health.status == HealthStatus.UNHEALTHY:
            response["status"] = "DEGRADED"

        return response
