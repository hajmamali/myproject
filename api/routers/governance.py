"""
Governance Center API Endpoints

Provides real-time governance health, audit metrics, fail-closed events,
and mutation authorization statistics for the Governance Center dashboard.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mahoun.core.governance.governance_context import GovernanceContext
from mahoun.audit.models import AuditEvent, AuditSeverity
from mahoun.graph.neo4j.connection import Neo4jConnection, get_connection
from mahoun.security.rbac import require_permissions, Permission


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/api/v1/governance",
    tags=["governance"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Models
# ============================================================================

class Issue(BaseModel):
    """Represents a governance issue"""
    id: str
    severity: str = Field(..., description="critical | high | medium | low")
    category: str
    message: str
    timestamp: datetime


class ConstitutionalHealth(BaseModel):
    """Overall constitutional health status"""
    status: str = Field(..., description="healthy | degraded | critical")
    score: float = Field(..., ge=0, le=100, description="Compliance score 0-100")
    issues: List[Issue]
    lastValidation: datetime


class TrendData(BaseModel):
    """Time series trend data point"""
    timestamp: datetime
    value: float


class AuditMetrics(BaseModel):
    """Aggregated audit metrics"""
    totalEvents: int
    criticalEvents: int
    complianceRate: float = Field(..., ge=0, le=100)
    trends: List[TrendData]


class FailClosedEvent(BaseModel):
    """Fail-closed safety event"""
    id: str
    type: str
    reason: str
    impact: str
    timestamp: datetime
    recovered: bool


class RiskDistribution(BaseModel):
    """Distribution of mutations by risk level"""
    low: int
    medium: int
    high: int
    critical: int


class MutationAuthorization(BaseModel):
    """Mutation authorization statistics"""
    pendingRequests: int
    approvalRate: float = Field(..., ge=0, le=100)
    averageReviewTime: float  # milliseconds
    riskDistribution: RiskDistribution


# ============================================================================
# Helper Functions
# ============================================================================

async def calculate_health_score(
    governance_ctx: GovernanceContext,
    issues: List[Issue]
) -> float:
    """
    Calculate overall constitutional health score
    
    Formula:
    - Start at 100
    - Deduct points based on issue severity:
      - Critical: -10 points each
      - High: -5 points each
      - Medium: -2 points each
      - Low: -0.5 points each
    - Minimum score: 0
    """
    score = 100.0
    
    for issue in issues:
        if issue.severity == "critical":
            score -= 10.0
        elif issue.severity == "high":
            score -= 5.0
        elif issue.severity == "medium":
            score -= 2.0
        elif issue.severity == "low":
            score -= 0.5
    
    return max(0.0, score)


def determine_health_status(score: float) -> str:
    """Determine health status from score"""
    if score >= 90:
        return "healthy"
    elif score >= 70:
        return "degraded"
    else:
        return "critical"


async def fetch_governance_issues(
    governance_ctx: GovernanceContext,
    neo4j: Neo4jConnection
) -> List[Issue]:
    """
    Fetch current governance issues from the system
    
    This queries:
    - Neo4j governance validation logs
    - Constitutional constraint violations
    - Policy enforcement failures
    - Mutation authorization denials
    """
    issues: List[Issue] = []
    
    # Query Neo4j for recent governance violations
    query = """
    MATCH (event:GovernanceEvent)
    WHERE event.timestamp > datetime() - duration('PT24H')
      AND event.status IN ['FAILED', 'VIOLATED', 'DENIED']
    RETURN 
        event.id as id,
        event.severity as severity,
        event.category as category,
        event.message as message,
        event.timestamp as timestamp
    ORDER BY event.timestamp DESC
    LIMIT 50
    """
    
    try:
        results = await neo4j.execute_query(query)
        
        for record in results:
            issues.append(Issue(
                id=record["id"],
                severity=record["severity"].lower(),
                category=record["category"],
                message=record["message"],
                timestamp=record["timestamp"]
            ))
    except Exception as e:
        # If query fails, add a synthetic issue about the failure
        issues.append(Issue(
            id="system-error-001",
            severity="high",
            category="System Health",
            message=f"Failed to fetch governance events: {str(e)}",
            timestamp=datetime.utcnow()
        ))
    
    return issues


async def fetch_audit_metrics_data(
    neo4j: Neo4jConnection,
    hours: int = 24
) -> AuditMetrics:
    """Fetch aggregated audit metrics"""
    
    query = """
    MATCH (event:AuditEvent)
    WHERE event.timestamp > datetime() - duration({duration})
    WITH 
        count(event) as total,
        count(CASE WHEN event.severity = 'CRITICAL' THEN 1 END) as critical,
        event.timestamp as ts,
        event.compliance as compliance
    RETURN 
        total,
        critical,
        compliance,
        ts
    ORDER BY ts DESC
    """
    
    try:
        results = await neo4j.execute_query(
            query,
            {"duration": f"PT{hours}H"}
        )
        
        total_events = 0
        critical_events = 0
        compliance_events = 0
        trends: List[TrendData] = []
        
        for record in results:
            total_events += record.get("total", 0)
            critical_events += record.get("critical", 0)
            
            if record.get("compliance"):
                compliance_events += 1
            
            trends.append(TrendData(
                timestamp=record["ts"],
                value=float(record.get("total", 0))
            ))
        
        compliance_rate = (
            (compliance_events / total_events * 100) 
            if total_events > 0 
            else 100.0
        )
        
        return AuditMetrics(
            totalEvents=total_events,
            criticalEvents=critical_events,
            complianceRate=compliance_rate,
            trends=trends[:20]  # Last 20 data points
        )
        
    except Exception as e:
        # Return default metrics on error
        return AuditMetrics(
            totalEvents=0,
            criticalEvents=0,
            complianceRate=100.0,
            trends=[]
        )


async def fetch_fail_closed_events_data(
    neo4j: Neo4jConnection,
    limit: int = 10
) -> List[FailClosedEvent]:
    """Fetch recent fail-closed safety events"""
    
    query = """
    MATCH (event:FailClosedEvent)
    WHERE event.timestamp > datetime() - duration('PT24H')
    RETURN 
        event.id as id,
        event.type as type,
        event.reason as reason,
        event.impact as impact,
        event.timestamp as timestamp,
        event.recovered as recovered
    ORDER BY event.timestamp DESC
    LIMIT {limit}
    """
    
    try:
        results = await neo4j.execute_query(query, {"limit": limit})
        
        return [
            FailClosedEvent(
                id=record["id"],
                type=record["type"],
                reason=record["reason"],
                impact=record["impact"],
                timestamp=record["timestamp"],
                recovered=record.get("recovered", False)
            )
            for record in results
        ]
        
    except Exception:
        return []


async def fetch_mutation_stats_data(
    neo4j: Neo4jConnection
) -> MutationAuthorization:
    """Fetch mutation authorization statistics"""
    
    query = """
    MATCH (req:MutationRequest)
    WHERE req.timestamp > datetime() - duration('PT24H')
    WITH 
        count(CASE WHEN req.status = 'PENDING' THEN 1 END) as pending,
        count(CASE WHEN req.status = 'APPROVED' THEN 1 END) as approved,
        count(req) as total,
        avg(req.reviewTime) as avgTime,
        req.riskLevel as risk
    RETURN 
        pending,
        approved,
        total,
        avgTime,
        risk
    """
    
    try:
        results = await neo4j.execute_query(query)
        
        pending = 0
        approved = 0
        total = 0
        avg_time = 0.0
        risk_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for record in results:
            pending += record.get("pending", 0)
            approved += record.get("approved", 0)
            total += record.get("total", 0)
            avg_time = record.get("avgTime", 0.0)
            
            risk = record.get("risk", "low").lower()
            if risk in risk_dist:
                risk_dist[risk] += 1
        
        approval_rate = (approved / total * 100) if total > 0 else 100.0
        
        return MutationAuthorization(
            pendingRequests=pending,
            approvalRate=approval_rate,
            averageReviewTime=avg_time,
            riskDistribution=RiskDistribution(**risk_dist)
        )
        
    except Exception:
        return MutationAuthorization(
            pendingRequests=0,
            approvalRate=100.0,
            averageReviewTime=0.0,
            riskDistribution=RiskDistribution(
                low=0, medium=0, high=0, critical=0
            )
        )


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/health", response_model=ConstitutionalHealth)
async def get_governance_health(
    governance_ctx: GovernanceContext = Depends(),
    neo4j: Neo4jConnection = Depends(),
    _: None = Depends(require_permissions([Permission.READ]))
):
    """
    Get overall constitutional health status
    
    Returns:
    - Overall health status (healthy/degraded/critical)
    - Compliance score (0-100)
    - List of active issues
    - Last validation timestamp
    """
    
    # Fetch current issues
    issues = await fetch_governance_issues(governance_ctx, neo4j)
    
    # Calculate health score
    score = await calculate_health_score(governance_ctx, issues)
    
    # Determine status
    status = determine_health_status(score)
    
    return ConstitutionalHealth(
        status=status,
        score=score,
        issues=issues,
        lastValidation=datetime.utcnow()
    )


@router.get("/audit/metrics", response_model=AuditMetrics)
async def get_audit_metrics(
    hours: int = 24,
    neo4j: Neo4jConnection = Depends(),
    _: None = Depends(require_permissions([Permission.READ]))
):
    """
    Get aggregated audit event metrics
    
    Parameters:
    - hours: Time window in hours (default: 24)
    
    Returns:
    - Total audit events
    - Critical events count
    - Compliance rate
    - Time series trends
    """
    
    return await fetch_audit_metrics_data(neo4j, hours)


@router.get("/fail-closed/recent", response_model=List[FailClosedEvent])
async def get_fail_closed_events(
    limit: int = 10,
    neo4j: Neo4jConnection = Depends(),
    _: None = Depends(require_permissions([Permission.READ]))
):
    """
    Get recent fail-closed safety events
    
    Parameters:
    - limit: Maximum number of events to return (default: 10)
    
    Returns:
    - List of recent fail-closed events with recovery status
    """
    
    return await fetch_fail_closed_events_data(neo4j, limit)


@router.get("/mutations/stats", response_model=MutationAuthorization)
async def get_mutation_stats(
    neo4j: Neo4jConnection = Depends(),
    _: None = Depends(require_permissions([Permission.READ]))
):
    """
    Get mutation authorization statistics
    
    Returns:
    - Pending mutation requests
    - Approval rate
    - Average review time
    - Risk distribution breakdown
    """
    
    return await fetch_mutation_stats_data(neo4j)
