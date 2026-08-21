# 🔍 Audit: موجودی زیرساخت Monitoring

**تاریخ:** 2026-08-19  
**وضعیت:** Infrastructure Assessment برای MVP Monitoring  

---

## 📊 خلاصه اجرایی

**خبر خوب:** حدود **70-80%** از backend monitoring زیرساخت آماده است!  
**چالش:** API exposure و Frontend integration نیاز به کار دارد.

---

## ✅ بخش 1: چی الان PRODUCTION-READY هست

### 1.1 Graph Health Monitoring ✅ (90% آماده)

#### Backend موجود:
```python
# mahoun/graph/validation/ultra_integrity_validator.py
class UltraIntegrityValidator:
    ✓ get_health_score() -> float              # خط 371
    ✓ check_orphaned_nodes() -> Dict           # خط 130
    ✓ check_circular_references() -> Dict      # خط 156
    ✓ check_hash_chain_integrity() -> Dict     # خط 186
    ✓ check_temporal_consistency() -> Dict     # خط 227
    ✓ detect_graph_anomalies() -> Dict         # خط 254
    ✓ validate_all() -> Dict                   # خط 283 (comprehensive)
```

**وضعیت:** ✅ Backend کامل، فقط needs API wrapper

---

### 1.2 Model Performance Tracking ✅ (95% آماده)

#### Backend موجود:
```python
# mahoun/llm/advanced_model_orchestrator.py  
class AdvancedModelOrchestrator:
    ✓ get_model_metrics(model_id) -> Dict     # خط 478
    ✓ get_system_status() -> Dict              # monitoring وضعیت کلی
    ✓ ModelMetrics dataclass                   # complete metrics structure
      - total_requests, successful/failed
      - error_rate, avg/p95/p99 latency
      - latency_history (deque 1000)
      - first/last request timestamps
    
    ✓ A/B Testing Infrastructure:              # خطوط 270-354
      - start_ab_test()
      - get_ab_test_model()
      - evaluate_ab_test()
    
    ✓ Canary Deployment:                       # خطوط 356-433
      - start_canary_deployment()
      - check_canary_health()
      - promote_canary()
```

**وضعیت:** ✅ Backend کامل با A/B و Canary support!

---

### 1.3 API Endpoints ⚠️ (50% آماده)

#### موجود - Generic Metrics:
```python
# api/routers/metrics.py - خط 22
✓ GET  /metrics               # all metrics
✓ GET  /metrics/summary       # summary stats  
✓ GET  /metrics/{name}        # specific metric
✓ GET  /metrics/agents/summary # agent metrics
✓ POST /metrics/reset         # reset metrics
```

#### موجود - Health Checks:
```python
# api/routers/health_v2.py - خط 19
✓ GET /health/v2                    # basic health
✓ GET /health/v2/detailed           # comprehensive  
✓ GET /health/v2/component/{name}   # component-specific
```

#### ❌ ناموجود - Monitoring-Specific Endpoints:
```
✗ GET /api/v1/monitoring/graph/health
✗ GET /api/v1/monitoring/graph/violations
✗ GET /api/v1/monitoring/models/performance
✗ GET /api/v1/monitoring/models/leaderboard
✗ POST /api/v1/maintenance/cleanup-orphans
✗ WS /api/v1/monitoring/stream
```

---

### 1.4 Legal-Specific Monitoring ✅ (100% آماده!)

```python
# mahoun/monitoring/legal_metrics.py
class UltraProfessionalLegalMonitoring:
    ✓ track_legal_query()                      # خط 356
    ✓ get_stats() -> Dict                      # خط 605
    ✓ get_comprehensive_stats() -> Dict        # خط 830
    ✓ export_prometheus_metrics() -> str       # خط 882
    ✓ health_check() -> Dict                   # خط 900
    ✓ SLA tracking & compliance
    ✓ Alert system با callback
```

**استفاده فعلی:**
```python
# api/main.py - خط 659-663
✓ Metrics router registered at /metrics
```

---

## 🚧 بخش 2: چی ساخته شده ولی NOT WIRED

### 2.1 Monitoring Infrastructure Built but Unused

```python
# mahoun/infrastructure/health_checker.py
✓ HealthChecker class - comprehensive checks
✓ Component health verification
✓ Circuit breaker integration

# mahoun/infrastructure/health/checker.py  
✓ Alternative health checker implementation

# mahoun/ai/health.py
✓ AIRuntimeHealthChecker - خط 99
✓ HealthStatus enum
✓ HealthCheckResult dataclass
✓ Comprehensive AI runtime checks
```

**مشکل:** این classes ساخته شدن ولی **از API استفاده نمیشن**!

---

### 2.2 Dashboard Infrastructure Exists!

```python
# mahoun/dashboard/router.py - خط 48
✓ Dashboard HTML template موجود
✓ GET /api/health endpoint - خط 103
✓ Health system integration
```

**مشکل:** این یک dashboard جداگونه است، نیاز به یکپارچه‌سازی با monitoring guide

---

## ❌ بخش 3: چی کاملاً ناموجود است

### 3.1 Real-time Updates
```
✗ WebSocket support
✗ Server-Sent Events (SSE)
✗ Live metrics streaming
```

### 3.2 Auto-Cleanup Endpoints
```
✗ POST /maintenance/cleanup-orphans
✗ Automated orphan detection & removal API
✗ Dry-run support
✗ Review interface for risky orphans
```

### 3.3 Training Readiness Indicator
```
✗ Training readiness calculation
✗ Data coverage assessment  
✗ Label quality scoring
✗ Diversity metrics
```

### 3.4 Model Comparison/Leaderboard
```
✗ GET /models/leaderboard
✗ GET /models/compare?ids=...
✗ Ranking algorithm
✗ Weighted scoring system
```

---

## 🎯 بخش 4: کارهای مورد نیاز برای MVP

### Priority 1: Wire Existing Components (1 week)

```python
# api/routers/monitoring.py (NEW FILE)
from mahoun.graph.validation.ultra_integrity_validator import UltraIntegrityValidator
from mahoun.llm.advanced_model_orchestrator import AdvancedModelOrchestrator

@router.get("/monitoring/graph/health")
async def get_graph_health(request: Request):
    """Expose UltraIntegrityValidator.get_health_score()"""
    validator = request.app.state.integrity_validator  # از bootstrap
    return {"health_score": validator.get_health_score()}

@router.get("/monitoring/graph/violations")
async def get_violations(request: Request):
    """Expose UltraIntegrityValidator.violations"""
    validator = request.app.state.integrity_validator
    return {"violations": validator.violations}

@router.get("/monitoring/models/performance")
async def get_model_performance(request: Request):
    """Expose AdvancedModelOrchestrator.get_model_metrics()"""
    orchestrator = request.app.state.model_orchestrator  # از bootstrap
    return orchestrator.get_model_metrics()

@router.get("/monitoring/models/leaderboard")
async def get_model_leaderboard(request: Request):
    """Sort models by composite score"""
    orchestrator = request.app.state.model_orchestrator
    metrics = orchestrator.get_model_metrics()
    
    # Calculate scores
    leaderboard = []
    for model_id, data in metrics.items():
        if 'error' in data:
            continue
        score = calculate_score(data)  # weighted formula
        leaderboard.append({
            'model_id': model_id,
            'score': score,
            **data
        })
    
    return sorted(leaderboard, key=lambda x: x['score'], reverse=True)
```

**زمان تخمینی:** 3-4 روز

---

### Priority 2: Auto-Cleanup API (3 days)

```python
@router.post("/maintenance/cleanup-orphans")
async def cleanup_orphans(
    request: Request,
    mode: str = "safe",  # safe | aggressive | manual-review
    dry_run: bool = True
):
    """
    Cleanup orphaned nodes
    
    Mode:
      - safe: Only nodes با zero connections
      - aggressive: Include low-importance orphans
      - manual-review: Return list for human approval
    """
    validator = request.app.state.integrity_validator
    
    # Run validation first
    validator.check_orphaned_nodes()
    orphans = [v for v in validator.violations if v.violation_type == 'orphaned_node']
    
    if mode == "manual-review":
        return {"orphans": orphans, "action": "review_required"}
    
    # Safe cleanup logic
    safe_orphans = filter_safe_orphans(orphans)
    
    if dry_run:
        return {"would_delete": len(safe_orphans), "orphans": safe_orphans}
    
    # Actually delete
    deleted = delete_orphaned_nodes(safe_orphans)
    return {"deleted_count": deleted}
```

**زمان تخمینی:** 2-3 روز

---

### Priority 3: Frontend Integration (1 week)

```typescript
// frontend/src/pages/MonitoringDashboard.tsx
import { useQuery } from 'react-query';

const MonitoringDashboard = () => {
  const { data: graphHealth } = useQuery('graph-health', 
    () => fetch('/api/v1/monitoring/graph/health').then(r => r.json()),
    { refetchInterval: 5000 }  // هر 5 ثانیه
  );
  
  const { data: modelPerf } = useQuery('model-performance',
    () => fetch('/api/v1/monitoring/models/performance').then(r => r.json()),
    { refetchInterval: 10000 }
  );
  
  return (
    <div>
      <GaugeChart value={graphHealth?.health_score} />
      <ModelLeaderboard models={modelPerf} />
    </div>
  );
};
```

**زمان تخمینی:** 5-7 روز

---

## 📈 تخمین زمانی کل MVP

| Task | Status | Time | Priority |
|------|--------|------|----------|
| Wire existing monitoring endpoints | 🔴 Not started | 3-4 days | P0 |
| Auto-cleanup API | 🔴 Not started | 2-3 days | P0 |
| Model leaderboard logic | 🔴 Not started | 1-2 days | P1 |
| Frontend basic dashboard | 🔴 Not started | 5-7 days | P0 |
| **Total** | | **11-16 days** | |

---

## 🎉 نتیجه‌گیری

### چی داریم:
✅ UltraIntegrityValidator (full-featured)  
✅ AdvancedModelOrchestrator (با A/B و Canary!)  
✅ Generic /metrics endpoints  
✅ Health check endpoints  
✅ Legal-specific monitoring  

### چی نداریم:
❌ Monitoring-specific API wrappers  
❌ Auto-cleanup endpoints  
❌ Real-time WebSocket  
❌ Frontend dashboard  

### خبر خوب:
**Backend logic 80% آماده است!** فقط باید:
1. API wrappers بنویسیم (3-4 روز)
2. Auto-cleanup endpoint (2-3 روز)
3. Frontend dashboard (5-7 روز)

**Total MVP: 2-3 هفته instead of 6-8 هفته!** 🚀

---

**توصیه نهایی:**  
Start با wiring existing components. این سریع‌ترین راه برای دیدن نتیجه است!
