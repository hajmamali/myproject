# pipelines/gnn/graph_analytics.py
"""Graph Analytics and Visualization"""

import torch
import networkx as nx
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from mahoun.pipelines._logging import setup_logger

log = setup_logger("graph_analytics")


class GraphAnalytics:
    """Analytics and visualization for legal document graph"""

    def __init__(self, graph_path: Optional[str] = None):
        log.info("Initializing Graph Analytics")
        self.nx_graph = None
        self.graph_data = None

        if graph_path:
            self._load_graph(graph_path)

    def _load_graph(self, graph_path: str):
        """Load graph from file"""
        path = Path(graph_path)

        if path.suffix == ".pt":
            self.graph_data = torch.load(graph_path)
            self.nx_graph = self._pyg_to_networkx(self.graph_data)
        elif path.suffix == ".graphml":
            self.nx_graph = nx.read_graphml(graph_path)

        log.info(f"Loaded graph: {self.nx_graph.number_of_nodes()} nodes")

    def _pyg_to_networkx(self, data) -> nx.DiGraph:
        """Convert PyG to NetworkX"""
        G = nx.DiGraph()

        for i in range(data.num_nodes):
            G.add_node(i)

        num_edges = data.edge_index.shape[1]
        for i in range(num_edges):
            src = data.edge_index[0, i].item()
            dst = data.edge_index[1, i].item()
            weight = data.edge_attr[i, 0].item() if data.edge_attr is not None else 1.0
            G.add_edge(src, dst, weight=weight)

        return G

    def compute_metrics(self) -> Dict[str, Any]:
        """Compute graph metrics"""
        log.info("Computing metrics...")

        G = self.nx_graph
        degrees = [d for n, d in G.degree()]

        metrics = {
            "num_nodes": G.number_of_nodes(),
            "num_edges": G.number_of_edges(),
            "density": nx.density(G),
            "avg_degree": np.mean(degrees),
            "max_degree": np.max(degrees),
        }

        if G.is_directed():
            metrics["num_weakly_connected"] = nx.number_weakly_connected_components(G)

        return metrics

    def find_hubs(self, top_k: int = 20, method: str = "pagerank") -> List[Dict]:
        """Find hub documents"""
        log.info(f"Finding top {top_k} hubs...")

        G = self.nx_graph

        if method == "pagerank":
            scores = nx.pagerank(G, weight="weight")
        elif method == "degree":
            scores = dict(G.degree())
        else:
            scores = nx.betweenness_centrality(G)

        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        hubs = []
        for node_id, score in sorted_nodes[:top_k]:
            hubs.append({"node_id": node_id, "score": score, "degree": G.degree(node_id)})

        return hubs

    def detect_communities(self, algorithm: str = "louvain") -> Dict[int, int]:
        """Detect communities"""
        log.info("Detecting communities...")

        G = self.nx_graph.to_undirected()

        try:
            import community as community_louvain

            communities = community_louvain.best_partition(G)
        except ImportError:
            communities_gen = nx.community.label_propagation_communities(G)
            communities = {}
            for comm_id, nodes in enumerate(communities_gen):
                for node in nodes:
                    communities[node] = comm_id

        return communities

    def generate_report(self, output_path: str = "graph_report.json"):
        """Generate report"""
        log.info("Generating report...")

        report = {"metrics": self.compute_metrics(), "hubs": self.find_hubs(top_k=20)}

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        log.info(f"Report saved to {output_path}")
        return report
