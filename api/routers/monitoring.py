"""
Intelligent System Monitoring API Router
=========================================
Production-grade monitoring endpoints for graph integrity and model performance.

This router wires UltraIntegrityValidator and AdvancedModelOrchestrator
to provide real-time health scores, violation tracking, model leaderboards,
and performance analytics.

Endpoints:
- GET /monitoring/graph/health - Graph health score with breakdown
- GET /monitoring/graph/violations - Active graph violations with severity
- GET /monitoring/models/performance - Model performance metrics
- GET /monitoring/models/leaderboard - Model ranking by composite score
- GET /monitoring/system/overview - Complete system status
"""

from fastapi import APIRouter, HTTPException, status, Query, Request
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
    responses={
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)


# ============================================================================
# GRAPH INTEGRITY MONITORING
# ============================================================================

@router.get(
    "/graph/health",
    summary="Graph Health Score",
    description="""
    Get comprehensive graph integrity health score (0-100).
    
    Runs all UltraIntegrityValidator checks:
    - Orphaned nodes detection
    - Circular reference detection
    - Hash chain integrity
    - Temporal consistency
    - Anomaly detection
    
    Returns weighted health score with detailed breakdown.
    """,
    response_description="Health score with component breakdown"
)
async def get_graph_health(
    request: Request,
    run_validation: bool = Query(True, description="Run fresh validation vs use cached"),
    parallel: bool = Query(True, description="Run checks in parallel for performance")
) -> Dict[str, Any]:
    """
    Calculate graph health score with detailed breakdown
    
    Args:
        run_validation: If True, runs fresh validation; if False, uses last cached results
        parallel: If True, runs validation checks in parallel
    
    Returns:
        {
            "health_score": float (0-100),
            "status": "healthy" | "degraded" | "critical",
            "timestamp": ISO timestamp,
            "validation_results": {...},
            "component_scores": {
                "orphaned_nodes": float,
                "circular_refs": float,
                "hash_integrity": float,
                "temporal_consistency": float,
                "anomalies": float
            },
            "recommendations": List[str]
        }
    """
    try:
        # Get UltraIntegrityValidator from app state
        if not hasattr(request.app.state, 'integrity_validator'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Graph integrity validator not initialized. Ensure bootstrap wiring is complete."
            )
        
        validator = request.app.state.integrity_validator
        
        # Run validation if requested
        if run_validation:
            validation_results = validator.validate_all(parallel=parallel)
        else:
            # Use cached violations
            validation_results = {
                "violations_count": len(validator.violations),
                "violations": [
                    {
                        "id": v.violation_id,
                        "type": v.violation_type,
                        "severity": v.severity,
                        "entity": v.entity_id,
                        "message": v.message
                    }
                    for v in validator.violations[:100]  # Limit to first 100
                ]
            }
        
        # Get health score
        health_score = validator.get_health_score()
        
        # Determine status based on score
        if health_score >= 90:
            health_status = "healthy"
        elif health_score >= 70:
            health_status = "degraded"
        else:
            health_status = "critical"
        
        # Calculate component scores (inverse of violation counts)
        violations_by_type = {}
        for v in validator.violations:
            violations_by_type[v.violation_type] = violations_by_type.get(v.violation_type, 0) + 1
        
        component_scores = {
            "orphaned_nodes": max(0, 100 - violations_by_type.get("orphaned_node", 0) * 2),
            "circular_refs": max(0, 100 - violations_by_type.get("circular_reference", 0) * 5),
            "hash_integrity": max(0, 100 - violations_by_type.get("hash_chain_broken", 0) * 10),
            "temporal_consistency": max(0, 100 - violations_by_type.get("temporal_violation", 0) * 3),
            "anomalies": max(0, 100 - violations_by_type.get("anomaly_detected", 0) * 4)
        }
        
        # Generate recommendations
        recommendations = []
        if violations_by_type.get("orphaned_node", 0) > 10:
            recommendations.append("Consider running auto-cleanup for orphaned nodes")
        if violations_by_type.get("circular_reference", 0) > 0:
            recommendations.append("CRITICAL: Circular references detected - manual review required")
        if violations_by_type.get("hash_chain_broken", 0) > 0:
            recommendations.append("CRITICAL: Hash chain integrity compromised - investigate immediately")
        if health_score < 70:
            recommendations.append("System health degraded - schedule maintenance window")
        
        return {
            "health_score": health_score,
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "validation_results": validation_results,
            "component_scores": component_scores,
            "recommendations": recommendations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph health: {str(e)}"
        )


@router.get(
    "/graph/violations",
    summary="Graph Violations List",
    description="""
    Get list of active graph integrity violations.
    
    Supports filtering by:
    - Severity (critical, high, medium, low)
    - Violation type
    - Entity label
    
    Returns paginated results with remediation suggestions.
    """,
    response_description="List of violations with metadata"
)
async def get_graph_violations(
    request: Request,
    severity: Optional[str] = Query(None, description="Filter by severity: critical|high|medium|low"),
    violation_type: Optional[str] = Query(None, description="Filter by violation type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum violations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    Get filtered list of graph violations
    
    Args:
        severity: Filter by severity level
        violation_type: Filter by specific violation type
        limit: Max results per page
        offset: Pagination offset
    
    Returns:
        {
            "total": int,
            "returned": int,
            "offset": int,
            "violations": [
                {
                    "id": str,
                    "type": str,
                    "severity": str,
                    "entity_id": str,
                    "entity_label": str,
                    "message": str,
                    "detected_at": ISO timestamp,
                    "remediation": str,
                    "affected_downstream": List[str]
                }
            ]
        }
    """
    try:
        if not hasattr(request.app.state, 'integrity_validator'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Graph integrity validator not initialized"
            )
        
        validator = request.app.state.integrity_validator
        violations = validator.violations
        
        # Apply filters
        if severity:
            violations = [v for v in violations if v.severity.lower() == severity.lower()]
        
        if violation_type:
            violations = [v for v in violations if v.violation_type == violation_type]
        
        total_count = len(violations)
        
        # Apply pagination
        paginated = violations[offset:offset + limit]
        
        # Format response
        formatted_violations = [
            {
                "id": v.violation_id,
                "type": v.violation_type,
                "severity": v.severity,
                "entity_id": v.entity_id,
                "entity_label": v.entity_label,
                "message": v.message,
                "detected_at": v.detected_at,
                "remediation": v.remediation_suggestion,
                "affected_downstream": v.affected_downstream,
                "metadata": v.metadata
            }
            for v in paginated
        ]
        
        return {
            "total": total_count,
            "returned": len(formatted_violations),
            "offset": offset,
            "violations": formatted_violations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get violations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get violations: {str(e)}"
        )


# ============================================================================
# MODEL PERFORMANCE MONITORING
# ============================================================================

@router.get(
    "/models/performance",
    summary="Model Performance Metrics",
    description="""
    Get detailed performance metrics for a specific model or all models.
    
    Metrics include:
    - Request count & rate
    - Average latency (p50, p95, p99)
    - Error rate & types
    - Success rate
    - Throughput (req/sec)
    
    Supports time-window filtering for trend analysis.
    """,
    response_description="Model performance metrics"
)
async def get_model_performance(
    request: Request,
    model_id: Optional[str] = Query(None, description="Specific model ID, or null for all models"),
    time_window: int = Query(3600, ge=60, le=86400, description="Time window in seconds (1min - 24h)")
) -> Dict[str, Any]:
    """
    Get model performance metrics
    
    Args:
        model_id: Specific model to query, or None for all models
        time_window: Time window in seconds for metrics calculation
    
    Returns:
        {
            "timestamp": ISO timestamp,
            "time_window_seconds": int,
            "models": {
                "<model_id>": {
                    "model_id": str,
                    "model_type": str,
                    "total_requests": int,
                    "request_rate": float,  # req/sec
                    "latency": {
                        "avg_ms": float,
                        "p50_ms": float,
                        "p95_ms": float,
                        "p99_ms": float
                    },
                    "errors": {
                        "total": int,
                        "rate": float  # percentage
                    },
                    "success_rate": float,  # percentage
                    "active": bool,
                    "health_score": float
                }
            }
        }
    """
    try:
        if not hasattr(request.app.state, 'model_orchestrator'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model orchestrator not initialized. Ensure AdvancedModelOrchestrator is wired in bootstrap."
            )
        
        orchestrator = request.app.state.model_orchestrator
        
        # Get metrics
        if model_id:
            metrics = orchestrator.get_model_metrics(model_id)
            if not metrics:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model '{model_id}' not found"
                )
            models_data = {model_id: metrics}
        else:
            # Get all models
            models_data = {}
            for mid in orchestrator.models.keys():
                metrics = orchestrator.get_model_metrics(mid)
                if metrics:
                    models_data[mid] = metrics
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "time_window_seconds": time_window,
            "models": models_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model performance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model performance: {str(e)}"
        )


@router.get(
    "/models/leaderboard",
    summary="Model Leaderboard",
    description="""
    Get ranked leaderboard of all models by composite performance score.
    
    Scoring formula (weighted):
    - Success rate: 40%
    - Latency (inverse): 30%
    - Throughput: 20%
    - Error rate (inverse): 10%
    
    Returns top N models with detailed comparison metrics.
    """,
    response_description="Ranked model leaderboard"
)
async def get_model_leaderboard(
    request: Request,
    top_n: int = Query(10, ge=1, le=100, description="Number of top models to return"),
    model_type: Optional[str] = Query(None, description="Filter by model type")
) -> Dict[str, Any]:
    """
    Get model leaderboard ranked by composite score
    
    Args:
        top_n: Number of top models to return
        model_type: Optional filter by model type
    
    Returns:
        {
            "timestamp": ISO timestamp,
            "ranking": [
                {
                    "rank": int,
                    "model_id": str,
                    "model_type": str,
                    "composite_score": float (0-100),
                    "score_breakdown": {
                        "success_rate_score": float,
                        "latency_score": float,
                        "throughput_score": float,
                        "reliability_score": float
                    },
                    "metrics": {
                        "total_requests": int,
                        "success_rate": float,
                        "avg_latency_ms": float,
                        "error_rate": float
                    },
                    "active": bool
                }
            ],
            "total_models": int
        }
    """
    try:
        if not hasattr(request.app.state, 'model_orchestrator'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model orchestrator not initialized"
            )
        
        orchestrator = request.app.state.model_orchestrator
        
        # Get all models
        all_models = []
        for model_id, model_info in orchestrator.models.items():
            # Filter by type if specified
            if model_type and model_info.get("model_type") != model_type:
                continue
            
            metrics = orchestrator.get_model_metrics(model_id)
            if not metrics:
                continue
            
            # Calculate composite score
            # Weights: success_rate=0.4, latency=0.3, throughput=0.2, reliability=0.1
            success_rate = metrics.get("success_rate", 0.0)
            avg_latency = metrics.get("latency", {}).get("avg_ms", 1000)
            total_requests = metrics.get("total_requests", 0)
            error_rate = metrics.get("errors", {}).get("rate", 0.0)
            
            # Normalize scores (0-100)
            success_score = success_rate  # Already in percentage
            latency_score = max(0, 100 - (avg_latency / 10))  # Assume 1000ms = 0, 0ms = 100
            throughput_score = min(100, (total_requests / 100) * 10)  # 1000 requests = 100
            reliability_score = max(0, 100 - error_rate)  # Lower error rate = better
            
            composite_score = (
                success_score * 0.4 +
                latency_score * 0.3 +
                throughput_score * 0.2 +
                reliability_score * 0.1
            )
            
            all_models.append({
                "model_id": model_id,
                "model_type": model_info.get("model_type", "unknown"),
                "composite_score": round(composite_score, 2),
                "score_breakdown": {
                    "success_rate_score": round(success_score, 2),
                    "latency_score": round(latency_score, 2),
                    "throughput_score": round(throughput_score, 2),
                    "reliability_score": round(reliability_score, 2)
                },
                "metrics": {
                    "total_requests": total_requests,
                    "success_rate": success_rate,
                    "avg_latency_ms": avg_latency,
                    "error_rate": error_rate
                },
                "active": model_info.get("active", False)
            })
        
        # Sort by composite score (descending)
        all_models.sort(key=lambda x: x["composite_score"], reverse=True)
        
        # Add ranking
        for idx, model in enumerate(all_models[:top_n], start=1):
            model["rank"] = idx
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "ranking": all_models[:top_n],
            "total_models": len(all_models)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model leaderboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model leaderboard: {str(e)}"
        )


# ============================================================================
# SYSTEM OVERVIEW
# ============================================================================

@router.get(
    "/system/overview",
    summary="Complete System Status",
    description="""
    Get comprehensive system overview combining:
    - Graph health score
    - Model performance summary
    - Active violations count
    - System resource status
    - Uptime and version info
    
    Single endpoint for dashboard landing page.
    """,
    response_description="Complete system status overview"
)
async def get_system_overview(request: Request) -> Dict[str, Any]:
    """
    Get complete system overview
    
    Returns:
        {
            "timestamp": ISO timestamp,
            "graph": {
                "health_score": float,
                "status": str,
                "violations": {
                    "total": int,
                    "critical": int,
                    "high": int
                }
            },
            "models": {
                "total": int,
                "active": int,
                "avg_success_rate": float,
                "avg_latency_ms": float,
                "top_performer": str
            },
            "system": {
                "uptime_seconds": float,
                "version": str
            }
        }
    """
    try:
        overview = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "graph": {},
            "models": {},
            "system": {}
        }
        
        # Graph health
        if hasattr(request.app.state, 'integrity_validator'):
            validator = request.app.state.integrity_validator
            health_score = validator.get_health_score()
            
            violations_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for v in validator.violations:
                violations_by_severity[v.severity] = violations_by_severity.get(v.severity, 0) + 1
            
            overview["graph"] = {
                "health_score": health_score,
                "status": "healthy" if health_score >= 90 else ("degraded" if health_score >= 70 else "critical"),
                "violations": {
                    "total": len(validator.violations),
                    "critical": violations_by_severity["critical"],
                    "high": violations_by_severity["high"]
                }
            }
        
        # Model performance
        if hasattr(request.app.state, 'model_orchestrator'):
            orchestrator = request.app.state.model_orchestrator
            system_status = orchestrator.get_system_status()
            
            overview["models"] = {
                "total": system_status.get("total_models", 0),
                "active": system_status.get("active_models", 0),
                "avg_success_rate": system_status.get("avg_success_rate", 0.0),
                "avg_latency_ms": system_status.get("avg_latency_ms", 0.0),
                "top_performer": system_status.get("top_performer", "N/A")
            }
        
        # System info
        if hasattr(request.app.state, 'start_time'):
            uptime = datetime.utcnow().timestamp() - request.app.state.start_time
            overview["system"]["uptime_seconds"] = round(uptime, 2)
        
        overview["system"]["version"] = "2.0.0"
        
        return overview
        
    except Exception as e:
        logger.error(f"Failed to get system overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system overview: {str(e)}"
        )


# ============================================================================
# MAINTENANCE / AUTO-CLEANUP ENDPOINTS
# ============================================================================

@router.post(
    "/maintenance/cleanup-orphans",
    summary="Auto-Cleanup Orphaned Nodes",
    description="""
    Automatically cleanup orphaned nodes based on selected mode and classification.
    
    Cleanup Modes:
    - **safe**: Only delete nodes older than 30 days with no relationships
    - **aggressive**: Delete all orphaned nodes regardless of age (use with caution)
    - **manual-review**: Return list of candidates without deletion for human review
    
    Supports dry-run mode to preview changes without executing deletions.
    All deletions go through GovernedNeo4jSession with full audit trail.
    """,
    response_description="Cleanup operation results"
)
async def cleanup_orphaned_nodes(
    request: Request,
    mode: str = Query(..., description="Cleanup mode: safe|aggressive|manual-review"),
    dry_run: bool = Query(False, description="Preview changes without executing deletions"),
    batch_size: int = Query(50, ge=1, le=500, description="Maximum nodes to process per batch"),
    age_threshold_days: int = Query(30, ge=1, le=365, description="Minimum age in days for safe cleanup")
) -> Dict[str, Any]:
    """
    Execute governance-compliant orphan cleanup operation
    
    Args:
        mode: Cleanup strategy (safe/aggressive/manual-review)
        dry_run: If True, only returns what would be deleted without executing
        batch_size: Maximum nodes to process in single operation
        age_threshold_days: Minimum node age for safe cleanup mode
    
    Returns:
        {
            "mode": str,
            "dry_run": bool,
            "summary": {
                "candidates_found": int,
                "nodes_processed": int,
                "nodes_deleted": int,
                "errors_count": int
            },
            "candidates": [
                {
                    "node_id": str,
                    "label": str,
                    "age_days": int,
                    "classification": "safe" | "risky",
                    "reason": str,
                    "action": "delete" | "skip" | "review"
                }
            ],
            "execution_time_ms": float,
            "governance_audit_id": str
        }
    """
    try:
        # Validate mode parameter
        valid_modes = {"safe", "aggressive", "manual-review"}
        if mode not in valid_modes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )
        
        # Get UltraIntegrityValidator for orphan detection
        if not hasattr(request.app.state, 'integrity_validator'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Integrity validator not initialized. Cannot perform cleanup operations."
            )
        
        validator = request.app.state.integrity_validator
        start_time = datetime.utcnow()
        
        # Step 1: Identify orphaned nodes
        orphan_check_result = validator.check_orphaned_nodes()
        
        # Extract orphan nodes from validator result
        # Assuming check_orphaned_nodes returns a dict with violations or node data
        orphan_violations = [
            v for v in validator.violations 
            if v.violation_type == "orphaned_node"
        ]
        
        # Step 2: Classify orphans based on safety criteria using advanced classifier
        from mahoun.monitoring.orphan_classifier import create_orphan_classifier
        
        classifier = create_orphan_classifier(
            age_threshold_days=age_threshold_days,
            confidence_threshold=0.8,
            enable_anomaly_detection=True
        )
        
        # Get orphan violations and classify them
        orphan_violations = [
            v for v in validator.violations 
            if v.violation_type == "orphaned_node"
        ]
        
        # Batch classify orphans
        classifications = classifier.classify_batch(orphan_violations[:batch_size])
        
        # Convert to expected format and determine actions
        candidates = []
        nodes_to_delete = []
        
        for classification in classifications:
            candidate_dict = classification.to_dict()
            candidates.append(candidate_dict)
            
            # Determine action based on mode and classification
            if mode == "safe" and classification.risk_level.value == "safe":
                nodes_to_delete.append(candidate_dict)
            elif mode == "aggressive" and classification.action.value in ["delete", "review"]:
                nodes_to_delete.append(candidate_dict)
            # manual-review mode doesn't delete anything
        
        # Step 3: Execute deletions (unless dry-run or manual-review)
        deleted_count = 0
        errors_count = 0
        governance_audit_id = ""
        
        if not dry_run and mode != "manual-review" and nodes_to_delete:
            try:
                # Create governance context for cleanup operations
                from mahoun.core.governance.governance_context import GovernanceContext
                from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
                from mahoun.graph.neo4j.connection import get_connection
                
                governance_ctx = GovernanceContext(
                    capability="orphan_cleanup",
                    correlation_id=f"cleanup-{start_time.timestamp()}",
                    provenance_source="maintenance_api",
                    provenance_author="system"
                )
                
                # Get Neo4j connection for governed operations
                connection = get_connection()
                
                # Create governed session for safe deletions
                governed_session = GovernedNeo4jSession(
                    raw_executor=connection._raw_execute,
                    correlation_id=governance_ctx.correlation_id,
                    actor_id="maintenance_system"
                )
                
                # Execute deletions through governance boundary
                for node_candidate in nodes_to_delete:
                    try:
                        # Use soft delete by default for safety
                        receipt = governed_session.delete_node(
                            label=node_candidate.get("label", "Unknown"),
                            node_id=node_candidate["node_id"],
                            soft_delete=True,
                            deleted_reason=f"automated_cleanup_{mode}",
                            source_event_id=f"cleanup-{start_time.timestamp()}"
                        )
                        
                        deleted_count += 1
                        governance_audit_id = receipt.correlation_id
                        
                        logger.info(
                            f"Deleted orphaned node {node_candidate['node_id']} "
                            f"(mode: {mode}, classification: {node_candidate['classification']})"
                        )
                        
                    except Exception as delete_error:
                        errors_count += 1
                        logger.error(
                            f"Failed to delete node {node_candidate['node_id']}: {delete_error}"
                        )
                        
            except Exception as governance_error:
                logger.error(f"Governance setup failed for cleanup: {governance_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initialize governance for cleanup: {str(governance_error)}"
                )
        
        # Step 4: Prepare response
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "mode": mode,
            "dry_run": dry_run,
            "summary": {
                "candidates_found": len(candidates),
                "nodes_processed": len(nodes_to_delete),
                "nodes_deleted": deleted_count,
                "errors_count": errors_count
            },
            "candidates": candidates,
            "execution_time_ms": round(execution_time, 2),
            "governance_audit_id": governance_audit_id,
            "recommendations": _generate_cleanup_recommendations(mode, candidates, deleted_count)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Orphan cleanup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup operation failed: {str(e)}"
        )


# ============================================================================
# HELPER FUNCTIONS FOR ORPHAN CLEANUP
# ============================================================================

def _classify_orphan_node(violation, age_threshold_days: int) -> Dict[str, Any]:
    """
    Classify an orphaned node as safe or risky for deletion
    
    Safe deletion criteria:
    - Node age > age_threshold_days
    - No outgoing relationships
    - Not a critical entity type (Evidence, Precedent, Constitutional)
    - No recent activity (last 30 days)
    
    Args:
        violation: AdvancedViolation object from UltraIntegrityValidator
        age_threshold_days: Minimum age threshold for safe deletion
    
    Returns:
        Dict with classification details
    """
    # Parse metadata from violation
    metadata = getattr(violation, 'metadata', {})
    age_days = metadata.get('age_days', 0)
    entity_label = getattr(violation, 'entity_label', 'Unknown')
    node_id = getattr(violation, 'entity_id', 'unknown')
    
    # Critical entity types that should never be auto-deleted
    critical_labels = {'Evidence', 'Precedent', 'Constitutional', 'LegalRule', 'CaseOutcome'}
    
    # Classification logic
    is_safe = True
    reasons = []
    
    # Age check
    if age_days < age_threshold_days:
        is_safe = False
        reasons.append(f"Too recent ({age_days} days < {age_threshold_days} threshold)")
    
    # Entity type check
    if entity_label in critical_labels:
        is_safe = False
        reasons.append(f"Critical entity type: {entity_label}")
    
    # Additional safety checks from metadata
    if metadata.get('has_relationships', False):
        is_safe = False
        reasons.append("Has existing relationships")
    
    if metadata.get('recent_activity', False):
        is_safe = False
        reasons.append("Recent activity detected")
    
    # Determine action
    if is_safe:
        action = "delete"
        reason = "Safe for automated cleanup"
    else:
        action = "review" if reasons else "skip"
        reason = "; ".join(reasons) if reasons else "Manual review recommended"
    
    return {
        "node_id": node_id,
        "label": entity_label,
        "age_days": age_days,
        "classification": "safe" if is_safe else "risky",
        "reason": reason,
        "action": action,
        "metadata": metadata
    }


def _generate_cleanup_recommendations(mode: str, candidates: List[Dict], deleted_count: int) -> List[str]:
    """Generate recommendations based on cleanup results"""
    recommendations = []
    
    total_candidates = len(candidates)
    safe_count = sum(1 for c in candidates if c["classification"] == "safe")
    risky_count = total_candidates - safe_count
    
    if mode == "manual-review":
        recommendations.append(f"Found {total_candidates} orphaned nodes: {safe_count} safe, {risky_count} require review")
        if safe_count > 0:
            recommendations.append("Consider running 'safe' mode to auto-cleanup safe nodes")
    
    elif mode == "safe":
        if deleted_count > 0:
            recommendations.append(f"Successfully cleaned up {deleted_count} safe orphaned nodes")
        if risky_count > 0:
            recommendations.append(f"{risky_count} nodes require manual review before deletion")
    
    elif mode == "aggressive":
        recommendations.append(f"Processed {total_candidates} nodes in aggressive mode")
        if risky_count > 0:
            recommendations.append("WARNING: Aggressive mode may have deleted critical nodes - verify results")
    
    if total_candidates > deleted_count and mode != "manual-review":
        recommendations.append("Run health check to verify graph integrity after cleanup")
    
    return recommendations
