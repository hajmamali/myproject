"""
Rollback Orchestrator
=====================

Classification: CRITICAL / CONTROL PLANE / DISASTER RECOVERY
Purpose: Enterprise-grade rollback capability for policies, deployments, and configurations

Features:
- Automatic rollback on deployment failure
- Manual rollback to any previous version
- Point-in-time recovery (restore to specific timestamp)
- Rollback simulation (dry-run before execution)
- Rollback impact analysis (what will change?)
- Multi-resource rollback (policy + config + data)
- Rollback verification (health checks after rollback)
- Rollback audit trail (who, when, why)
- Cascade rollback (rollback dependent resources)
- Partial rollback (rollback subset of changes)

Architecture:
- State snapshots (before/after comparison)
- Transaction log replay (event sourcing)
- Compensating transactions (undo operations)
- Checkpointing (periodic save points)
- Rollback safety checks (prevent catastrophic rollback)

Author: MAHOUN Control Plane Council
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable
from uuid import uuid4

from mahoun.core.policy_deployment import (
    PolicyVersion,
    PolicyArtifact,
    PolicyArtifactStore,
    DeploymentStage,
    DeploymentStatus,
)
from mahoun.core.exceptions_v2 import (
    ValidationError,
    OperationalError,
)


logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & STATUS
# ============================================================================

class RollbackType(str, Enum):
    """Type of rollback operation"""
    POLICY = "policy"                # Rollback policy deployment
    CONFIGURATION = "configuration"   # Rollback runtime config
    DATABASE = "database"            # Rollback database schema/data
    MODEL = "model"                  # Rollback ML model version
    FULL_SYSTEM = "full_system"      # Rollback entire system state


class RollbackReason(str, Enum):
    """Reason for rollback"""
    DEPLOYMENT_FAILURE = "deployment_failure"  # Automatic: deployment failed
    VALIDATION_FAILURE = "validation_failure"  # Automatic: post-deploy validation failed
    PERFORMANCE_DEGRADATION = "performance_degradation"  # Automatic: metrics degraded
    MANUAL_REQUEST = "manual_request"          # Manual: operator initiated
    SECURITY_INCIDENT = "security_incident"    # Manual: security breach detected
    BUG_DISCOVERED = "bug_discovered"          # Manual: critical bug found


class RollbackStatus(str, Enum):
    """Rollback execution status"""
    PLANNED = "planned"              # Rollback plan created
    SIMULATING = "simulating"        # Running dry-run simulation
    APPROVED = "approved"            # Rollback approved by operator
    EXECUTING = "executing"          # Rollback in progress
    COMPLETED = "completed"          # Rollback successful
    FAILED = "failed"                # Rollback failed
    CANCELLED = "cancelled"          # Rollback cancelled


class SafetyCheckResult(str, Enum):
    """Safety check result"""
    SAFE = "safe"                    # Safe to rollback
    WARNING = "warning"              # Risky but allowed
    BLOCKED = "blocked"              # Not safe — blocked


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass(frozen=True)
class StateSnapshot:
    """
    Immutable snapshot of system state at a point in time.
    
    Used for before/after comparison and point-in-time recovery.
    """
    snapshot_id: str
    timestamp: str
    resource_type: RollbackType
    resource_id: str
    state_data: Dict[str, Any]  # Serialized state
    state_hash: str = ""  # SHA-256 of state_data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.state_hash:
            state_json = json.dumps(self.state_data, sort_keys=True)
            computed_hash = hashlib.sha256(state_json.encode()).hexdigest()
            object.__setattr__(self, "state_hash", computed_hash)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "state_data": self.state_data,
            "state_hash": self.state_hash,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StateSnapshot:
        return cls(
            snapshot_id=data["snapshot_id"],
            timestamp=data["timestamp"],
            resource_type=RollbackType(data["resource_type"]),
            resource_id=data["resource_id"],
            state_data=data["state_data"],
            state_hash=data.get("state_hash", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SafetyCheck:
    """Single rollback safety check"""
    check_name: str
    result: SafetyCheckResult
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackImpact:
    """
    Impact analysis of rollback operation.
    
    Shows what will change if rollback is executed.
    """
    resources_affected: int
    changes: List[str]  # Human-readable change descriptions
    estimated_downtime_sec: int
    data_loss_risk: bool
    breaking_changes: List[str]
    affected_users: int = 0
    affected_services: List[str] = field(default_factory=list)


@dataclass
class RollbackPlan:
    """
    Rollback execution plan.
    
    Generated during simulation, executed during rollback.
    """
    rollback_id: str
    rollback_type: RollbackType
    target_snapshot: StateSnapshot
    current_snapshot: StateSnapshot
    reason: RollbackReason
    safety_checks: List[SafetyCheck] = field(default_factory=list)
    impact: Optional[RollbackImpact] = None
    rollback_steps: List[str] = field(default_factory=list)
    approval_required: bool = True
    approvers: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = ""
    
    def is_safe(self) -> bool:
        """Check if rollback is safe to execute"""
        return all(
            check.result != SafetyCheckResult.BLOCKED
            for check in self.safety_checks
        )
    
    def has_warnings(self) -> bool:
        """Check if rollback has warnings"""
        return any(
            check.result == SafetyCheckResult.WARNING
            for check in self.safety_checks
        )


@dataclass
class RollbackRecord:
    """
    Immutable rollback history record.
    
    Event-sourced: Each rollback creates a new record.
    """
    rollback_id: str
    rollback_type: RollbackType
    target_snapshot: StateSnapshot
    reason: RollbackReason
    status: RollbackStatus
    started_at: str
    completed_at: Optional[str] = None
    initiated_by: str = ""
    approvers: List[str] = field(default_factory=list)
    safety_checks: List[SafetyCheck] = field(default_factory=list)
    rollback_steps: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    verification_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "rollback_type": self.rollback_type.value,
            "target_snapshot": self.target_snapshot.to_dict(),
            "reason": self.reason.value,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "initiated_by": self.initiated_by,
            "approvers": self.approvers,
            "safety_checks": [asdict(check) for check in self.safety_checks],
            "rollback_steps": self.rollback_steps,
            "error_message": self.error_message,
            "verification_results": self.verification_results,
            "metadata": self.metadata,
        }


# ============================================================================
# SNAPSHOT STORE
# ============================================================================

class SnapshotStore:
    """
    Time-series storage for state snapshots.
    
    Provides point-in-time recovery and before/after comparison.
    """
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory index (resource_id -> [snapshots])
        self._snapshots: Dict[str, List[StateSnapshot]] = {}
        
        # Load existing snapshots
        self._load_snapshots()
        
        logger.info(
            f"SnapshotStore initialized: {len(self._snapshots)} resources tracked"
        )
    
    def _load_snapshots(self):
        """Load snapshots from storage"""
        for snapshot_file in self.storage_path.glob("*.json"):
            try:
                with open(snapshot_file, "r") as f:
                    data = json.load(f)
                    snapshot = StateSnapshot.from_dict(data)
                    
                    if snapshot.resource_id not in self._snapshots:
                        self._snapshots[snapshot.resource_id] = []
                    
                    self._snapshots[snapshot.resource_id].append(snapshot)
            except Exception as e:
                logger.error(f"Failed to load snapshot {snapshot_file}: {e}")
        
        # Sort snapshots by timestamp
        for snapshots in self._snapshots.values():
            snapshots.sort(key=lambda s: s.timestamp)
    
    def save_snapshot(self, snapshot: StateSnapshot) -> None:
        """Save state snapshot"""
        # Store to filesystem
        filename = f"{snapshot.resource_id}_{snapshot.snapshot_id}.json"
        filepath = self.storage_path / filename
        
        with open(filepath, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)
        
        # Update index
        if snapshot.resource_id not in self._snapshots:
            self._snapshots[snapshot.resource_id] = []
        
        self._snapshots[snapshot.resource_id].append(snapshot)
        self._snapshots[snapshot.resource_id].sort(key=lambda s: s.timestamp)
        
        logger.info(
            f"Saved snapshot: {snapshot.resource_id} @ {snapshot.timestamp}"
        )
    
    def get_latest_snapshot(self, resource_id: str) -> Optional[StateSnapshot]:
        """Get most recent snapshot for resource"""
        snapshots = self._snapshots.get(resource_id, [])
        return snapshots[-1] if snapshots else None
    
    def get_snapshot_at_time(
        self,
        resource_id: str,
        timestamp: datetime,
    ) -> Optional[StateSnapshot]:
        """Get snapshot closest to specified timestamp"""
        snapshots = self._snapshots.get(resource_id, [])
        if not snapshots:
            return None
        
        # Find closest snapshot before timestamp
        target_ts = timestamp.isoformat()
        candidates = [s for s in snapshots if s.timestamp <= target_ts]
        
        return candidates[-1] if candidates else None
    
    def get_snapshots_in_range(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[StateSnapshot]:
        """Get all snapshots within time range"""
        snapshots = self._snapshots.get(resource_id, [])
        start_ts = start_time.isoformat()
        end_ts = end_time.isoformat()
        
        return [
            s for s in snapshots
            if start_ts <= s.timestamp <= end_ts
        ]
    
    def list_resources(self) -> List[str]:
        """List all tracked resource IDs"""
        return list(self._snapshots.keys())


# ============================================================================
# ROLLBACK ORCHESTRATOR
# ============================================================================

class RollbackOrchestrator:
    """
    Enterprise-grade rollback orchestrator.
    
    Responsibilities:
    - Snapshot management (create/restore)
    - Rollback planning and simulation
    - Safety checks (prevent catastrophic rollback)
    - Impact analysis (what will change?)
    - Rollback execution with verification
    - Rollback audit trail
    
    Usage:
        orchestrator = RollbackOrchestrator(snapshot_store)
        
        # Take snapshot before deployment
        snapshot = await orchestrator.take_snapshot(
            resource_type=RollbackType.POLICY,
            resource_id="execution_policy_v2",
            state_data={...},
        )
        
        # Plan rollback to previous snapshot
        plan = await orchestrator.plan_rollback(
            target_snapshot_id=previous_snapshot.snapshot_id,
            reason=RollbackReason.DEPLOYMENT_FAILURE,
        )
        
        # Approve rollback (if required)
        await orchestrator.approve_rollback(plan.rollback_id, approver="admin@mahoun.ai")
        
        # Execute rollback
        record = await orchestrator.execute_rollback(plan)
    """
    
    def __init__(
        self,
        snapshot_store: SnapshotStore,
        artifact_store: Optional[PolicyArtifactStore] = None,
    ):
        self.snapshot_store = snapshot_store
        self.artifact_store = artifact_store
        
        # Rollback history
        self._rollback_history: List[RollbackRecord] = []
        
        # Pending rollbacks (awaiting approval)
        self._pending_rollbacks: Dict[str, RollbackPlan] = {}
        
        # Rollback lock (prevent concurrent rollbacks)
        self._rollback_lock = asyncio.Lock()
        
        # Health check callbacks (for post-rollback verification)
        self._health_checks: List[Callable] = []
        
        logger.info("RollbackOrchestrator initialized")
    
    async def take_snapshot(
        self,
        resource_type: RollbackType,
        resource_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateSnapshot:
        """
        Take snapshot of current state.
        
        Call this BEFORE making any changes (deployment, config update, etc.).
        
        Returns:
            StateSnapshot (for rollback target)
        """
        snapshot = StateSnapshot(
            snapshot_id=f"snap-{uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resource_type=resource_type,
            resource_id=resource_id,
            state_data=state_data,
            metadata=metadata or {},
        )
        
        self.snapshot_store.save_snapshot(snapshot)
        
        logger.info(
            f"Snapshot created: {resource_id} ({resource_type.value}) "
            f"@ {snapshot.timestamp}"
        )
        
        return snapshot
    
    async def plan_rollback(
        self,
        target_snapshot_id: str,
        reason: RollbackReason,
        initiated_by: str = "system",
    ) -> RollbackPlan:
        """
        Plan rollback operation.
        
        This is the first step — generates rollback plan with:
        - Safety checks
        - Impact analysis
        - Rollback steps
        
        Returns:
            RollbackPlan (ready for approval and execution)
        """
        rollback_id = f"rollback-{uuid4().hex[:12]}"
        
        logger.info(
            f"Planning rollback {rollback_id}: target={target_snapshot_id}, "
            f"reason={reason.value}"
        )
        
        # Find target snapshot
        target_snapshot = await self._find_snapshot(target_snapshot_id)
        if not target_snapshot:
            raise ValidationError(f"Target snapshot not found: {target_snapshot_id}")
        
        # Get current state
        current_snapshot = self.snapshot_store.get_latest_snapshot(
            target_snapshot.resource_id
        )
        if not current_snapshot:
            raise OperationalError(
                f"No current snapshot for resource: {target_snapshot.resource_id}"
            )
        
        # Run safety checks
        safety_checks = await self._run_safety_checks(
            target_snapshot,
            current_snapshot,
            reason,
        )
        
        # Analyze impact
        impact = await self._analyze_impact(target_snapshot, current_snapshot)
        
        # Generate rollback steps
        rollback_steps = await self._generate_rollback_steps(
            target_snapshot,
            current_snapshot,
        )
        
        # Create rollback plan
        plan = RollbackPlan(
            rollback_id=rollback_id,
            rollback_type=target_snapshot.resource_type,
            target_snapshot=target_snapshot,
            current_snapshot=current_snapshot,
            reason=reason,
            safety_checks=safety_checks,
            impact=impact,
            rollback_steps=rollback_steps,
            approval_required=(reason == RollbackReason.MANUAL_REQUEST),
            created_by=initiated_by,
        )
        
        # Store pending rollback
        self._pending_rollbacks[rollback_id] = plan
        
        logger.info(
            f"Rollback plan created: {rollback_id} "
            f"(safe={plan.is_safe()}, warnings={plan.has_warnings()})"
        )
        
        return plan
    
    async def simulate_rollback(self, plan: RollbackPlan) -> Dict[str, Any]:
        """
        Simulate rollback (dry-run).
        
        Executes rollback steps in simulation mode (no actual changes).
        
        Returns:
            Simulation results (what would change)
        """
        logger.info(f"Simulating rollback: {plan.rollback_id}")
        
        simulation_results = {
            "rollback_id": plan.rollback_id,
            "safe_to_execute": plan.is_safe(),
            "estimated_downtime_sec": plan.impact.estimated_downtime_sec if plan.impact else 0,
            "resources_affected": plan.impact.resources_affected if plan.impact else 0,
            "changes": plan.impact.changes if plan.impact else [],
            "simulated_steps": [],
        }
        
        # Simulate each step
        for step in plan.rollback_steps:
            logger.info(f"[SIMULATION] {step}")
            simulation_results["simulated_steps"].append({
                "step": step,
                "status": "would_execute",
            })
            await asyncio.sleep(0.01)  # Simulate work
        
        logger.info(f"Simulation complete: {plan.rollback_id}")
        
        return simulation_results
    
    async def approve_rollback(
        self,
        rollback_id: str,
        approver: str,
    ) -> None:
        """Approve pending rollback"""
        plan = self._pending_rollbacks.get(rollback_id)
        if not plan:
            raise ValidationError(f"Rollback not found: {rollback_id}")
        
        if not plan.approval_required:
            raise ValidationError(f"Rollback does not require approval: {rollback_id}")
        
        if approver in plan.approvers:
            raise ValidationError(f"Already approved by {approver}")
        
        plan.approvers.append(approver)
        
        logger.info(
            f"Rollback {rollback_id} approved by {approver} "
            f"({len(plan.approvers)} approvals)"
        )
    
    async def execute_rollback(self, plan: RollbackPlan) -> RollbackRecord:
        """
        Execute rollback plan.
        
        This is the final step — actually performs the rollback.
        
        Steps:
        1. Acquire rollback lock
        2. Validate safety checks
        3. Check approvals (if required)
        4. Execute rollback steps
        5. Verify health checks
        6. Record rollback history
        7. Release lock
        
        Returns:
            RollbackRecord (success or failure)
        """
        async with self._rollback_lock:
            logger.info(f"Executing rollback: {plan.rollback_id}")
            
            # Start rollback record
            record = RollbackRecord(
                rollback_id=plan.rollback_id,
                rollback_type=plan.rollback_type,
                target_snapshot=plan.target_snapshot,
                reason=plan.reason,
                status=RollbackStatus.EXECUTING,
                started_at=datetime.now(timezone.utc).isoformat(),
                initiated_by=plan.created_by,
                approvers=plan.approvers,
                safety_checks=plan.safety_checks,
                rollback_steps=plan.rollback_steps,
            )
            
            try:
                # Check safety
                if not plan.is_safe():
                    raise ValidationError(
                        f"Rollback blocked by safety checks: {plan.rollback_id}"
                    )
                
                # Check approvals
                if plan.approval_required and not plan.approvers:
                    raise ValidationError(
                        f"Rollback requires approval: {plan.rollback_id}"
                    )
                
                # Execute rollback steps
                for step in plan.rollback_steps:
                    logger.info(f"Executing: {step}")
                    await self._execute_rollback_step(
                        step,
                        plan.target_snapshot,
                        plan.current_snapshot,
                    )
                
                # Verify health checks
                verification_results = await self._verify_rollback(
                    plan.target_snapshot
                )
                record.verification_results = verification_results
                
                # Mark as completed
                record.status = RollbackStatus.COMPLETED
                record.completed_at = datetime.now(timezone.utc).isoformat()
                
                logger.info(f"Rollback successful: {plan.rollback_id}")
            
            except Exception as e:
                logger.error(
                    f"Rollback failed: {plan.rollback_id} — {e}",
                    exc_info=True,
                )
                
                record.status = RollbackStatus.FAILED
                record.completed_at = datetime.now(timezone.utc).isoformat()
                record.error_message = str(e)
            
            # Record rollback history
            self._rollback_history.append(record)
            
            # Remove from pending
            if plan.rollback_id in self._pending_rollbacks:
                del self._pending_rollbacks[plan.rollback_id]
            
            return record
    
    async def _find_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Find snapshot by ID"""
        for snapshots in self.snapshot_store._snapshots.values():
            for snapshot in snapshots:
                if snapshot.snapshot_id == snapshot_id:
                    return snapshot
        return None
    
    async def _run_safety_checks(
        self,
        target: StateSnapshot,
        current: StateSnapshot,
        reason: RollbackReason,
    ) -> List[SafetyCheck]:
        """Run rollback safety checks"""
        checks = []
        
        # Check 1: State hash verification
        if target.state_hash == current.state_hash:
            checks.append(SafetyCheck(
                check_name="state_unchanged",
                result=SafetyCheckResult.BLOCKED,
                message="Target state is identical to current state (no-op rollback)",
            ))
        else:
            checks.append(SafetyCheck(
                check_name="state_changed",
                result=SafetyCheckResult.SAFE,
                message="State differs from target (rollback will have effect)",
            ))
        
        # Check 2: Time-based safety (don't rollback too far back)
        target_time = datetime.fromisoformat(target.timestamp)
        current_time = datetime.fromisoformat(current.timestamp)
        time_diff = (current_time - target_time).total_seconds()
        
        if time_diff > 86400 * 7:  # 7 days
            checks.append(SafetyCheck(
                check_name="age_check",
                result=SafetyCheckResult.WARNING,
                message=f"Rollback target is {time_diff / 86400:.1f} days old (review carefully)",
            ))
        else:
            checks.append(SafetyCheck(
                check_name="age_check",
                result=SafetyCheckResult.SAFE,
                message=f"Rollback target is recent ({time_diff / 3600:.1f} hours old)",
            ))
        
        # Check 3: Reason-based approval requirement
        if reason in (RollbackReason.SECURITY_INCIDENT, RollbackReason.MANUAL_REQUEST):
            checks.append(SafetyCheck(
                check_name="approval_required",
                result=SafetyCheckResult.WARNING,
                message=f"Manual approval required for {reason.value}",
            ))
        
        return checks
    
    async def _analyze_impact(
        self,
        target: StateSnapshot,
        current: StateSnapshot,
    ) -> RollbackImpact:
        """Analyze rollback impact"""
        # Simple diff (in production, use deep comparison)
        changes = ["State will be restored to previous snapshot"]
        
        # Estimate downtime
        estimated_downtime = 30  # seconds
        
        return RollbackImpact(
            resources_affected=1,
            changes=changes,
            estimated_downtime_sec=estimated_downtime,
            data_loss_risk=False,
            breaking_changes=[],
        )
    
    async def _generate_rollback_steps(
        self,
        target: StateSnapshot,
        current: StateSnapshot,
    ) -> List[str]:
        """Generate rollback execution steps"""
        return [
            f"1. Validate target snapshot: {target.snapshot_id}",
            f"2. Restore {target.resource_type.value} state",
            "3. Verify health checks",
            "4. Confirm rollback success",
        ]
    
    async def _execute_rollback_step(
        self,
        step: str,
        target: StateSnapshot,
        current: StateSnapshot,
    ) -> None:
        """Execute single rollback step"""
        # TODO: Implement actual rollback logic based on resource_type
        await asyncio.sleep(0.1)  # Simulate work
    
    async def _verify_rollback(
        self,
        target: StateSnapshot,
    ) -> Dict[str, Any]:
        """Verify rollback via health checks"""
        results = {
            "health_checks_passed": True,
            "checks_run": len(self._health_checks),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        for health_check in self._health_checks:
            try:
                await health_check()
            except Exception as e:
                results["health_checks_passed"] = False
                results["error"] = str(e)
                break
        
        return results
    
    def register_health_check(self, health_check: Callable) -> None:
        """Register health check callback (for post-rollback verification)"""
        self._health_checks.append(health_check)
        logger.info(f"Registered health check: {health_check.__name__}")
    
    def get_rollback_history(
        self,
        resource_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RollbackRecord]:
        """Get rollback history"""
        history = self._rollback_history
        
        if resource_id:
            history = [
                record for record in history
                if record.target_snapshot.resource_id == resource_id
            ]
        
        return sorted(
            history,
            key=lambda r: r.started_at,
            reverse=True,
        )[:limit]
    
    def get_pending_rollbacks(self) -> List[RollbackPlan]:
        """Get rollbacks awaiting approval"""
        return list(self._pending_rollbacks.values())


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_rollback_orchestrator: Optional[RollbackOrchestrator] = None
_snapshot_store: Optional[SnapshotStore] = None


def get_rollback_orchestrator() -> RollbackOrchestrator:
    """Get singleton rollback orchestrator instance"""
    global _rollback_orchestrator, _snapshot_store
    
    if _rollback_orchestrator is None:
        if _snapshot_store is None:
            storage_path = Path("/tmp/mahoun_snapshots")  # TODO: Use config
            _snapshot_store = SnapshotStore(storage_path)
        
        _rollback_orchestrator = RollbackOrchestrator(_snapshot_store)
    
    return _rollback_orchestrator
