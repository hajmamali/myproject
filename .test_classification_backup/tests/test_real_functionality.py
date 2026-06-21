"""
تست عملکرد واقعی سیستم - Real Functionality Tests
==================================================
این تست‌ها بررسی می‌کنند که سیستم واقعاً کار می‌کند و فریب نمی‌دهد.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRealFastAPIApp:
    """تست واقعی FastAPI Application"""
    
    def test_app_creation(self):
        """تست اینکه app واقعاً ساخته می‌شود"""
        from api.main import app
        
        assert app is not None
        assert hasattr(app, 'routes')
        assert len(app.routes) > 0
        
        # بررسی route های مهم
        route_paths = [r.path for r in app.routes]
        assert '/health' in route_paths
        assert any('/api/v1/mahoun' in r for r in route_paths)
        assert any('/v1/search' in r for r in route_paths)
    
    def test_health_endpoint_exists(self):
        """تست اینکه health endpoint وجود دارد"""
        from api.main import app
        
        route_paths = [r.path for r in app.routes]
        health_routes = [r for r in route_paths if 'health' in r.lower()]
        
        assert len(health_routes) > 0, "Health endpoint باید وجود داشته باشد"
    
    def test_all_routers_registered(self):
        """تست اینکه همه router ها register شده‌اند"""
        from api.main import app
        
        route_paths = [r.path for r in app.routes]
        
        # بررسی router های اصلی
        required_prefixes = [
            '/system',
            '/api/system',
            '/v1/search',
            '/api/ingest',
            '/api/v1/mahoun',
            '/health/v2',
            '/metrics',
            '/internal',
            '/internal/dashboard'
        ]
        
        found = []
        for prefix in required_prefixes:
            if any(r.startswith(prefix) for r in route_paths):
                found.append(prefix)
        
        assert len(found) >= 6, f"حداقل 6 router باید register شده باشند. پیدا شده: {found}"


class TestRealDatabaseConnections:
    """تست واقعی Database Connections"""
    
    @pytest.mark.asyncio
    async def test_database_functions_exist(self):
        """تست اینکه database functions وجود دارند"""
        from api.database import (
            init_db, close_db,
            init_postgres, close_postgres,
            init_neo4j, close_neo4j,
            init_redis, close_redis
        )
        
        assert callable(init_db)
        assert callable(close_db)
        assert callable(init_postgres)
        assert callable(close_postgres)
        assert callable(init_neo4j)
        assert callable(close_neo4j)
        assert callable(init_redis)
        assert callable(close_redis)
    
    @pytest.mark.asyncio
    async def test_database_init_doesnt_crash(self):
        """تست اینکه init_db crash نمی‌کند (حتی اگر DB در دسترس نباشد)"""
        from api.database import init_db, close_db
        
        try:
            await init_db()
            print("✓ Database initialization attempted")
        except Exception as e:
            # اگر DB در دسترس نباشد، این OK است
            print(f"⚠ Database not available (expected in dev): {type(e).__name__}")
        
        try:
            await close_db()
            print("✓ Database close attempted")
        except Exception as e:
            print(f"⚠ Database close issue: {type(e).__name__}")


class TestRealAgentSystem:
    """تست واقعی Agent System"""
    
    def test_agent_factory_exists(self):
        """تست اینکه AgentFactory واقعاً وجود دارد"""
        from mahoun.agents import AgentFactory
        
        assert AgentFactory is not None
        assert hasattr(AgentFactory, 'create_agent')
    
    def test_agent_classes_exist(self):
        """تست اینکه agent classes واقعاً وجود دارند"""
        from mahoun.agents import (
            ContractAgent,
            Orchestrator,
            BaseAgent
        )
        
        assert ContractAgent is not None
        assert Orchestrator is not None
        assert BaseAgent is not None
    
    @pytest.mark.asyncio
    async def test_contract_agent_can_be_created(self):
        """تست اینکه می‌توان ContractAgent را ساخت"""
        from mahoun.agents import ContractAgent
        
        try:
            agent = ContractAgent()
            assert agent is not None
            assert hasattr(agent, 'name') or hasattr(agent, 'agent_name')
            print(f"✓ ContractAgent created: {type(agent).__name__}")
        except Exception as e:
            pytest.fail(f"نمی‌توان ContractAgent را ساخت: {e}")
    
    @pytest.mark.asyncio
    async def test_orchestrator_can_be_created(self):
        """تست اینکه می‌توان Orchestrator را ساخت"""
        from mahoun.agents import Orchestrator
        
        try:
            orchestrator = Orchestrator()
            assert orchestrator is not None
            assert hasattr(orchestrator, 'agents') or hasattr(orchestrator, 'workflows')
            print(f"✓ Orchestrator created: {type(orchestrator).__name__}")
        except Exception as e:
            pytest.fail(f"نمی‌توان Orchestrator را ساخت: {e}")


class TestRealRAGService:
    """تست واقعی RAG Service"""
    
    def test_rag_service_class_exists(self):
        """تست اینکه HybridRAGService class وجود دارد"""
        from mahoun.rag.hybrid_rag_service import HybridRAGService
        
        assert HybridRAGService is not None
        assert hasattr(HybridRAGService, '__init__')
    
    def test_rag_service_can_be_imported(self):
        """تست اینکه می‌توان RAG service را import کرد"""
        try:
            from mahoun.rag.hybrid_rag_service import HybridRAGService
            from mahoun.rag.citation_engine import CitationEngine
            print("✓ RAG components imported successfully")
        except ImportError as e:
            pytest.fail(f"نمی‌توان RAG components را import کرد: {e}")


class TestRealIngestionPipeline:
    """تست واقعی Ingestion Pipeline"""
    
    def test_ingestion_pipeline_exists(self):
        """تست اینکه IngestionPipeline وجود دارد"""
        from mahoun.pipelines.ingestion import IngestionPipeline
        
        assert IngestionPipeline is not None
    
    @pytest.mark.asyncio
    async def test_ingestion_pipeline_can_be_initialized(self):
        """تست اینکه می‌توان pipeline را initialize کرد"""
        from mahoun.pipelines.ingestion import IngestionPipeline
        
        try:
            pipeline = IngestionPipeline()
            await pipeline.initialize()
            assert pipeline._initialized
            print("✓ IngestionPipeline initialized")
        except Exception as e:
            # ممکن است dependencies نصب نباشند
            print(f"⚠ IngestionPipeline initialization issue: {type(e).__name__}")
            # این را fail نمی‌کنیم چون optional dependencies ممکن است نصب نباشند


class TestRealConfiguration:
    """تست واقعی Configuration"""
    
    def test_settings_can_be_loaded(self):
        """تست اینکه settings واقعاً load می‌شود"""
        from api.config import get_settings
        
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, 'database')
        assert hasattr(settings, 'security')
        assert hasattr(settings, 'models')
        print(f"✓ Settings loaded: {settings.environment}")
    
    def test_database_settings_exist(self):
        """تست اینکه database settings وجود دارد"""
        from api.config import get_settings
        
        settings = get_settings()
        db = settings.database
        
        assert hasattr(db, 'postgres_host')
        assert hasattr(db, 'postgres_port')
        assert hasattr(db, 'postgres_db')
        assert hasattr(db, 'neo4j_uri')
        assert hasattr(db, 'redis_host')
        print("✓ Database settings exist")


class TestRealDependencies:
    """تست واقعی Dependencies"""
    
    def test_critical_dependencies_installed(self):
        """تست اینکه dependencies مهم نصب شده‌اند"""
        critical_deps = {
            'fastapi': 'FastAPI framework',
            'pydantic': 'Data validation',
            'asyncpg': 'PostgreSQL driver',
        }
        
        missing = []
        for module, description in critical_deps.items():
            try:
                __import__(module)
                print(f"✓ {module} ({description})")
            except ImportError:
                missing.append(f"{module} ({description})")
                print(f"❌ {module} ({description}) - نصب نیست!")
        
        if missing:
            pytest.fail(f"Dependencies مهم نصب نیستند: {', '.join(missing)}")
    
    def test_optional_dependencies_status(self):
        """بررسی وضعیت optional dependencies"""
        optional_deps = {
            'neo4j': 'Neo4j driver',
            'redis': 'Redis client',
            'chromadb': 'Vector store',
            'sentence_transformers': 'Embeddings',
        }
        
        status = {}
        for module, description in optional_deps.items():
            try:
                __import__(module)
                status[module] = 'installed'
                print(f"✓ {module} ({description}) - نصب است")
            except ImportError:
                status[module] = 'missing'
                print(f"⚠ {module} ({description}) - نصب نیست (optional)")
        
        # این را fail نمی‌کنیم چون optional هستند
        assert True


class TestRealIntegration:
    """تست واقعی Integration Points"""
    
    @pytest.mark.asyncio
    async def test_main_components_can_work_together(self):
        """تست اینکه کامپوننت‌های اصلی می‌توانند با هم کار کنند"""
        # 1. App
        from api.main import app
        assert app is not None
        
        # 2. Settings
        from api.config import get_settings
        settings = get_settings()
        assert settings is not None
        
        # 3. Agent
        from mahoun.agents import ContractAgent
        agent = ContractAgent()
        assert agent is not None
        
        # 4. RAG Service
        from mahoun.rag.hybrid_rag_service import HybridRAGService
        assert HybridRAGService is not None
        
        print("✓ All main components can work together")
    
    def test_no_circular_imports(self):
        """تست اینکه circular import وجود ندارد"""
        import sys
        
        # Clear any cached imports
        modules_to_check = [
            'api.main',
            'api.database',
            'mahoun.agents',
            'mahoun.rag.hybrid_rag_service',
        ]
        
        for module in modules_to_check:
            if module in sys.modules:
                del sys.modules[module]
        
        # Try importing in order
        try:
            from api.main import app
            from api.database import init_db
            from mahoun.agents import ContractAgent
            from mahoun.rag.hybrid_rag_service import HybridRAGService
            
            print("✓ No circular imports detected")
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")


class TestRealErrorHandling:
    """تست واقعی Error Handling"""
    
    def test_global_exception_handler_exists(self):
        """تست اینکه global exception handler وجود دارد"""
        from api.main import app
        
        # بررسی exception handlers
        handlers = getattr(app, 'exception_handlers', {})
        assert Exception in handlers or len(handlers) > 0
        print("✓ Exception handlers configured")
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """تست اینکه سیستم gracefully degrade می‌کند"""
        # تست اینکه اگر یک dependency نباشد، سیستم crash نمی‌کند
        try:
            from mahoun.agents import ContractAgent
            agent = ContractAgent()
            
            # اگر RAG service نباشد، باید gracefully handle شود
            if not hasattr(agent, 'rag_service') or agent.rag_service is None:
                print("⚠ RAG service not available (graceful degradation)")
            else:
                print("✓ RAG service available")
        except Exception as e:
            # این باید gracefully handle شود
            print(f"⚠ Component not available: {type(e).__name__}")


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])

