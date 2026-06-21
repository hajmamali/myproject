"""
Alerting System
===============

Production-grade alerting with multiple channels.

Features:
- PagerDuty integration (critical alerts)
- Slack integration (team notifications)
- Email alerts (configurable)
- Alert deduplication
- Alert severity levels
- Alert routing rules
- Rate limiting

Supports incident management workflows.
"""

import os
import json
import time
import logging
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone, timedelta
from enum import Enum
from threading import RLock
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"  # System down, immediate action required
    ERROR = "error"  # Significant issue, action required soon
    WARNING = "warning"  # Potential issue, investigate
    INFO = "info"  # Informational, no action required


class AlertChannel(str, Enum):
    """Alert delivery channels"""
    PAGERDUTY = "pagerduty"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """Alert with metadata"""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    source: str  # Component that generated alert
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict = field(default_factory=dict)
    dedup_key: Optional[str] = None  # For deduplication
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['severity'] = self.severity.value
        return data
    
    def compute_dedup_key(self) -> str:
        """Compute deduplication key"""
        if self.dedup_key:
            return self.dedup_key
        
        # Generate from title + source
        data = f"{self.title}:{self.source}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class AlertRule:
    """Alert routing rule"""
    name: str
    severity_levels: List[AlertSeverity]
    channels: List[AlertChannel]
    source_pattern: Optional[str] = None  # Regex pattern for source
    enabled: bool = True


class AlertingSystem:
    """
    Production-grade alerting system.
    
    Features:
    - Multiple channels (PagerDuty, Slack, Email)
    - Alert deduplication
    - Severity-based routing
    - Rate limiting
    - Alert history
    - Thread-safe operations
    
    Usage:
        alerting = AlertingSystem()
        
        # Configure channels
        alerting.configure_pagerduty(
            api_key=os.getenv("PAGERDUTY_API_KEY"),
            service_id=os.getenv("PAGERDUTY_SERVICE_ID")
        )
        
        alerting.configure_slack(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL")
        )
        
        # Send alert
        alert = Alert(
            alert_id="alert_001",
            title="High error rate detected",
            description="Error rate exceeded 5% threshold",
            severity=AlertSeverity.ERROR,
            source="api_monitoring"
        )
        
        alerting.send(alert)
    """
    
    def __init__(
        self,
        enable_deduplication: bool = True,
        dedup_window_seconds: int = 300,  # 5 minutes
        rate_limit_per_minute: int = 10
    ):
        """
        Initialize alerting system.
        
        Args:
            enable_deduplication: Enable alert deduplication
            dedup_window_seconds: Deduplication window
            rate_limit_per_minute: Max alerts per minute
        """
        self.enable_deduplication = enable_deduplication
        self.dedup_window = dedup_window_seconds
        self.rate_limit = rate_limit_per_minute
        
        # Channel configurations
        self._pagerduty_config: Optional[Dict] = None
        self._slack_config: Optional[Dict] = None
        self._email_config: Optional[Dict] = None
        
        # Alert routing rules
        self._rules: List[AlertRule] = []
        self._setup_default_rules()
        
        # Deduplication tracking
        self._recent_alerts: Dict[str, datetime] = {}  # dedup_key -> last_sent
        
        # Rate limiting
        self._alert_timestamps: List[datetime] = []
        
        # Alert history
        self._alert_history: List[Alert] = []
        self._max_history = 1000
        
        # Statistics
        self._total_alerts = 0
        self._deduplicated_alerts = 0
        self._rate_limited_alerts = 0
        
        # Thread safety
        self._lock = RLock()
        
        logger.info(
            f"AlertingSystem initialized "
            f"(dedup={enable_deduplication}, rate_limit={rate_limit_per_minute}/min)"
        )
    
    def configure_pagerduty(
        self,
        api_key: str,
        service_id: str,
        integration_key: Optional[str] = None
    ) -> None:
        """
        Configure PagerDuty integration.
        
        Args:
            api_key: PagerDuty API key
            service_id: PagerDuty service ID
            integration_key: Integration key (Events API v2)
        """
        self._pagerduty_config = {
            "api_key": api_key,
            "service_id": service_id,
            "integration_key": integration_key,
        }
        
        logger.info("PagerDuty configured")
    
    def configure_slack(
        self,
        webhook_url: str,
        channel: Optional[str] = None
    ) -> None:
        """
        Configure Slack integration.
        
        Args:
            webhook_url: Slack webhook URL
            channel: Optional channel override
        """
        self._slack_config = {
            "webhook_url": webhook_url,
            "channel": channel,
        }
        
        logger.info("Slack configured")
    
    def configure_email(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_address: str,
        to_addresses: List[str]
    ) -> None:
        """
        Configure email integration.
        
        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_address: From email address
            to_addresses: List of recipient addresses
        """
        self._email_config = {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_address": from_address,
            "to_addresses": to_addresses,
        }
        
        logger.info("Email configured")
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add alert routing rule"""
        with self._lock:
            self._rules.append(rule)
            logger.info(f"Added alert rule: {rule.name}")
    
    def send(self, alert: Alert) -> bool:
        """
        Send alert through configured channels.
        
        Args:
            alert: Alert to send
            
        Returns:
            True if sent successfully
        """
        with self._lock:
            self._total_alerts += 1
            
            # Check deduplication
            if self.enable_deduplication:
                dedup_key = alert.compute_dedup_key()
                
                if dedup_key in self._recent_alerts:
                    last_sent = self._recent_alerts[dedup_key]
                    time_since = (datetime.now(timezone.utc) - last_sent).total_seconds()
                    
                    if time_since < self.dedup_window:
                        self._deduplicated_alerts += 1
                        logger.debug(f"Alert deduplicated: {alert.title}")
                        return False
                
                self._recent_alerts[dedup_key] = datetime.now(timezone.utc)
            
            # Check rate limiting
            if not self._check_rate_limit():
                self._rate_limited_alerts += 1
                logger.warning(f"Alert rate limited: {alert.title}")
                return False
            
            # Store in history
            self._alert_history.append(alert)
            if len(self._alert_history) > self._max_history:
                self._alert_history.pop(0)
            
            # Determine channels based on rules
            channels = self._get_channels_for_alert(alert)
            
            # Send to each channel
            success = True
            for channel in channels:
                try:
                    if channel == AlertChannel.PAGERDUTY:
                        self._send_pagerduty(alert)
                    elif channel == AlertChannel.SLACK:
                        self._send_slack(alert)
                    elif channel == AlertChannel.EMAIL:
                        self._send_email(alert)
                except Exception as e:
                    logger.error(f"Failed to send alert to {channel.value}: {e}")
                    success = False
            
            logger.info(
                f"Alert sent: {alert.title} "
                f"(severity={alert.severity.value}, channels={[c.value for c in channels]})"
            )
            
            return success
    
    def _setup_default_rules(self) -> None:
        """Setup default routing rules"""
        # Critical alerts -> PagerDuty + Slack
        self._rules.append(AlertRule(
            name="critical_alerts",
            severity_levels=[AlertSeverity.CRITICAL],
            channels=[AlertChannel.PAGERDUTY, AlertChannel.SLACK]
        ))
        
        # Error alerts -> Slack
        self._rules.append(AlertRule(
            name="error_alerts",
            severity_levels=[AlertSeverity.ERROR],
            channels=[AlertChannel.SLACK]
        ))
        
        # Warning alerts -> Slack (low priority)
        self._rules.append(AlertRule(
            name="warning_alerts",
            severity_levels=[AlertSeverity.WARNING],
            channels=[AlertChannel.SLACK]
        ))
    
    def _get_channels_for_alert(self, alert: Alert) -> List[AlertChannel]:
        """Determine which channels to use for alert"""
        channels: Set[AlertChannel] = set()
        
        for rule in self._rules:
            if not rule.enabled:
                continue
            
            # Check severity
            if alert.severity not in rule.severity_levels:
                continue
            
            # Check source pattern (if specified)
            if rule.source_pattern:
                import re
                if not re.match(rule.source_pattern, alert.source):
                    continue
            
            # Add channels
            channels.update(rule.channels)
        
        return list(channels)
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows sending"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=1)
        
        # Remove old timestamps
        self._alert_timestamps = [
            ts for ts in self._alert_timestamps
            if ts > cutoff
        ]
        
        # Check limit
        if len(self._alert_timestamps) >= self.rate_limit:
            return False
        
        # Add current timestamp
        self._alert_timestamps.append(now)
        return True
    
    def _send_pagerduty(self, alert: Alert) -> None:
        """Send alert to PagerDuty"""
        if not self._pagerduty_config:
            logger.warning("PagerDuty not configured")
            return
        
        try:
            import requests
            
            # Use Events API v2
            url = "https://events.pagerduty.com/v2/enqueue"
            
            payload = {
                "routing_key": self._pagerduty_config["integration_key"],
                "event_action": "trigger",
                "dedup_key": alert.compute_dedup_key(),
                "payload": {
                    "summary": alert.title,
                    "severity": alert.severity.value,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "custom_details": alert.metadata,
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"Sent alert to PagerDuty: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"PagerDuty send failed: {e}")
            raise
    
    def _send_slack(self, alert: Alert) -> None:
        """Send alert to Slack"""
        if not self._slack_config:
            logger.warning("Slack not configured")
            return
        
        try:
            import requests
            
            # Format message
            color = {
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.ERROR: "danger",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.INFO: "good",
            }.get(alert.severity, "warning")
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": alert.title,
                    "text": alert.description,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Source",
                            "value": alert.source,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": False
                        }
                    ],
                    "footer": "Mahoun Alerting",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }
            
            if self._slack_config.get("channel"):
                payload["channel"] = self._slack_config["channel"]
            
            response = requests.post(
                self._slack_config["webhook_url"],
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.debug(f"Sent alert to Slack: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            raise
    
    def _send_email(self, alert: Alert) -> None:
        """Send alert via email"""
        if not self._email_config:
            logger.warning("Email not configured")
            return
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self._email_config["from_address"]
            msg['To'] = ", ".join(self._email_config["to_addresses"])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Email body
            body = f"""
Alert Details:
--------------
Title: {alert.title}
Severity: {alert.severity.value.upper()}
Source: {alert.source}
Time: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

Description:
{alert.description}

Metadata:
{json.dumps(alert.metadata, indent=2)}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(
                self._email_config["smtp_host"],
                self._email_config["smtp_port"]
            ) as server:
                server.starttls()
                server.login(
                    self._email_config["username"],
                    self._email_config["password"]
                )
                server.send_message(msg)
            
            logger.debug(f"Sent alert via email: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            raise
    
    def get_statistics(self) -> Dict:
        """Get alerting statistics"""
        with self._lock:
            return {
                "total_alerts": self._total_alerts,
                "deduplicated_alerts": self._deduplicated_alerts,
                "rate_limited_alerts": self._rate_limited_alerts,
                "history_size": len(self._alert_history),
                "active_rules": len([r for r in self._rules if r.enabled]),
            }
    
    def get_recent_alerts(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        Get recent alerts.
        
        Args:
            limit: Maximum number of alerts
            severity: Filter by severity
            
        Returns:
            List of recent alerts
        """
        with self._lock:
            alerts = self._alert_history.copy()
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            return alerts[-limit:]


# Singleton instance
_alerting_system: Optional[AlertingSystem] = None


def get_alerting_system() -> AlertingSystem:
    """Get or create singleton alerting system"""
    global _alerting_system
    
    if _alerting_system is None:
        _alerting_system = AlertingSystem()
        
        # Auto-configure from environment
        if os.getenv("PAGERDUTY_INTEGRATION_KEY"):
            _alerting_system.configure_pagerduty(
                api_key=os.getenv("PAGERDUTY_API_KEY", ""),
                service_id=os.getenv("PAGERDUTY_SERVICE_ID", ""),
                integration_key=os.getenv("PAGERDUTY_INTEGRATION_KEY")
            )
        
        if os.getenv("SLACK_WEBHOOK_URL"):
            _alerting_system.configure_slack(
                webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
                channel=os.getenv("SLACK_CHANNEL")
            )
    
    return _alerting_system


def send_alert(
    title: str,
    description: str,
    severity: AlertSeverity,
    source: str,
    metadata: Optional[Dict] = None
) -> bool:
    """
    Convenience function to send alert.
    
    Args:
        title: Alert title
        description: Alert description
        severity: Alert severity
        source: Alert source
        metadata: Additional metadata
        
    Returns:
        True if sent successfully
    """
    alerting = get_alerting_system()
    
    alert = Alert(
        alert_id=f"alert_{int(time.time() * 1000)}",
        title=title,
        description=description,
        severity=severity,
        source=source,
        metadata=metadata or {}
    )
    
    return alerting.send(alert)
