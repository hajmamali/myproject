# 🛡️ MAHOUN Orphan Modules - Hardening & Enforcement Analysis
## Generated: 2026-07-04

---

## ⚡ EXECUTIVE SUMMARY

از 6 ماژول orphan:
- **3 ماژول نیاز به Hardening دارن** (kg_adapters, reasoning_recorder_ultra, policies)
- **3 ماژول Safe هستن** (causal_effects, causal_structure, reranking_cot)

---

## 🔴 CRITICAL: Modules Requiring HARDENING

### 1. **kg_adapters** [P0 - GOVERNANCE-CRITICAL]

**✅ ALREADY HARDENED!** این ماژول از قبل governance-hardened هست!

#### Current Protection:
```python
# ✓ Uses GovernedNeo4jSession (not raw driver)
# ✓ Requires correlation_id + actor_id for ALL queries
# ✓ All operations audited via _append_governance_audit()
# ✓ Validates governance context via GovernanceContextManager.require_context()
```

#### What's Already There:
- ✅ Session factory pattern (no raw driver injection)
- ✅ Mandatory correlation_id/actor_id
- ✅ Audit logging for every operation
- ✅ SecurityBreachException on context mismatch
- ✅ GraphIntegrityException on query failure

#### Additional Hardening NEEDED:
```python
# Add to bootstrap/runtime.py integration:

# HARDENING: Validate session factory returns governed session
def kg_session_factory():
    conn = get_connection()
    session = conn.session()
    
    # ENFORCEMENT: Verify it's a GovernedNeo4jSession
    if not hasattr(session, '_execute_authorized'):
        raise SecurityBreachException(
            message="kg_adapter requires GovernedNeo4jSession",
            correlation_id="bootstrap",
            details={"component": "kg_adapter_init"}
        )
    
    return session
```

#### CI Gate Needed:
```bash
# Add to ci/gates/gate_neo4j_governance.sh:

echo "🔍 Checking kg_adapters governance compliance..."
grep -rn "GraphDatabase.driver" mahoun/reasoning/kg_adapters.py && {
    echo "❌ FATAL: kg_adapters bypasses governance!"
    exit 1
}

grep -rn "session_factory" mahoun/reasoning/kg_adapters.py || {
    echo "❌ FATAL: kg_adapters missing session factory!"
    exit 1
}

echo "✓ kg_adapters governance compliant"
```

---

### 2. **reasoning_recorder_ultra** [P1 - AUDIT-CRITICAL]

**⚠️ NEEDS HARDENING!** Cryptographic audit trail باید governance-protected باشه!

#### Current Risk:
- Recorder می‌تونه بدون governance context راه بیفته
- Hash-chain integrity check نداره runtime validation
- Tamper detection نداره fail-safe mechanism

#### Required Hardening:
```python
# mahoun/reasoning/reasoning_recorder_ultra.py

class UltraReasoningRecorder:
    def __init__(self, backend="file", audit_mode=True, **kwargs):
        # HARDENING: Require governance context in production
        if is_production() and not audit_mode:
            raise SecurityBreachException(
                message="UltraRecorder MUST run in audit_mode in production",
                correlation_id="recorder_init",
                details={"env": os.getenv("MAHOUN_ENV")}
            )
        
        self.backend = backend
        self.audit_mode = audit_mode
        self._hash_chain_verified = False
    
    def record_step(self, step: ReasoningStep, correlation_id: str, actor_id: str):
        """Record reasoning step with governance enforcement"""
        
        # HARDENING: Require governance context
        ctx = GovernanceContextManager.require_context()
        if ctx.correlation_id != correlation_id:
            raise SecurityBreachException(
                message="correlation_id mismatch in recorder",
                correlation_id=correlation_id,
                details={"expected": ctx.correlation_id}
            )
        
        # HARDENING: Verify hash chain before write
        if not self._verify_hash_chain():
            raise GraphIntegrityException(
                message="Hash chain integrity violation detected!",
                correlation_id=correlation_id,
                details={"component": "UltraRecorder"}
            )
        
        # Record with cryptographic proof
        self._write_step(step, correlation_id, actor_id)
        self._update_hash_chain(step)
    
    def _verify_hash_chain(self) -> bool:
        """Verify hash chain integrity"""
        # Implementation: check Merkle tree
        return True  # Placeholder
```

#### Tests Needed:
```python
# tests/reasoning/test_ultra_recorder_hardening.py

def test_ultra_recorder_requires_governance_context():
    """Recorder must fail without governance context"""
    recorder = UltraReasoningRecorder()
    
    with pytest.raises(SecurityBreachException):
        recorder.record_step(step, "corr-123", "actor-1")

def test_ultra_recorder_detects_tampered_chain():
    """Recorder must detect tampered hash chain"""
    recorder = UltraReasoningRecorder()
    
    # Simulate tampered chain
    recorder._tamper_chain()
    
    with pytest.raises(GraphIntegrityException):
        recorder.record_step(step, "corr-123", "actor-1")
```

---

### 3. **policies** [P1 - AUTHORIZATION-CRITICAL]

**⚠️ NEEDS HARDENING!** Policy selection باید RBAC-protected باشه!

#### Current Risk:
- هر کسی می‌تونه policy رو عوض کنه (Conservative → Aggressive)
- تغییر policy audit نمی‌شه
- تغییر policy در runtime نیاز به authorization داره

#### Required Hardening:
```python
# mahoun/reasoning/policies.py

from mahoun.security.rbac import require_permission, Permission

class PolicyManager:
    """Governance-protected policy management"""
    
    @staticmethod
    @require_permission(Permission.MODIFY_REASONING_POLICY)
    def set_policy(
        policy_type: PolicyType,
        actor_id: str,
        correlation_id: str,
        reason: str
    ) -> ReasoningPolicy:
        """
        Set reasoning policy (RBAC-protected)
        
        Requires: MODIFY_REASONING_POLICY permission
        """
        # HARDENING: Audit policy change
        from mahoun.security.audit_logger import AuditLogger
        
        AuditLogger.log_security_event(
            event_type="POLICY_CHANGE",
            actor_id=actor_id,
            correlation_id=correlation_id,
            details={
                "old_policy": "balanced",  # Get from registry
                "new_policy": policy_type.value,
                "reason": reason
            }
        )
        
        # HARDENING: Conservative policy requires senior approval
        if policy_type == PolicyType.AGGRESSIVE:
            if not require_permission(Permission.APPROVE_AGGRESSIVE_POLICY):
                raise SecurityBreachException(
                    message="Aggressive policy requires senior approval",
                    correlation_id=correlation_id,
                    details={"actor_id": actor_id}
                )
        
        policy = get_policy(policy_type)
        return policy
```

#### Tests Needed:
```python
# tests/policy/test_policy_hardening.py

def test_policy_change_requires_permission():
    """Policy change must require RBAC permission"""
    with pytest.raises(PermissionDenied):
        PolicyManager.set_policy(
            PolicyType.AGGRESSIVE,
            actor_id="user-without-permission",
            correlation_id="test-1",
            reason="testing"
        )

def test_aggressive_policy_requires_senior_approval():
    """Aggressive policy requires elevated permission"""
    with pytest.raises(SecurityBreachException):
        PolicyManager.set_policy(
            PolicyType.AGGRESSIVE,
            actor_id="junior-user",
            correlation_id="test-2",
            reason="testing"
        )

def test_policy_change_is_audited():
    """Policy change must be audited"""
    PolicyManager.set_policy(
        PolicyType.CONSERVATIVE,
        actor_id="admin",
        correlation_id="test-3",
        reason="high-stakes case"
    )
    
    # Verify audit log
    audit_entry = AuditLogger.get_latest()
    assert audit_entry["event_type"] == "POLICY_CHANGE"
    assert audit_entry["details"]["new_policy"] == "conservative"
```

---

## 🟢 SAFE: Modules NOT Requiring Hardening

### 4. **causal_effects** [LOW RISK]
- Pure mathematical computation (no DB access)
- Optional feature (fails gracefully)
- No governance bypass risk

### 5. **causal_structure** [LOW RISK]
- Statistical algorithm (PC/NOTEARS)
- No external dependencies
- Returns empty graph on failure

### 6. **reranking_cot** [LOW RISK]
- Pure reasoning generation
- No side effects
- Optional feature

---

## 📋 HARDENING CHECKLIST

### Phase 1: Critical (P0)
- [x] kg_adapters already governance-hardened
- [ ] Add kg_adapter bootstrap validation
- [ ] Add CI gate for kg_adapter compliance

### Phase 2: High Priority (P1)
- [ ] Harden reasoning_recorder_ultra
  - [ ] Require governance context
  - [ ] Add hash chain verification
  - [ ] Add tamper detection
- [ ] Harden policies
  - [ ] Add RBAC protection
  - [ ] Add audit logging
  - [ ] Add senior approval for aggressive mode

### Phase 3: Tests
- [ ] test_kg_adapter_governance_enforcement
- [ ] test_ultra_recorder_hardening (3 tests)
- [ ] test_policy_hardening (3 tests)

---

## 🎯 RECOMMENDATION

**باید این 2 ماژول رو harden کنیم قبل از integration:**
1. **reasoning_recorder_ultra** → Add governance context requirement
2. **policies** → Add RBAC protection

**kg_adapters قبلاً harden شده** - فقط نیاز به CI gate enforcement داره!

**بقیه ماژول‌ها (causal_effects, causal_structure, reranking_cot) safe هستن** و می‌تونیم مستقیم integrate کنیم! ✅
