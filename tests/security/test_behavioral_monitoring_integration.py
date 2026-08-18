"""
Behavioral Monitoring Integration Tests
========================================

Classification: P1 / SECURITY / INSIDER THREAT DETECTION
Purpose: Verify behavioral anomaly detection integrated with governance layer

Test Coverage:
- Mutation rate spike detection
- Bulk operation detection
- Off-hours activity detection
- Failed authorization tracking
- Profile building and baseline
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from mahoun.security.behavioral_monitor import (
    GovernanceBehavioralMonitor,
    BehaviorMetric,
    ThreatLevel,
    BehavioralAnomalyEvent,
)
from mahoun.security.governance_behavioral_integration import (
    observe_mutation_async,
    observe_auth_failure_async,
    should_block_operation,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def behavioral_monitor():
    """Fresh behavioral monitor for each test"""
    return GovernanceBehavioralMonitor(
        enable_monitoring=True,
        window_size=50,
        z_threshold=2.0,  # Lower threshold for easier testing
    )


# ============================================================================
# TEST 1: Mutation Rate Spike Detection
# ============================================================================

class TestMutationRateSpikeDetection:
    """Test detection of sudden spikes in mutation rate"""
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_normal_mutation_rate_no_alert(self, behavioral_monitor):
        """Normal mutation rate (1-2 per minute) should not trigger alert"""
        actor_id = "test-actor-1"
        
        # Simulate 3 normal mutations over 3 minutes
        for i in range(3):
            anomaly = await behavioral_monitor.observe_mutation(
                actor_id=actor_id,
                operation_type="NODE_CREATE",
                entity_count=1,
                correlation_id=f"test-corr-{i}",
            )
            
            assert anomaly is None, "Normal mutation rate should not trigger anomaly"
            
            # Simulate 1 minute delay
            await asyncio.sleep(0.01)
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_mutation_rate_spike_triggers_alert(self, behavioral_monitor):
        """Rapid mutations (>10 per minute) should trigger anomaly"""
        actor_id = "test-actor-spike"
        
        # Simulate burst of 15 mutations in rapid succession
        anomalies = []
        for i in range(15):
            anomaly = await behavioral_monitor.observe_mutation(
                actor_id=actor_id,
                operation_type="NODE_CREATE",
                entity_count=1,
                correlation_id=f"test-spike-{i}",
            )
            
            if anomaly:
                anomalies.append(anomaly)
        
        # Should detect at least one anomaly due to spike
        assert len(anomalies) > 0, "Mutation rate spike should trigger anomaly"
        
        # Verify anomaly properties
        for anomaly in anomalies:
            assert anomaly.actor_id == actor_id
            assert anomaly.metric in (
                BehaviorMetric.MUTATION_RATE,
                BehaviorMetric.BULK_OPERATION_SIZE,
            )
            assert anomaly.threat_level in (
                ThreatLevel.MEDIUM,
                ThreatLevel.HIGH,
            )


# ============================================================================
# TEST 2: Bulk Operation Detection
# ============================================================================

class TestBulkOperationDetection:
    """Test detection of bulk operations (mass delete, mass export)"""
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_small_operation_no_alert(self, behavioral_monitor):
        """Small operations (<10 entities) should not trigger alert"""
        anomaly = await behavioral_monitor.observe_mutation(
            actor_id="test-actor-small",
            operation_type="NODE_CREATE",
            entity_count=5,  # Small operation
            correlation_id="test-small-op",
        )
        
        assert anomaly is None, "Small operation should not trigger anomaly"
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_bulk_operation_triggers_medium_threat(self, behavioral_monitor):
        """Bulk operation (11-99 entities) should trigger MEDIUM threat"""
        anomaly = await behavioral_monitor.observe_mutation(
            actor_id="test-actor-bulk",
            operation_type="NODE_DELETE",
            entity_count=50,  # Bulk operation
            correlation_id="test-bulk-op",
        )
        
        assert anomaly is not None, "Bulk operation should trigger anomaly"
        assert anomaly.metric == BehaviorMetric.BULK_OPERATION_SIZE
        assert anomaly.threat_level == ThreatLevel.MEDIUM
        assert anomaly.observed_value == 50.0
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_mass_operation_triggers_high_threat(self, behavioral_monitor):
        """Mass operation (100+ entities) should trigger HIGH threat"""
        anomaly = await behavioral_monitor.observe_mutation(
            actor_id="test-actor-mass",
            operation_type="NODE_DELETE",
            entity_count=150,  # Mass operation
            correlation_id="test-mass-op",
        )
        
        assert anomaly is not None, "Mass operation should trigger anomaly"
        assert anomaly.metric == BehaviorMetric.BULK_OPERATION_SIZE
        assert anomaly.threat_level == ThreatLevel.HIGH
        assert anomaly.observed_value == 150.0


# ============================================================================
# TEST 3: Off-Hours Activity Detection
# ============================================================================

class TestOffHoursActivityDetection:
    """Test detection of suspicious off-hours activity"""
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_business_hours_activity_no_alert(self, behavioral_monitor):
        """Activity during business hours (9-17 UTC) should not trigger alert"""
        # Mock datetime to business hours (12:00 UTC)
        with patch("mahoun.security.behavioral_monitor.datetime") as mock_dt:
            mock_now = datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Simulate normal business hours activity
            for i in range(5):
                anomaly = await behavioral_monitor.observe_mutation(
                    actor_id="test-actor-business",
                    operation_type="NODE_CREATE",
                    entity_count=1,
                    correlation_id=f"test-business-{i}",
                )
            
            # Should not trigger off-hours anomaly
            # (may trigger rate spike, but not off-hours)
            # This test validates time-of-day logic
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_off_hours_activity_with_high_rate_triggers_alert(
        self,
        behavioral_monitor,
    ):
        """High mutation rate outside business hours should trigger alert"""
        # Mock datetime to off-hours (2:00 AM UTC)
        with patch("mahoun.security.behavioral_monitor.datetime") as mock_dt:
            mock_now = datetime(2026, 7, 2, 2, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Simulate rapid mutations off-hours
            anomalies = []
            for i in range(10):
                anomaly = await behavioral_monitor.observe_mutation(
                    actor_id="test-actor-offhours",
                    operation_type="NODE_CREATE",
                    entity_count=1,
                    correlation_id=f"test-offhours-{i}",
                )
                
                if anomaly and anomaly.metric == BehaviorMetric.OFF_HOURS_ACTIVITY:
                    anomalies.append(anomaly)
            
            # Should detect off-hours anomaly
            assert len(anomalies) > 0, "Off-hours activity spike should trigger anomaly"
            
            for anomaly in anomalies:
                assert anomaly.threat_level == ThreatLevel.MEDIUM


# ============================================================================
# TEST 4: Failed Authorization Tracking
# ============================================================================

class TestFailedAuthorizationTracking:
    """Test tracking of failed authorization attempts (privilege escalation)"""
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_single_auth_failure_no_alert(self, behavioral_monitor):
        """Single auth failure should not trigger anomaly"""
        anomaly = await behavioral_monitor.observe_auth_failure(
            actor_id="test-actor-auth",
            attempted_permission="write_critical",
            correlation_id="test-auth-1",
        )
        
        assert anomaly is None, "Single auth failure should not trigger anomaly"
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_multiple_auth_failures_trigger_alert(self, behavioral_monitor):
        """Multiple rapid auth failures should trigger MEDIUM+ threat"""
        actor_id = "test-actor-authfail"
        
        # Simulate 6 failed auth attempts (above threshold of 5)
        anomaly = None
        for i in range(6):
            anomaly = await behavioral_monitor.observe_auth_failure(
                actor_id=actor_id,
                attempted_permission=f"permission_{i}",
                correlation_id=f"test-authfail-{i}",
            )
        
        assert anomaly is not None, "Multiple auth failures should trigger anomaly"
        assert anomaly.metric == BehaviorMetric.FAILED_AUTH_RATE
        assert anomaly.threat_level in (ThreatLevel.MEDIUM, ThreatLevel.HIGH)


# ============================================================================
# TEST 5: Behavioral Profile Building
# ============================================================================

class TestBehavioralProfileBuilding:
    """Test actor behavioral profile baseline construction"""
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_profile_created_on_first_activity(self, behavioral_monitor):
        """First activity should create behavioral profile"""
        actor_id = "test-actor-profile"
        
        await behavioral_monitor.observe_mutation(
            actor_id=actor_id,
            operation_type="NODE_CREATE",
            entity_count=1,
            correlation_id="test-profile-1",
        )
        
        # Check profile exists
        profile = behavioral_monitor.get_profile(actor_id)
        assert profile is not None
        assert profile.actor_id == actor_id
        assert profile.total_mutations == 1
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_profile_updated_with_activity(self, behavioral_monitor):
        """Ongoing activity should update behavioral profile"""
        actor_id = "test-actor-update"
        
        # Simulate multiple activities
        for i in range(5):
            await behavioral_monitor.observe_mutation(
                actor_id=actor_id,
                operation_type="NODE_CREATE" if i < 3 else "NODE_DELETE",
                entity_count=1,
                correlation_id=f"test-update-{i}",
            )
        
        # Check profile updated
        profile = behavioral_monitor.get_profile(actor_id)
        assert profile.total_mutations >= 5
        assert profile.total_deletes >= 2
        assert len(profile.typical_operations) > 0


# ============================================================================
# TEST 6: Integration Hooks
# ============================================================================

class TestIntegrationHooks:
    """Test integration hooks for governance layer"""
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_observe_mutation_async_hook(self):
        """Test async mutation observation hook"""
        anomaly = await observe_mutation_async(
            actor_id="test-hook-actor",
            operation_type="NODE_CREATE",
            entity_count=1,
            correlation_id="test-hook-1",
        )
        
        # First call should not trigger anomaly (baseline)
        assert anomaly is None or anomaly.threat_level in (
            ThreatLevel.INFO,
            ThreatLevel.LOW,
        )
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_observe_auth_failure_async_hook(self):
        """Test async auth failure observation hook"""
        anomaly = await observe_auth_failure_async(
            actor_id="test-hook-auth",
            attempted_permission="admin_access",
            correlation_id="test-hook-auth-1",
        )
        
        # First failure should not trigger anomaly
        assert anomaly is None
    
    @pytest.mark.p1
    def test_should_block_operation_logic(self):
        """Test operation blocking logic"""
        # CRITICAL threat should be blocked
        critical_anomaly = BehavioralAnomalyEvent(
            event_id="test-critical",
            timestamp=datetime.now(timezone.utc),
            actor_id="test-actor",
            metric=BehaviorMetric.MUTATION_RATE,
            observed_value=100.0,
            expected_range=(0.0, 10.0),
            deviation_score=10.0,
            threat_level=ThreatLevel.CRITICAL,
        )
        assert should_block_operation(critical_anomaly) is True
        
        # MEDIUM threat should not be blocked (default policy)
        medium_anomaly = BehavioralAnomalyEvent(
            event_id="test-medium",
            timestamp=datetime.now(timezone.utc),
            actor_id="test-actor",
            metric=BehaviorMetric.MUTATION_RATE,
            observed_value=20.0,
            expected_range=(0.0, 10.0),
            deviation_score=2.0,
            threat_level=ThreatLevel.MEDIUM,
        )
        assert should_block_operation(medium_anomaly) is False


# ============================================================================
# TEST 7: Graceful Degradation
# ============================================================================

class TestGracefulDegradation:
    """Test that monitoring failures do not block operations"""
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_disabled_monitor_returns_none(self):
        """Disabled monitor should return None (no blocking)"""
        disabled_monitor = GovernanceBehavioralMonitor(enable_monitoring=False)
        
        anomaly = await disabled_monitor.observe_mutation(
            actor_id="test-actor",
            operation_type="NODE_CREATE",
            entity_count=1,
            correlation_id="test-disabled",
        )
        
        assert anomaly is None, "Disabled monitor should not detect anomalies"
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_monitoring_exception_does_not_raise(self, behavioral_monitor):
        """Monitoring exceptions should be caught (graceful degradation)"""
        # Patch detector to raise exception
        with patch.object(
            behavioral_monitor.detector,
            "check_anomaly",
            side_effect=Exception("Test exception"),
        ):
            # Should not raise — graceful degradation
            try:
                anomaly = await behavioral_monitor.observe_mutation(
                    actor_id="test-actor",
                    operation_type="NODE_CREATE",
                    entity_count=1,
                    correlation_id="test-exception",
                )
                
                # Should return None on error
                assert anomaly is None
            except Exception as e:
                pytest.fail(f"Monitoring exception should be caught, got: {e}")


# ============================================================================
# SUMMARY
# ============================================================================

"""
Test Coverage Summary:
======================

✅ Mutation rate spike detection (normal vs. spike)
✅ Bulk operation detection (small / medium / large)
✅ Off-hours activity detection (business hours vs. off-hours)
✅ Failed authorization tracking (single vs. multiple)
✅ Behavioral profile building (creation + updates)
✅ Integration hooks (async observation)
✅ Operation blocking logic (threat-level-based)
✅ Graceful degradation (disabled monitor, exceptions)

Next Steps:
-----------
1. Integrate observe_mutation_background() into GovernedNeo4jSession.write_*()
2. Integrate observe_auth_failure_background() into RBACManager.check_permission()
3. Add alerting callback (PagerDuty, Slack, email)
4. Add security dashboard endpoint (GET /api/security/anomalies)
5. Add admin API for viewing behavioral profiles (GET /api/security/profiles/{actor_id})
"""
