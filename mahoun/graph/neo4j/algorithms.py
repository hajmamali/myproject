"""
Graph Algorithms
================

Advanced graph algorithms using Neo4j GDS.
"""


from typing import Any, Dict, List, Optional, Tuple
from mahoun.graph.neo4j.connection import Neo4jConnection, get_connection


class GraphAlgorithms:
    """Graph algorithm implementations"""
    
    def __init__(self, connection: Optional[Neo4jConnection] = None):
        self.conn = connection or get_connection()
    
    def compute_pagerank(
        self,
        node_label: str = "Document",
        rel_type: str = "CITES",
        iterations: int = 20,
        damping_factor: float = 0.85,
        write_property: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Compute PageRank scores
        
        Args:
            node_label: Node label to compute on
            rel_type: Relationship type
            iterations: Number of iterations
            damping_factor: Damping factor (0.85 typical)
            write_property: Property to write scores to
            
        Returns:
            List of (node_id, score) tuples
        """
        if write_property:
            query = f"""
            CALL gds.pageRank.write({{
                nodeProjection: '{node_label}',
                relationshipProjection: '{rel_type}',
                maxIterations: {iterations},
                dampingFactor: {damping_factor},
                writeProperty: '{write_property}'
            }})
            YIELD nodePropertiesWritten, ranIterations
            RETURN nodePropertiesWritten, ranIterations
            """
        else:
            query = f"""
            CALL gds.pageRank.stream({{
                nodeProjection: '{node_label}',
                relationshipProjection: '{rel_type}',
                maxIterations: {iterations},
                dampingFactor: {damping_factor}
            }})
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).id AS node_id, score
            ORDER BY score DESC
            """
        
        try:
            result = self.conn.execute_query(query)
            return [dict(r) for r in result]
        except Exception as e:
            print(f"⚠️  PageRank failed (GDS may not be installed): {e}")
            return self._fallback_pagerank(node_label, rel_type, iterations, damping_factor)
    
    def _fallback_pagerank(
        self,
        node_label: str,
        rel_type: str,
        iterations: int,
        damping_factor: float
    ) -> List[Dict[str, Any]]:
        """Fallback PageRank without GDS"""
        # Simple degree centrality as fallback
        query = f"""
        MATCH (n:{node_label})
        OPTIONAL MATCH (n)<-[r:{rel_type}]-()
        WITH n, count(r) AS inDegree
        RETURN n.id AS node_id, inDegree AS score
        ORDER BY score DESC
        """
        
        result = self.conn.execute_query(query)
        return [dict(r) for r in result]
    
    def detect_communities(
        self,
        node_label: str = "Document",
        rel_type: str = "CITES",
        algorithm: str = "louvain",
        write_property: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect communities in graph
        
        Args:
            node_label: Node label
            rel_type: Relationship type
            algorithm: Algorithm (louvain, label_propagation)
            write_property: Property to write community IDs to
            
        Returns:
            List of (node_id, community_id) tuples
        """
        if algorithm == "louvain":
            algo_name = "gds.louvain"
        elif algorithm == "label_propagation":
            algo_name = "gds.labelPropagation"
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        if write_property:
            query = f"""
            CALL {algo_name}.write({{
                nodeProjection: '{node_label}',
                relationshipProjection: '{rel_type}',
                writeProperty: '{write_property}'
            }})
            YIELD communityCount, modularity
            RETURN communityCount, modularity
            """
        else:
            query = f"""
            CALL {algo_name}.stream({{
                nodeProjection: '{node_label}',
                relationshipProjection: '{rel_type}'
            }})
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId).id AS node_id, communityId
            """
        
        try:
            result = self.conn.execute_query(query)
            return [dict(r) for r in result]
        except Exception as e:
            print(f"⚠️  Community detection failed: {e}")
            return []
    
    def find_shortest_path(
        self,
        from_id: str,
        to_id: str,
        node_label: str = "Document",
        rel_type: str = "CITES",
        max_depth: int = 10
    ) -> Optional[List[str]]:
        """
        Find shortest path between two nodes
        
        Args:
            from_id: Source node ID
            to_id: Target node ID
            node_label: Node label
            rel_type: Relationship type
            max_depth: Maximum path depth
            
        Returns:
            List of node IDs in path, or None if no path
        """
        query = f"""
        MATCH path = shortestPath(
            (a:{node_label} {{id: $from_id}})-[:{rel_type}*..{max_depth}]->(b:{node_label} {{id: $to_id}})
        )
        RETURN [n IN nodes(path) | n.id] AS path
        """
        
        result = self.conn.execute_query(
            query,
            {"from_id": from_id, "to_id": to_id}
        )
        
        return result[0]["path"] if result else None
    
    def compute_betweenness_centrality(
        self,
        node_label: str = "Document",
        rel_type: str = "CITES",
        write_property: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Compute betweenness centrality"""
        if write_property:
            query = f"""
            CALL gds.betweenness.write({{
                nodeProjection: '{node_label}',
                relationshipProjection: '{rel_type}',
                writeProperty: '{write_property}'
            }})
            YIELD centralityDistribution
            RETURN centralityDistribution
            """
        else:
            query = f"""
            CALL gds.betweenness.stream({{
                nodeProjection: '{node_label}',
                relationshipProjection: '{rel_type}'
            }})
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).id AS node_id, score
            ORDER BY score DESC
            """
        
        try:
            result = self.conn.execute_query(query)
            return [dict(r) for r in result]
        except Exception as e:
            print(f"⚠️  Betweenness centrality failed: {e}")
            return []
    
    def find_similar_nodes(
        self,
        node_id: str,
        node_label: str = "Document",
        rel_type: str = "CITES",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar nodes based on common neighbors
        
        Args:
            node_id: Source node ID
            node_label: Node label
            rel_type: Relationship type
            limit: Max results
            
        Returns:
            List of similar nodes with similarity scores
        """
        query = f"""
        MATCH (n:{node_label} {{id: $node_id}})-[:{rel_type}]-(neighbor)-[:{rel_type}]-(similar:{node_label})
        WHERE n <> similar
        WITH similar, count(DISTINCT neighbor) AS commonNeighbors
        RETURN similar.id AS node_id, commonNeighbors AS similarity
        ORDER BY similarity DESC
        LIMIT {limit}
        """
        
        result = self.conn.execute_query(query, {"node_id": node_id})
        return [dict(r) for r in result]


# Convenience functions
def compute_pagerank(
    node_label: str = "Document",
    rel_type: str = "CITES",
    **kwargs
) -> List[Dict[str, Any]]:
    """Compute PageRank"""
    algo = GraphAlgorithms()
    return algo.compute_pagerank(node_label, rel_type, **kwargs)


def detect_communities(
    node_label: str = "Document",
    rel_type: str = "CITES",
    **kwargs
) -> List[Dict[str, Any]]:
    """Detect communities"""
    algo = GraphAlgorithms()
    return algo.detect_communities(node_label, rel_type, **kwargs)


def find_shortest_path(
    from_id: str,
    to_id: str,
    **kwargs
) -> Optional[List[str]]:
    """Find shortest path"""
    algo = GraphAlgorithms()
    return algo.find_shortest_path(from_id, to_id, **kwargs)
