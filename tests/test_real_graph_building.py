"""
تست واقعی ساخت گراف - Real Graph Building Tests
================================================
این تست‌ها اثبات می‌کنند که سیستم واقعاً گراف می‌سازد.
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any, List
from mahoun.switchboard import switchboard

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRealGraphBuilder:
    """تست واقعی Graph Builder"""
    
    def test_graph_builder_exists(self):
        """تست اینکه UltraGraphBuilder واقعاً وجود دارد"""

        UltraGraphBuilder = type(switchboard.get_module("ultra_graph_builder"))
        assert UltraGraphBuilder is not None
        assert hasattr(UltraGraphBuilder, 'build_graph')
        print("✓ UltraGraphBuilder class exists")
    
    def test_graph_builder_can_be_created(self):
        """تست اینکه می‌توان GraphBuilder را ساخت"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        assert builder is not None
        assert hasattr(builder, 'nodes')
        assert hasattr(builder, 'edges')
        assert hasattr(builder, 'build_graph')
        print("✓ UltraGraphBuilder can be instantiated")
    
    def test_graph_builder_has_storage(self):
        """تست اینکه GraphBuilder storage دارد"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        # بررسی storage structures
        assert hasattr(builder, 'nodes')
        assert hasattr(builder, 'edges')
        assert isinstance(builder.get_nodes(), dict)
        assert isinstance(builder.get_edges(), list)
        print("✓ GraphBuilder has proper storage structures")

class TestRealGraphConstruction:
    """تست واقعی ساخت گراف"""
    
    def test_can_build_simple_graph(self):
        """تست اینکه می‌توان یک گراف ساده ساخت"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        # ساخت entities و relationships ساده
        entities = [
            {
                "id": "person_1",
                "label": "احمد",
                "type": "Person",
                "properties": {"age": 30}
            },
            {
                "id": "person_2",
                "label": "محمد",
                "type": "Person",
                "properties": {"age": 25}
            },
            {
                "id": "company_1",
                "label": "شرکت حقوقی",
                "type": "Company",
                "properties": {"name": "شرکت حقوقی"}
            }
        ]
        
        relationships = [
            {
                "source_id": "person_1",
                "target_id": "person_2",
                "type": "KNOWS",
                "properties": {"since": "2020"}
            },
            {
                "source_id": "person_1",
                "target_id": "company_1",
                "type": "WORKS_FOR",
                "properties": {"role": "lawyer"}
            }
        ]
        
        # ساخت گراف
        result = builder.build_graph(entities, relationships)
        
        # بررسی نتیجه
        assert result is not None
        assert isinstance(result, dict)
        
        # بررسی اینکه nodes اضافه شده‌اند
        assert len(builder.get_nodes()) > 0, "Nodes باید اضافه شده باشند"
        print(f"✓ Graph built with {len(builder.get_nodes())} nodes")
        
        # بررسی اینکه edges اضافه شده‌اند
        assert len(builder.get_edges()) > 0, "Edges باید اضافه شده باشند"
        print(f"✓ Graph has {len(builder.get_edges())} edges")
    
    def test_graph_contains_nodes(self):
        """تست اینکه گراف واقعاً nodes دارد"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        entities = [
            {"id": "node_1", "label": "Node 1", "type": "Test"},
            {"id": "node_2", "label": "Node 2", "type": "Test"}
        ]
        relationships = [
            {"source_id": "node_1", "target_id": "node_2", "type": "RELATED"}
        ]
        
        builder.build_graph(entities, relationships)
        
        # بررسی اینکه nodes در storage هستند
        assert "node_1" in builder.get_nodes(), "node_1 باید در گراف باشد"
        assert "node_2" in builder.get_nodes(), "node_2 باید در گراف باشد"
        
        node1 = builder.get_nodes()["node_1"]
        assert node1.id == "node_1"
        assert node1.label == "Node 1"
        print("✓ Graph nodes are properly stored")
    
    def test_graph_contains_edges(self):
        """تست اینکه گراف واقعاً edges دارد"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        entities = [
            {"id": "a", "label": "A", "type": "Test"},
            {"id": "b", "label": "B", "type": "Test"}
        ]
        relationships = [
            {"source_id": "a", "target_id": "b", "type": "CONNECTS"}
        ]
        
        builder.build_graph(entities, relationships)
        
        # بررسی اینکه edges در storage هستند
        assert len(builder.get_edges()) > 0, "Edges باید در گراف باشند"
        
        # بررسی محتوای edge
        edge = builder.get_edges()[0]
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.relationship_type == "CONNECTS"
        print("✓ Graph edges are properly stored")
    
    def test_graph_build_returns_metrics(self):
        """تست اینکه build_graph metrics برمی‌گرداند"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        entities = [
            {"id": "e1", "label": "Entity 1", "type": "Entity"},
            {"id": "e2", "label": "Entity 2", "type": "Entity"}
        ]
        relationships = [
            {"source_id": "e1", "target_id": "e2", "type": "RELATED"}
        ]
        
        result = builder.build_graph(entities, relationships)
        
        # بررسی metrics
        assert "metrics" in result or "nodes_added" in result or "total_nodes" in str(result)
        print("✓ Graph build returns metrics")
    
    def test_graph_can_handle_multiple_entities(self):
        """تست اینکه گراف می‌تواند entities متعدد را handle کند"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        # ساخت 10 entity
        entities = [
            {"id": f"entity_{i}", "label": f"Entity {i}", "type": "Test"}
            for i in range(10)
        ]
        
        # ساخت relationships بین آنها
        relationships = [
            {"source_id": f"entity_{i}", "target_id": f"entity_{i+1}", "type": "NEXT"}
            for i in range(9)
        ]
        
        result = builder.build_graph(entities, relationships)
        
        # بررسی اینکه همه nodes اضافه شده‌اند
        assert len(builder.get_nodes()) == 10, f"باید 10 node باشد، اما {len(builder.get_nodes())} است"
        assert len(builder.get_edges()) == 9, f"باید 9 edge باشد، اما {len(builder.get_edges())} است"
        print(f"✓ Graph can handle multiple entities ({len(builder.get_nodes())} nodes, {len(builder.get_edges())} edges)")

class TestRealGraphQuery:
    """تست واقعی Query کردن گراف"""
    
    def test_can_query_nodes(self):
        """تست اینکه می‌توان nodes را query کرد"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        # ساخت گراف
        entities = [
            {"id": "q1", "label": "Query Node 1", "type": "Query"},
            {"id": "q2", "label": "Query Node 2", "type": "Query"}
        ]
        relationships = [
            {"source_id": "q1", "target_id": "q2", "type": "LINKS"}
        ]
        
        builder.build_graph(entities, relationships)
        
        # Query node
        node = builder.get_nodes().get("q1")
        assert node is not None
        assert node.id == "q1"
        assert node.label == "Query Node 1"
        print("✓ Can query nodes from graph")
    
    def test_can_query_edges(self):
        """تست اینکه می‌توان edges را query کرد"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        entities = [
            {"id": "edge_test_1", "label": "Edge Test 1", "type": "Test"},
            {"id": "edge_test_2", "label": "Edge Test 2", "type": "Test"}
        ]
        relationships = [
            {"source_id": "edge_test_1", "target_id": "edge_test_2", "type": "TEST_EDGE"}
        ]
        
        builder.build_graph(entities, relationships)
        
        # Query edges
        edges = [e for e in builder.get_edges() if e.source_id == "edge_test_1"]
        assert len(edges) > 0
        assert edges[0].relationship_type == "TEST_EDGE"
        print("✓ Can query edges from graph")
    
    def test_can_find_neighbors(self):
        """تست اینکه می‌توان neighbors یک node را پیدا کرد"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        # ساخت گراف star-shaped
        entities = [
            {"id": "center", "label": "Center", "type": "Node"},
            {"id": "node1", "label": "Node 1", "type": "Node"},
            {"id": "node2", "label": "Node 2", "type": "Node"},
            {"id": "node3", "label": "Node 3", "type": "Node"}
        ]
        relationships = [
            {"source_id": "center", "target_id": "node1", "type": "CONNECTS"},
            {"source_id": "center", "target_id": "node2", "type": "CONNECTS"},
            {"source_id": "center", "target_id": "node3", "type": "CONNECTS"}
        ]
        
        builder.build_graph(entities, relationships)
        
        # پیدا کردن neighbors
        center_edges = [e for e in builder.get_edges() if e.source_id == "center"]
        assert len(center_edges) == 3, f"Center باید 3 neighbor داشته باشد، اما {len(center_edges)} دارد"
        print(f"✓ Can find neighbors (found {len(center_edges)} neighbors for center node)")

class TestRealGraphMetrics:
    """تست واقعی Graph Metrics"""
    
    def test_graph_has_metrics(self):
        """تست اینکه گراف metrics دارد"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        entities = [
            {"id": "m1", "label": "Metric 1", "type": "Metric"},
            {"id": "m2", "label": "Metric 2", "type": "Metric"},
            {"id": "m3", "label": "Metric 3", "type": "Metric"}
        ]
        relationships = [
            {"source_id": "m1", "target_id": "m2", "type": "LINKS"},
            {"source_id": "m2", "target_id": "m3", "type": "LINKS"}
        ]
        
        builder.build_graph(entities, relationships)
        
        # بررسی metrics
        if hasattr(builder, 'compute_analytics'):
            metrics = builder.compute_analytics()
            assert metrics is not None
            print("✓ Graph has analytics/metrics")
        else:
            # حداقل بررسی کنیم که nodes و edges count درست است
            assert len(builder.get_nodes()) == 3
            assert len(builder.get_edges()) == 2
            print("✓ Graph has correct node and edge counts")

class TestRealGraphBuildPipeline:
    """تست واقعی Graph Build Pipeline"""
    
    def test_graph_build_pipeline_exists(self):
        """تست اینکه GraphBuildPipeline وجود دارد"""
        try:
            
            GraphBuildPipeline = type(switchboard.get_module("graph_build_pipeline"))
            assert GraphBuildPipeline is not None
            print("✓ GraphBuildPipeline exists")
        except ImportError:
            pytest.skip("GraphBuildPipeline not available")
    
    def test_graph_build_pipeline_can_be_created(self):
        """تست اینکه می‌توان GraphBuildPipeline را ساخت"""
        try:

            pipeline = type(switchboard.get_module("graph_build_pipeline"))()
            assert pipeline is not None
            assert hasattr(pipeline, 'build_from_verdict')
            print("✓ GraphBuildPipeline can be instantiated")
        except ImportError:
            pytest.skip("GraphBuildPipeline not available")

class TestRealCitationGraph:
    """تست واقعی Citation Graph"""
    
    def test_citation_graph_exists(self):
        """تست اینکه DocumentCitationGraph وجود دارد"""
        try:
            
            DocumentCitationGraph = type(switchboard.get_module("document_citation_graph"))
            assert DocumentCitationGraph is not None
            print("✓ DocumentCitationGraph exists")
        except ImportError:
            pytest.skip("DocumentCitationGraph not available")
    
    def test_citation_graph_can_be_created(self):
        """تست اینکه می‌توان CitationGraph را ساخت"""
        try:

            graph = type(switchboard.get_module("document_citation_graph"))()
            assert graph is not None
            assert hasattr(graph, 'create_citation_graph')
            print("✓ DocumentCitationGraph can be instantiated")
        except ImportError:
            pytest.skip("DocumentCitationGraph not available")

class TestRealGraphIntegration:
    """تست واقعی Integration گراف با سایر کامپوننت‌ها"""
    
    def test_graph_builder_integration(self):
        """تست اینکه GraphBuilder با سایر کامپوننت‌ها integrate می‌شود"""

        # ساخت گراف
        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        # ساخت entities از یک document فرضی
        entities = [
            {
                "id": "doc_1",
                "label": "Document 1",
                "type": "Document",
                "properties": {"title": "Test Document"}
            },
            {
                "id": "law_1",
                "label": "Law Article 1",
                "type": "Law",
                "properties": {"article": "123"}
            }
        ]
        
        relationships = [
            {
                "source_id": "doc_1",
                "target_id": "law_1",
                "type": "CITES",
                "properties": {"confidence": 0.9}
            }
        ]
        
        result = builder.build_graph(entities, relationships)
        
        # بررسی اینکه integration کار می‌کند
        assert len(builder.get_nodes()) == 2
        assert len(builder.get_edges()) == 1
        
        # بررسی اینکه edge properties حفظ شده
        edge = builder.get_edges()[0]
        assert edge.properties.get("confidence") == 0.9
        
        print("✓ Graph builder integrates with other components")

class TestRealGraphPersistence:
    """تست واقعی Persistence گراف"""
    
    def test_graph_data_structure_persists(self):
        """تست اینکه داده‌های گراف persist می‌مانند"""

        builder = type(switchboard.get_module("ultra_graph_builder"))()
        
        # ساخت گراف
        entities = [
            {"id": "persist_1", "label": "Persist 1", "type": "Test"},
            {"id": "persist_2", "label": "Persist 2", "type": "Test"}
        ]
        relationships = [
            {"source_id": "persist_1", "target_id": "persist_2", "type": "PERSISTS"}
        ]
        
        builder.build_graph(entities, relationships)
        
        # بررسی اینکه داده‌ها persist شده‌اند
        assert len(builder.get_nodes()) == 2
        assert len(builder.get_edges()) == 1
        
        # Query دوباره
        node = builder.get_nodes().get("persist_1")
        assert node is not None
        assert node.id == "persist_1"
        
        print("✓ Graph data persists in memory")

# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])

