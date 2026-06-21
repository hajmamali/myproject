"""
Graph Optimizer Job - Official Entrypoint
==========================================
Offline job for graph optimization.

This script:
1. Reads config from configs/graph/optimizer.yaml (or defaults)
2. Establishes governance context
3. Creates governed Neo4j session factory
4. Runs optimization cycle
5. Produces reports to logs/graph_optimization/

Usage:
    python -m graph.optimizer.run_optimizer_job
    
    # With custom config
    python -m graph.optimizer.run_optimizer_job --config configs/graph/custom_optimizer.yaml
"""

import argparse
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_optimizer_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load optimizer configuration from YAML file.
    
    Args:
        config_path: Path to config file (defaults to configs/runtime_profile.yaml)
    
    Returns:
        Dictionary with optimizer config
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "configs" / "runtime_profile.yaml"
    else:
        config_path = Path(config_path)
    
    defaults = {
        "checkpoint_interval": 10,
        "report_dir": "logs/graph_optimization",
        "enable_feedback_loop": True
    }
    
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return defaults
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f) or {}
        
        optimizer_config = yaml_config.get("training", {}).get("optimizer", {})
        
        # Merge with defaults
        config = {**defaults, **optimizer_config}
        return config
    except ImportError:
        logger.warning("YAML not available, using defaults")
        return defaults
    except Exception as e:
        logger.warning(f"Failed to load config: {e}, using defaults")
        return defaults


async def run_optimization_cycle(
    connection: Any,
    config: Dict[str, Any],
    report_dir: Path,
    correlation_id: str,
    actor_id: str,
) -> bool:
    """
    Run graph optimization cycle with governance context.
    
    Args:
        connection: Neo4jConnection instance
        config: Optimizer configuration
        report_dir: Directory for reports
        correlation_id: Request correlation ID
        actor_id: Actor performing operations
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # GOVERNANCE ENFORCEMENT: Must use governed session
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        async with GovernanceContextManager.active_context(
            correlation_id=correlation_id,
            actor_id=actor_id
        ) as ctx:
            with connection.governed_session(
                correlation_id=correlation_id, 
                actor_id=actor_id
            ) as session:
                # All graph operations now go through governance
                logger.info(f"Starting optimization with governance context: {ctx.context_id}")
                
                # Example governance-compliant operation
                receipt = session.write_node(
                    "OptimizationJob",
                    {
                        "id": correlation_id,
                        "status": "running",
                        "provenance": ctx.require_provenance(
                            source="optimizer",
                            author=actor_id
                        ).to_dict()
                    }
                )
                
                logger.info(f"Optimization job created: {receipt.entry_id}")
                return True
        from mahoun.core.governance.governance_context import GovernanceContextManager
        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
        from mahoun.graph.optimizer.graph_optimizer import GraphOptimizer
        from mahoun.graph.optimizer.config import GraphOptimizationConfig
        
        # Create governed session factory
        # Use connection._raw_execute as the raw_executor
        # This properly handles authorization checks and connection lifecycle
        def session_factory() -> GovernedNeo4jSession:
            return GovernedNeo4jSession(
                raw_executor=connection._raw_execute,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )
        
        # Create optimizer config
        opt_config = GraphOptimizationConfig(
            enable_feedback_loop=config.get("enable_feedback_loop", True),
            enable_snapshots=True,
            snapshot_label=f"JOB-{correlation_id[:8]}",
        )
        
        # Create optimizer with governed session factory
        optimizer = GraphOptimizer(
            session_factory=session_factory,
            config=opt_config,
            logger=logger,
        )
        
        logger.info("Starting graph optimization cycle...")
        
        # Run optimization cycle with governance context
        async with GovernanceContextManager.active_context(
            correlation_id=correlation_id,
            execution_mode="STRICT",
        ):
            # Ensure schema
            await optimizer.ensure_schema(
                correlation_id=correlation_id,
                actor_id=actor_id,
            )
            
            # Update edge weights (if feedback loop enabled)
            if config.get("enable_feedback_loop", True):
                await optimizer.update_edge_weights(
                    correlation_id=correlation_id,
                    actor_id=actor_id,
                )
            else:
                await optimizer.score_and_flag_edges(
                    correlation_id=correlation_id,
                    actor_id=actor_id,
                )
            
            # Apply degree capping
            await optimizer.apply_degree_capping(
                correlation_id=correlation_id,
                actor_id=actor_id,
            )
            
            # Create snapshot
            if opt_config.enable_snapshots:
                await optimizer.snapshot_state(
                    correlation_id=correlation_id,
                    actor_id=actor_id,
                )
        
        logger.info("✅ Graph optimization complete!")
        logger.info(f"Reports saved to {report_dir}")
        logger.info("="*80)
        
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import optimizer: {e}")
        return False
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        return False


def main():
    """Main entrypoint for graph optimizer job"""
    parser = argparse.ArgumentParser(description="Run graph optimization cycle")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to optimizer config YAML file"
    )
    parser.add_argument(
        "--report-dir",
        type=str,
        default=None,
        help="Directory for optimization reports"
    )
    
    args = parser.parse_args()
    
    # GOVERNANCE GATE: Prevent running optimizer in production without explicit consent
    mahoun_env = os.getenv("MAHOUN_ENV", "dev")
    if mahoun_env in ("production", "prod") and not os.getenv("MAHOUN_ALLOW_OPTIMIZER_IN_PROD"):
        logger.error("❌ GOVERNANCE VIOLATION: Optimizer job blocked in production")
        logger.error("   Set MAHOUN_ALLOW_OPTIMIZER_IN_PROD=true to override")
        return 1
    
    logger.info("="*80)
    logger.info("Graph Optimizer Job - Starting")
    logger.info("="*80)
    
    # Load config
    config = load_optimizer_config(args.config)
    
    # Override with CLI args
    if args.report_dir:
        config["report_dir"] = args.report_dir
    
    # Ensure report directory exists
    report_dir = Path(config["report_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Report directory: {report_dir}")
    
    # Generate IDs for this run
    correlation_id = f"opt-{uuid.uuid4().hex[:16]}"
    actor_id = "optimizer-job"
    
    logger.info(f"Correlation ID: {correlation_id}")
    logger.info(f"Actor ID: {actor_id}")
    
    # Get Neo4j connection from runtime config
    try:
        from mahoun.graph.neo4j.connection import get_connection
        
        connection = get_connection()
        
        logger.info("✅ Connected to Neo4j")
        
        # Run async optimization cycle
        success = asyncio.run(
            run_optimization_cycle(
                connection=connection,
                config=config,
                report_dir=report_dir,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )
        )
        
        return 0 if success else 1
        
    except ImportError as e:
        logger.error(f"Failed to import optimizer: {e}")
        return 1
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

