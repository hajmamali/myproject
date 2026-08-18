# FORTRESS DEVELOPER GUIDE
## MAHOUN Reasoning Layer Security - Technical Reference

**Version**: 1.0.0  
**Last Updated**: May 13, 2026  
**Status**: Production Ready  
**Security Level**: FORTRESS  

---

## QUICK START

### Installation
```bash
# Install cryptography library (required for fortress mode)
pip install cryptography

# Set environment for production
export MAHOUN_ENV=production

# Verify fortress initialization
python -c "from mahoun.reasoning.reasoning_layer_fortress import get_reasoning_fortress; print(get_reasoning_fortress().get_fortress_status())"
```

### Basic Usage
```python
from mahoun.reasoning import UnifiedReasoningService, ReasoningRequest, ReasoningTask

# Initialize fortress-protected reasoning service
service = UnifiedReasoningService(enable_neural=True)

# Create reasoning request
request = ReasoningRequest(
    task=ReasoningTask.QUESTION_ANSWERING,
    facts=["Contract was signed on January 1, 2024"],
    rules=["If contract is signed, it is binding"],
    question="Is the contract binding?"
)

# Execute fortress-protected reasoning
response = await service.reason(request)

print(f"Success: {response.success}")
print(f"Confidence: {response.confidence}")
print(f"Fortress Protected: {response.metadata.get('fortress_protected')}")
```

---

## ARCHITECTURE OVERVIEW

### Security Layers

```
┌─────────────────────────────────────────────┐
│         APPLICATION LAYER                    │
│  (Your code using UnifiedReasoningService)   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      🏰 FORTRESS PROTECTION LAYER 🏰        │
│  • Cryptographic signatures (4096-bit RSA)   │
│  • Access control (time-limited tokens)      │
│  • Integrity monitoring (continuous)         │
│  • Audit logging (forensic-grade)            │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      🛡️ NEURAL VALIDATION LAYER 🛡️         │
│  • Symbolic cross-validation (3 methods)     │
│  • Automatic rejection (unverified outputs)  │
│  • Performance caching (SHA-256 keys)        │
│  • Metrics tracking (comprehensive)          │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      🔐 GUARDRAILS ENFORCEMENT 🔐           │
│  • Hardened import (fail-fast)               │
│  • Runtime invariants (non-bypassable)       │
│  • Environment detection (multi-layer)       │
│  • Degraded mode guards (loud no-ops)        │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      REASONING ENGINES (PROTECTED)           │
│  • Symbolic (FOL, Rete, Unification)         │
│  • Neural (LLM, CoT, Causal)                 │
│  • Hybrid (Combined approach)                │
└──────────────────────────────────────────────┘
```

---

## COMPONENT REFERENCE

### 1. Reasoning Layer Fortress

**File**: `mahoun/reasoning/reasoning_layer_fortress.py`

#### Key Classes

##### `ReasoningLayerFortress`
Main fortress protection system.

```python
from mahoun.reasoning.reasoning_layer_fortress import get_reasoning_fortress

# Get global fortress instance
fortress = get_reasoning_fortress()

# Check fortress status
status = fortress.get_fortress_status()
print(f"Security Level: {status['security_level']}")
print(f"Protected Components: {status['protected_components']}")
print(f"Integrity Checks: {status['integrity_checks']}")

# Grant access token for operations
token = fortress.grant_access_token()

# Revoke access token
fortress.revoke_access_token()
```

#### Decorators

##### `@fortress_protect`
Protect a function with fortress security.

```python
from mahoun.reasoning.reasoning_layer_fortress import fortress_protect

@fortress_protect("my_reasoning_function", critical=True)
def my_reasoning_function(x: int) -> int:
    """This function is now fortress-protected"""
    return x * 2

# Function is automatically protected
result = my_reasoning_function(5)  # Fortress checks applied
```

#### Context Managers

##### `fortress_access()`
Temporary access token for fortress operations.

```python
from mahoun.reasoning.reasoning_layer_fortress import fortress_access

with fortress_access():
    # Perform fortress-protected operations
    result = protected_function()
    # Token automatically revoked on exit
```

---

### 2. Neural Validation Layer

**File**: `mahoun/reasoning/neural_validation.py`

#### Key Classes

##### `NeuralOutputValidator`
Validates neural outputs with symbolic reasoning.

```python
from mahoun.reasoning.neural_validation import get_neural_validator

# Get global validator instance
validator = get_neural_validator()

# Validate neural output
validation_result = validator.validate_neural_conclusion(
    neural_output="The defendant is liable for breach of contract.",
    evidence_context=[
        "Contract was signed",
        "Defendant failed to deliver",
        "Plaintiff suffered damages"
    ],
    question_context="Is the defendant liable?"
)

print(f"Valid: {validation_result.valid}")
print(f"Confidence: {validation_result.confidence}")
print(f"Method: {validation_result.validation_method}")
print(f"Proof Chain: {validation_result.proof_chain}")
```

#### Convenience Functions

##### `validate_neural_output()`
Quick validation interface.

```python
from mahoun.reasoning.neural_validation import validate_neural_output

result = validate_neural_output(
    neural_output="Legal conclusion here",
    evidence_context=["fact1", "fact2"],
    question_context="Question?"
)
```

#### Configuration

```python
# Update confidence threshold
validator.update_confidence_threshold(0.9)  # Stricter validation

# Clear validation cache
validator.clear_cache()

# Get validation metrics
metrics = validator.get_validation_metrics()
print(f"Success Rate: {metrics['success_rate']}")
print(f"Rejection Rate: {metrics['rejection_rate']}")
print(f"Cache Hit Rate: {metrics['cache_hit_rate']}")
```

---

### 3. Hardened Guardrails Import

**File**: `mahoun/guardrails/hardened_import.py`

#### Key Functions

##### `import_guardrails_with_enforcement()`
Import guardrails with fail-fast enforcement.

```python
from mahoun.guardrails.hardened_import import import_guardrails_with_enforcement

# Import with enforcement
result = import_guardrails_with_enforcement()

print(f"Status: {result.status.value}")
print(f"Environment: {result.environment.value}")
print(f"Operational: {result.is_operational()}")
print(f"Security Level: {result.get_security_level()}")
```

#### Environment Configuration

```bash
# Production (fail-fast on import failure)
export MAHOUN_ENV=production

# Staging (degraded mode with warnings)
export MAHOUN_ENV=staging

# Development (explicit acknowledgment required)
export MAHOUN_ENV=development
export MAHOUN_ACKNOWLEDGE_DEGRADED_GUARDS=true  # If guardrails unavailable

# Testing (monitoring mode)
export MAHOUN_ENV=test
```

---

## SECURITY BEST PRACTICES

### 1. Always Use Fortress Access

❌ **BAD**:
```python
# Direct access without fortress protection
result = reasoning_function()
```

✅ **GOOD**:
```python
# Use fortress access context
with fortress_access():
    result = reasoning_function()
```

### 2. Never Bypass Neural Validation

❌ **BAD**:
```python
# Attempting to bypass validation (will be logged and blocked)
result = validator.validate_neural_conclusion(
    neural_output=output,
    evidence_context=evidence,
    bypass_validation=True  # IGNORED - logged as security violation
)
```

✅ **GOOD**:
```python
# Proper validation
result = validate_neural_output(
    neural_output=output,
    evidence_context=evidence
)
```

### 3. Handle Validation Failures Properly

❌ **BAD**:
```python
try:
    result = validate_neural_output(output, evidence)
except InvariantViolation:
    # Silently ignore and use unvalidated output
    return output  # DANGEROUS!
```

✅ **GOOD**:
```python
try:
    result = validate_neural_output(output, evidence)
    return result
except InvariantViolation as e:
    # Log failure and return error
    logger.error(f"Neural validation failed: {e}")
    raise  # Propagate error - don't use unvalidated output
```

### 4. Monitor Fortress Status

```python
# Regular fortress health checks
fortress = get_reasoning_fortress()

if fortress.is_compromised:
    logger.critical("FORTRESS COMPROMISED - SYSTEM SHUTDOWN REQUIRED")
    # Trigger emergency procedures
    
status = fortress.get_fortress_status()
if status['integrity_failures'] > 0:
    logger.warning(f"Integrity failures detected: {status['integrity_failures']}")
```

---

## DEBUGGING & TROUBLESHOOTING

### Common Issues

#### Issue 1: "Fortress is compromised"

**Symptom**: `SecurityError: Fortress is compromised - reasoning operations blocked`

**Cause**: Integrity check failed or security violation detected

**Solution**:
```python
# Check fortress status
fortress = get_reasoning_fortress()
status = fortress.get_fortress_status()
print(f"Compromised: {status['is_compromised']}")
print(f"Integrity Failures: {status['integrity_failures']}")

# Check audit trail for details
audit_trail = fortress.export_audit_trail()
for event in audit_trail[-10:]:  # Last 10 events
    if event['event_type'] == 'fortress_lockdown':
        print(f"Lockdown Reason: {event['details']['reason']}")
```

#### Issue 2: "Neural output rejected"

**Symptom**: `InvariantViolation: neural_output_validation_failed`

**Cause**: Neural output failed symbolic cross-validation

**Solution**:
```python
# Check validation details
try:
    result = validate_neural_output(output, evidence)
except InvariantViolation as e:
    print(f"Rejection Reason: {e.details['rejection_reason']}")
    print(f"Validation Method: {e.details['validation_method']}")
    print(f"Confidence: {e.details['confidence']}")
    
    # Options:
    # 1. Improve evidence context
    # 2. Refine neural output
    # 3. Lower confidence threshold (carefully!)
```

#### Issue 3: "Guardrails import failed"

**Symptom**: `SystemExit: FATAL: Guardrails unavailable in PRODUCTION mode`

**Cause**: Guardrails module cannot be imported in production

**Solution**:
```bash
# Check environment
echo $MAHOUN_ENV

# Verify guardrails module exists
python -c "from mahoun.guardrails import runtime_invariants"

# Check dependencies
pip list | grep mahoun

# Reinstall if needed
pip install -e .
```

---

## PERFORMANCE TUNING

### 1. Validation Caching

```python
# Increase cache size for better hit rate
validator = get_neural_validator()
validator.validation_cache_size = 5000  # Default: 1000

# Monitor cache performance
metrics = validator.get_validation_metrics()
print(f"Cache Hit Rate: {metrics['cache_hit_rate']:.2%}")

# Clear cache if needed (e.g., after threshold change)
validator.clear_cache()
```

### 2. Confidence Threshold Tuning

```python
# Lower threshold for faster validation (less strict)
validator.update_confidence_threshold(0.7)  # Default: 0.8

# Higher threshold for stricter validation (slower)
validator.update_confidence_threshold(0.9)

# Monitor rejection rate
metrics = validator.get_validation_metrics()
print(f"Rejection Rate: {metrics['rejection_rate']:.2%}")
```

### 3. Fortress Monitoring Interval

```python
# Adjust monitoring interval (default: 60 seconds)
fortress = get_reasoning_fortress()
fortress._shutdown_event.wait(120)  # Check every 2 minutes instead
```

---

## TESTING

### Unit Tests

```python
import pytest
from mahoun.reasoning import UnifiedReasoningService, ReasoningRequest

@pytest.mark.asyncio
async def test_fortress_protected_reasoning():
    """Test fortress-protected reasoning"""
    service = UnifiedReasoningService()
    
    request = ReasoningRequest(
        task=ReasoningTask.FORWARD_INFERENCE,
        facts=["A", "A -> B"],
        rules=[]
    )
    
    response = await service.reason(request)
    
    assert response.success
    assert response.metadata['fortress_protected'] == True
    assert response.metadata['integrity_verified'] == True
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_neural_validation_enforcement():
    """Test that neural outputs are validated"""
    service = UnifiedReasoningService(enable_neural=True)
    
    request = ReasoningRequest(
        task=ReasoningTask.QUESTION_ANSWERING,
        facts=["Contract signed"],
        rules=[],
        question="Is contract valid?"
    )
    
    response = await service.reason(request)
    
    # Check validation metadata
    assert 'symbolic_validation' in response.result
    assert response.result['symbolic_validation']['validated'] == True
    assert response.result['zero_hallucination_guarantee'] == True
```

### Security Tests

```python
def test_bypass_attempt_detection():
    """Test that bypass attempts are detected and logged"""
    validator = get_neural_validator()
    
    # Attempt bypass (should be logged)
    result = validator.validate_neural_conclusion(
        neural_output="Test output",
        evidence_context=["Evidence"],
        bypass_validation=True  # Bypass attempt
    )
    
    # Check metrics
    metrics = validator.get_validation_metrics()
    assert metrics['bypass_attempts'] > 0
```

---

## MONITORING & ALERTS

### Key Metrics to Monitor

```python
# Fortress Status
fortress = get_reasoning_fortress()
status = fortress.get_fortress_status()

metrics_to_monitor = {
    'is_compromised': status['is_compromised'],  # Alert if True
    'integrity_failures': status['integrity_failures'],  # Alert if > 0
    'protected_components': status['protected_components'],  # Should be stable
    'active_tokens': status['active_tokens'],  # Monitor for leaks
}

# Neural Validation Metrics
validator = get_neural_validator()
validation_metrics = validator.get_validation_metrics()

validation_to_monitor = {
    'rejection_rate': validation_metrics['rejection_rate'],  # Alert if > 50%
    'bypass_attempts': validation_metrics['bypass_attempts'],  # Alert if > 0
    'hallucination_detections': validation_metrics['hallucination_detections'],  # Track trend
    'cache_hit_rate': validation_metrics['cache_hit_rate'],  # Optimize if < 20%
}
```

### Alerting Rules

```python
# Example alerting logic
def check_security_alerts():
    fortress = get_reasoning_fortress()
    validator = get_neural_validator()
    
    # Critical alerts
    if fortress.is_compromised:
        send_alert("CRITICAL: Fortress compromised!", severity="P0")
    
    if fortress.get_fortress_status()['integrity_failures'] > 0:
        send_alert("CRITICAL: Integrity failures detected!", severity="P0")
    
    # Warning alerts
    metrics = validator.get_validation_metrics()
    if metrics['bypass_attempts'] > 0:
        send_alert(f"WARNING: {metrics['bypass_attempts']} bypass attempts detected", severity="P1")
    
    if metrics['rejection_rate'] > 0.5:
        send_alert(f"WARNING: High rejection rate: {metrics['rejection_rate']:.2%}", severity="P2")
```

---

## SUPPORT & RESOURCES

### Documentation
- **Phase 0**: `PHASE_0_INTEGRITY_GAP_REGISTER.md` - Gap analysis
- **Phase 1**: `PHASE_1_TECHNICAL_REMEDIATION_PLAN.md` - Implementation plan
- **Complete**: `PHASE_1_IMPLEMENTATION_COMPLETE.md` - Full technical details
- **Executive**: `EXECUTIVE_SUMMARY_PHASE_1.md` - Business summary

### Code References
- **Fortress**: `mahoun/reasoning/reasoning_layer_fortress.py`
- **Validation**: `mahoun/reasoning/neural_validation.py`
- **Import**: `mahoun/guardrails/hardened_import.py`
- **Integration**: `mahoun/reasoning/unified_reasoning_service.py`

### Contact
- **Security Issues**: security@mahoun.ai
- **Technical Support**: support@mahoun.ai
- **Principal Engineer**: kiro@mahoun.ai

---

**Last Updated**: May 13, 2026  
**Version**: 1.0.0  
**Status**: Production Ready  
**Classification**: INTERNAL - DEVELOPER GUIDE