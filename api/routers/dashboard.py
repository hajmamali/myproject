"""
Dashboard API Router

Provides metrics and data for both Studio (developer) and Portal (user) dashboards.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

# ============================================================================
# Response Models
# ============================================================================

class SystemHealthMetric(BaseModel):
    """System health metric"""
    component: str
    status: str  # healthy, warning, error
    value: float
    unit: str
    threshold: float
    last_updated: datetime

class QuickAction(BaseModel):
    """Quick action button"""
    id: str
    title: str
    description: str
    icon: str
    route: str
    requires_role: str

class AlertItem(BaseModel):
    """Alert notification"""
    id: str
    severity: str  # info, warning, error, critical
    title: str
    message: str
    timestamp: datetime
    component: str
    acknowledged: bool = False

class MetricTimeSeries(BaseModel):
    """Time series metric data point"""
    timestamp: datetime
    value: float

class RecentActivity(BaseModel):
    """Recent user activity"""
    id: str
    type: str  # query, upload, training, etc.
    title: str
    description: str
    timestamp: datetime
    status: str  # success, pending, failed
    user: Optional[str] = None

class UsageStat(BaseModel):
    """Usage statistics"""
    label: str
    current: int
    total: int
    percentage: float
    change: float  # percentage change from previous period

# ============================================================================
# Studio Dashboard Endpoints (Developer/Admin)
# ============================================================================

@router.get("/studio/overview")
async def get_studio_overview():
    """
    Get Studio dashboard overview
    
    Returns system health, metrics, quick actions, and alerts for developers.
    """
    # System health metrics
    health_metrics = [
        SystemHealthMetric(
            component="API Server",
            status="healthy",
            value=99.8,
            unit="%",
            threshold=95.0,
            last_updated=datetime.utcnow()
        ),
        SystemHealthMetric(
            component="Neo4j Database",
            status="healthy",
            value=87.3,
            unit="%",
            threshold=80.0,
            last_updated=datetime.utcnow()
        ),
        SystemHealthMetric(
            component="PostgreSQL",
            status="warning",
            value=92.1,
            unit="%",
            threshold=90.0,
            last_updated=datetime.utcnow()
        ),
        SystemHealthMetric(
            component="Redis Cache",
            status="healthy",
            value=98.5,
            unit="%",
            threshold=95.0,
            last_updated=datetime.utcnow()
        ),
    ]
    
    # Quick actions
    quick_actions = [
        QuickAction(
            id="view_graph",
            title="مشاهده گراف دانش",
            description="نمایش تعاملی گراف دانش",
            icon="graph",
            route="/app/studio/graph",
            requires_role="ANALYST"
        ),
        QuickAction(
            id="train_model",
            title="آموزش مدل",
            description="شروع جلسه آموزش جدید",
            icon="brain",
            route="/app/studio/training",
            requires_role="ADMIN"
        ),
        QuickAction(
            id="view_logs",
            title="مشاهده لاگ‌ها",
            description="بررسی لاگ‌های سیستم",
            icon="file-text",
            route="/app/studio/logs",
            requires_role="ANALYST"
        ),
        QuickAction(
            id="manage_datasets",
            title="مدیریت دیتاست‌ها",
            description="مدیریت مجموعه داده‌ها",
            icon="database",
            route="/app/studio/datasets",
            requires_role="ANALYST"
        ),
    ]
    
    # Recent alerts
    alerts = [
        AlertItem(
            id="alert_1",
            severity="warning",
            title="استفاده از حافظه بالا",
            message="استفاده از RAM به 85% رسیده است",
            timestamp=datetime.utcnow() - timedelta(minutes=15),
            component="API Server",
            acknowledged=False
        ),
        AlertItem(
            id="alert_2",
            severity="info",
            title="به‌روزرسانی مدل",
            message="مدل جدید با موفقیت مستقر شد",
            timestamp=datetime.utcnow() - timedelta(hours=2),
            component="Model Training",
            acknowledged=True
        ),
    ]
    
    # Real-time metrics (last 24 hours)
    now = datetime.utcnow()
    query_metrics = [
        MetricTimeSeries(
            timestamp=now - timedelta(hours=24-i),
            value=random.uniform(50, 200)
        )
        for i in range(24)
    ]
    
    return {
        "health_metrics": health_metrics,
        "quick_actions": quick_actions,
        "alerts": alerts,
        "metrics": {
            "queries_per_hour": query_metrics,
            "total_queries_today": 1847,
            "avg_response_time": 0.342,
            "error_rate": 0.012,
            "active_users": 23,
        },
        "system_info": {
            "version": "1.2.0",
            "uptime_hours": 168.5,
            "last_deployment": (now - timedelta(days=7)).isoformat(),
            "environment": "production",
        }
    }


@router.get("/studio/metrics/realtime")
async def get_realtime_metrics():
    """
    Get real-time system metrics
    
    Returns current system metrics for live monitoring.
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_usage": random.uniform(20, 80),
        "memory_usage": random.uniform(60, 85),
        "disk_usage": random.uniform(40, 70),
        "network_in": random.uniform(1, 10),  # MB/s
        "network_out": random.uniform(0.5, 5),  # MB/s
        "active_connections": random.randint(10, 50),
        "queries_per_second": random.uniform(2, 15),
        "cache_hit_rate": random.uniform(0.85, 0.98),
    }


@router.get("/studio/alerts")
async def get_studio_alerts(severity: Optional[str] = None, limit: int = 50):
    """
    Get system alerts
    
    Args:
        severity: Filter by severity (info, warning, error, critical)
        limit: Maximum number of alerts to return
    """
    alerts = [
        AlertItem(
            id=f"alert_{i}",
            severity=random.choice(["info", "warning", "error"]),
            title=f"هشدار {i}",
            message=f"پیام هشدار شماره {i}",
            timestamp=datetime.utcnow() - timedelta(minutes=i*10),
            component=random.choice(["API", "Database", "Cache", "Model"]),
            acknowledged=random.choice([True, False])
        )
        for i in range(20)
    ]
    
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    return {
        "alerts": alerts[:limit],
        "total": len(alerts),
        "unacknowledged": len([a for a in alerts if not a.acknowledged])
    }


@router.post("/studio/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """
    Acknowledge an alert
    """
    logger.info(f"Alert {alert_id} acknowledged")
    return {
        "success": True,
        "alert_id": alert_id,
        "acknowledged_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# Portal Dashboard Endpoints (Regular Users)
# ============================================================================

@router.get("/portal/overview")
async def get_portal_overview():
    """
    Get Portal dashboard overview
    
    Returns user-specific activities, usage stats, and recent queries.
    """
    # Recent activities
    activities = [
        RecentActivity(
            id=f"activity_{i}",
            type=random.choice(["query", "upload", "export"]),
            title=f"پرس‌وجوی حقوقی {i}",
            description=f"جستجوی رأی دادگاه - موضوع {i}",
            timestamp=datetime.utcnow() - timedelta(hours=i),
            status=random.choice(["success", "pending", "failed"]),
            user="کاربر فعلی"
        )
        for i in range(10)
    ]
    
    # Usage statistics
    usage_stats = [
        UsageStat(
            label="پرس‌وجوهای امروز",
            current=47,
            total=100,
            percentage=47.0,
            change=12.5
        ),
        UsageStat(
            label="مدارک بارگذاری شده",
            current=23,
            total=50,
            percentage=46.0,
            change=-5.2
        ),
        UsageStat(
            label="گزارش‌های تولید شده",
            current=8,
            total=20,
            percentage=40.0,
            change=25.0
        ),
    ]
    
    # Recent queries with results
    recent_queries = [
        {
            "id": f"query_{i}",
            "question": f"سوال حقوقی شماره {i}",
            "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
            "status": "completed",
            "confidence": random.uniform(0.85, 0.98),
            "verdict_count": random.randint(3, 15)
        }
        for i in range(5)
    ]
    
    return {
        "activities": activities,
        "usage_stats": usage_stats,
        "recent_queries": recent_queries,
        "user_info": {
            "total_queries": 1247,
            "total_uploads": 89,
            "member_since": "2024-01-15",
            "last_login": datetime.utcnow().isoformat(),
        },
        "quick_stats": {
            "queries_this_week": 47,
            "avg_confidence": 0.923,
            "saved_searches": 12,
            "bookmarked_verdicts": 34,
        }
    }


@router.get("/portal/activities")
async def get_user_activities(
    activity_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get user activities with pagination
    
    Args:
        activity_type: Filter by type (query, upload, export)
        limit: Number of activities per page
        offset: Pagination offset
    """
    activities = [
        RecentActivity(
            id=f"activity_{i}",
            type=random.choice(["query", "upload", "export"]),
            title=f"فعالیت {i}",
            description=f"توضیحات فعالیت {i}",
            timestamp=datetime.utcnow() - timedelta(hours=i),
            status=random.choice(["success", "pending", "failed"]),
        )
        for i in range(100)
    ]
    
    if activity_type:
        activities = [a for a in activities if a.type == activity_type]
    
    paginated = activities[offset:offset + limit]
    
    return {
        "activities": paginated,
        "total": len(activities),
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < len(activities)
    }


@router.get("/portal/stats/weekly")
async def get_weekly_stats():
    """
    Get weekly usage statistics
    """
    days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
    
    return {
        "queries_per_day": [
            {
                "day": day,
                "count": random.randint(5, 25)
            }
            for day in days
        ],
        "total_queries": 94,
        "avg_per_day": 13.4,
        "peak_day": "سه‌شنبه",
        "week_start": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        "week_end": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Common Endpoints (Both Studio and Portal)
# ============================================================================

@router.get("/search/suggestions")
async def get_search_suggestions(query: str, limit: int = 10):
    """
    Get search suggestions based on query
    """
    suggestions = [
        f"{query} - پیشنهاد {i}"
        for i in range(min(limit, 5))
    ]
    
    return {
        "query": query,
        "suggestions": suggestions
    }


@router.get("/notifications/unread")
async def get_unread_notifications():
    """
    Get unread notifications count
    """
    return {
        "count": random.randint(0, 15),
        "has_critical": random.choice([True, False])
    }
