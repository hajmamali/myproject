"""
Monitoring module for Mahoun platform.

Provides enterprise-grade monitoring with Prometheus metrics,
SLA tracking, legal-specific analytics, and alerting.
"""

# Safe imports first (no pandas dependency)
from mahoun.monitoring.anomaly_detector import (
    StatisticalAnomalyDetector,
    PerformanceDegradationDetector,
    AnomalyDetectionSystem,
    AnomalyAlert,
)

# Optional imports (may require pandas via self_improve)
try:
    from mahoun.monitoring.legal_metrics import (
        legal_monitoring,
        UltraProfessionalLegalMonitoring,
        LegalMetricType,
        track_legal_query_decorator,
    )
    from mahoun.monitoring.alerting import (
        AlertingSystem,
        Alert,
        AlertSeverity,
        AlertChannel,
        AlertRule,
        get_alerting_system,
        send_alert,
    )
    _FULL_MONITORING_AVAILABLE = True
except ImportError:
    # Graceful degradation if pandas not installed
    _FULL_MONITORING_AVAILABLE = False
    legal_monitoring = None
    UltraProfessionalLegalMonitoring = None
    LegalMetricType = None
    track_legal_query_decorator = None
    AlertingSystem = None
    Alert = None
    AlertSeverity = None
    AlertChannel = None
    AlertRule = None
    get_alerting_system = None
    send_alert = None

__all__ = [
    # Anomaly Detection (always available)
    "StatisticalAnomalyDetector",
    "PerformanceDegradationDetector",
    "AnomalyDetectionSystem",
    "AnomalyAlert",
    # Legal monitoring (optional)
    "legal_monitoring",
    "UltraProfessionalLegalMonitoring",
    "LegalMetricType",
    "track_legal_query_decorator",
    # Alerting (optional)
    "AlertingSystem",
    "Alert",
    "AlertSeverity",
    "AlertChannel",
    "AlertRule",
    "get_alerting_system",
    "send_alert",
]
