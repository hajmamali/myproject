from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class EdgeTypePolicy:
    """
    Policy for optimizing a specific edge type.
    
    v2 Enterprise additions:
    - min_weight, max_weight: bounds for dynamic edge weighting
    - priority: importance ranking for pruning decisions (higher = more important)
    """
    edge_type: str
    base_weight: float = 1.0
    max_degree: Optional[int] = None
    include_by_default: bool = True
    
    # v2 Enterprise fields
    min_weight: float = 0.1
    max_weight: float = 2.0
    priority: int = 10  # higher = more important in pruning/retention

@dataclass
class GraphOptimizationConfig:
    """
    Configuration for graph optimization.
    
    v2 Enterprise additions:
    - recency_half_life_days: time decay parameter for edge scoring
    - min_usage_for_promotion: threshold for usage-based boosting
    - pruning_threshold: minimum weight for active edges
    - enable_feedback_loop: toggle feedback-driven optimization
    - enable_snapshots: toggle optimization state snapshots
    - snapshot_label: label for snapshot metadata
    """
    edge_policies: Dict[str, EdgeTypePolicy]
    default_max_hops: int = 2
    default_max_nodes: int = 500
    default_max_edges: int = 2000
    
    # v2 Enterprise fields
    recency_half_life_days: int = 30
    min_usage_for_promotion: int = 3
    pruning_threshold: float = 0.15
    enable_feedback_loop: bool = True
    enable_snapshots: bool = True
    snapshot_label: str = "GRAPH_OPT_SNAPSHOT"

    @staticmethod
    def default():
        """
        Default configuration with enterprise-grade policies.
        
        v2 updates:
        - Higher base weights and degree caps for critical edge types
        - Priority-based ranking for adaptive pruning
        - Feedback loop and snapshots enabled by default
        """
        return GraphOptimizationConfig(
            edge_policies={
                "CITES_ARTICLE": EdgeTypePolicy(
                    edge_type="CITES_ARTICLE",
                    base_weight=1.5,
                    max_degree=100,
                    priority=15,
                    min_weight=0.2,
                    max_weight=2.5,
                ),
                "REFERS_TO_CASE": EdgeTypePolicy(
                    edge_type="REFERS_TO_CASE",
                    base_weight=1.2,
                    max_degree=100,
                    priority=15,
                    min_weight=0.2,
                    max_weight=2.5,
                ),
                "MENTIONS_CONCEPT": EdgeTypePolicy(
                    edge_type="MENTIONS_CONCEPT",
                    base_weight=0.6,
                    max_degree=40,
                    priority=10,
                    min_weight=0.1,
                    max_weight=1.5,
                ),
            },
            # v2 Enterprise defaults
            recency_half_life_days=30,
            min_usage_for_promotion=3,
            pruning_threshold=0.15,
            enable_feedback_loop=True,
            enable_snapshots=True,
        )
