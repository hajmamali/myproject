"""
Experiments / A/B Testing API Router
====================================
Subsystem Status: INTENTIONALLY DISABLED FOR RELEASE (per AGENTS.md Section 1-I).

Endpoints return documented responses declaring the subsystem status rather than
fabricated or fake metrics, satisfying Phase 4 architectural constraints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


class ExperimentsListResponse(BaseModel):
    experiments: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "disabled_for_release"
    message: str = (
        "A/B testing and self-improvement subsystem is intentionally disabled for "
        "release per AGENTS.md Section 1-I."
    )


@router.get("", response_model=ExperimentsListResponse)
@router.get("/", response_model=ExperimentsListResponse)
async def list_experiments() -> ExperimentsListResponse:
    """List active A/B experiments.

    Returns disabled state per AGENTS.md 1-I.
    """
    return ExperimentsListResponse()


@router.get("/{experiment_id}/results")
async def get_experiment_results(experiment_id: str) -> Dict[str, Any]:
    """Retrieve experiment evaluation results.

    Returns HTTP 501 Not Implemented per Phase 4 governance requirements.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            f"Experiment {experiment_id} results unavailable: A/B testing subsystem "
            "is intentionally disabled for release per AGENTS.md Section 1-I."
        ),
    )
