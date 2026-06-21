"""
Metrics API Router
==================
API endpoints for accessing collected metrics.

Endpoints:
- GET /metrics - Get all metrics
- GET /metrics/{metric_name} - Get specific metric
- GET /metrics/agents/summary - Get agent metrics summary
- POST /metrics/reset - Reset metrics
"""

from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict
import logging

from mahoun.metrics import get_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    responses={500: {"description": "Internal server error"}},
)


@router.get(
    "",
    summary="Get all metrics",
    description="Get all collected metrics (counters, gauges, and history)",
)
async def get_all_metrics() -> Dict[str, Any]:
    """
    Get all collected metrics

    Returns:
        Dictionary with all metrics data
    """
    try:
        collector = get_metrics_collector()
        return collector.get_all_metrics()
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}",
        )


@router.get(
    "/summary",
    summary="Get metrics summary",
    description="Get summary statistics for all metrics",
)
async def get_metrics_summary() -> Dict[str, Any]:
    """
    Get metrics summary

    Returns:
        Dictionary with summary statistics
    """
    try:
        collector = get_metrics_collector()
        all_metrics = collector.get_all_metrics()
        return {
            "total_counters": len(all_metrics.get("counters", {})),
            "total_gauges": len(all_metrics.get("gauges", {})),
            "total_histograms": len(all_metrics.get("histograms", {})),
            "total_metrics": (
                len(all_metrics.get("counters", {}))
                + len(all_metrics.get("gauges", {}))
                + len(all_metrics.get("histograms", {}))
            ),
        }
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics summary: {str(e)}",
        )


@router.get(
    "/{metric_name:path}",
    summary="Get specific metric",
    description="Get data for a specific metric by name",
)
async def get_metric(metric_name: str) -> Dict[str, Any]:
    """
    Get specific metric

    Args:
        metric_name: Name of the metric (e.g., "agent.process", "api.search")

    Returns:
        Metric data including counter, gauge, and history
    """
    # Reserved monitoring paths handled by api/main.py
    RESERVED_PATHS = {"legal", "prometheus", "reset"}
    if metric_name in RESERVED_PATHS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric '{metric_name}' not found",
        )

    try:
        collector = get_metrics_collector()
        all_metrics = collector.get_all_metrics()

        # Search across counters, gauges, and histograms
        result = {}
        for category in ["counters", "gauges", "histograms"]:
            metrics_in_category = all_metrics.get(category, {})
            for name, data in metrics_in_category.items():
                base_name = name.split("{")[0] if "{" in name else name
                if base_name == metric_name or name == metric_name:
                    result[name] = {"category": category, **data}

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metric '{metric_name}' not found",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metric '{metric_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metric: {str(e)}",
        )


@router.get(
    "/agents/summary",
    summary="Get agent metrics summary",
    description="Get summary of all agent-related metrics",
)
async def get_agent_metrics_summary() -> Dict[str, Any]:
    """
    Get summary of all agent metrics

    Returns:
        Dictionary with agent metrics summary
    """
    try:
        collector = get_metrics_collector()
        all_metrics = collector.get_all_metrics()

        # Filter agent metrics
        agent_metrics = {
            k: v
            for k, v in all_metrics.get("counters", {}).items()
            if k.startswith("agent.")
        }

        agent_gauges = {
            k: v
            for k, v in all_metrics.get("gauges", {}).items()
            if k.startswith("agent.")
        }

        return {
            "counters": agent_metrics,
            "gauges": agent_gauges,
            "total_agent_metrics": len(agent_metrics) + len(agent_gauges),
        }
    except Exception as e:
        logger.error(f"Failed to get agent metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent metrics: {str(e)}",
        )


@router.post(
    "/reset",
    summary="Reset metrics",
    description="Reset all metrics or a specific metric",
)
async def reset_metrics() -> Dict[str, Any]:
    """
    Reset metrics

    Args:
        metric_name: Optional metric name to reset (resets all if None)

    Returns:
        Confirmation message
    """
    try:
        collector = get_metrics_collector()
        collector.reset()

        return {"message": "All metrics reset successfully"}
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset metrics: {str(e)}",
        )
