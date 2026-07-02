# Governance Kernel + PolicyResolver Integration Analysis
**Critical Architecture Integration - Two Governance Layers Working Together**

**Date**: 2026-06-18  
**Status**: 🔍 **ANALYSIS COMPLETE - INTEGRATION STRATEGY DEFINED**

---

## Executive Summary

سیستم MAHOUN در حال حاضر دو لایه governance دارد که باید **یکپارچه** شوند:

### 1️⃣ **Governance Kernel** (موجود)
- **مسئولیت**: امنیت mutation operations
- **محل**: `mahoun/core/governance_kernel/`
- **کارکرد**: جلوگیری از WRITE/DELETE بدون authorization
- **Query Types**: READ, WRITE, DESTRUCTIVE, DDL, FORBIDDEN

### 2️⃣ **PolicyResolver** (جدید - Phase 1 ✅)
- **مسئولیت**: تصمیم‌گیری view mode و resource limits
- **محل**: `mahoun/core/policy_resolver.py`
- **کارکرد**: ACTIVE_VIEW vs HISTORICAL_VIEW، graph depth، semantic search
- **View Modes**: ACTIVE_VIEW, HISTORICAL_VIEW, MIXED_VIEW

---

## Current Architecture - How They Work

### Governance Kernel Flow (موجود)

```python
# محل: mahoun/core/governance_kernel/__init__.py

from mahoun.core.governance_kernel import (
    QueryType,              # READ, WRITE, DESTRUCTIVE
    enforce_governance,     # اجبار governance policy
    classify_query,         # تشخیص نوع query
    MutationAuthorizationBoundary  # مرز امنیتی
)

# Example:
query_type = classify_query("MATCH (n) RETURN n")  # → QueryType.READ
enforce_governance(query_type, correlation_id, actor_id)  # ✅ READ مجاز

query_type = classify_query("CREATE (n:Node)")  # → QueryType.WRITE
enforce_governance(query_type, None, None)  # ❌ GovernanceError: نیاز به correlation_id
```

**قوانین Governance Kernel**:
1. ✅ **READ**: همیشه مجاز (بدون authorization)
2. ⚠️ **WRITE**: نیاز به `correlation_id` و `actor_id`
3. 🔴 **DESTRUCTIVE**: نیاز به authorization + `allow_destructive=True`
4. 🚫 **FORBIDDEN**: هرگز مجاز نیست

---

### PolicyResolver Flow (جدید)

```python
# محل: mahoun/core/policy_resolver.py

from mahoun.core import PolicyResolver, ViewMode

resolver = PolicyResolver(profile_manager)
policy = resolver.resolve_policy(governance_context)

# policy شامل:
# - view_mode: ACTIVE_VIEW / HISTORICAL_VIEW / MIXED_VIEW
# - allow_tombstones: True/False
# - max_graph_depth: 3 (desktop) / 10 (enterprise)
# - semantic_enabled: True/False
# - reasoning_budget: LOW/MEDIUM/HIGH
```

**قوانین PolicyResolver**:
1. ✅ **ACTIVE_VIEW** (default): tombstones فیلتر می‌شوند
2. 🔍 **HISTORICAL_VIEW**: tombstones نشان داده می‌شوند (نیاز به justification)
3. ⚙️ **MIXED_VIEW**: کنترل توسط caller (بالاترین privilege)

---

## Integration Strategy - How They Should Work Together

### 🎯 مسئولیت‌ها (Separation of Concerns)

| Layer | مسئولیت | تصمیم‌گیری |
|-------|---------|-----------|
| **Governance Kernel** | امنیت mutation | آیا این operation مجاز است؟ |
| **PolicyResolver** | تعیین view mode | کدام data قابل رؤیت است؟ |

### ✅ تقسیم کار صحیح:

```python
# ✅ درست: دو لایه مستقل اما هماهنگ

# 1. PolicyResolver: تصمیم می‌گیرد چه چیزی قابل رؤیت است
policy = resolver.resolve_policy(governance_context)

# 2. Governance Kernel: تصمیم می‌گیرد آیا mutation مجاز است
query_type = classify_query(cypher_query)
enforce_governance(query_type, correlation_id, actor_id)

# 3. Query execution با هر دو policy
if policy.allow_tombstones:
    query = base_query  # بدون فیلتر
else:
    query = f"{base_query} AND n._deleted IS NULL"  # با فیلتر

if query_type == QueryType.WRITE:
    # Governed session (Governance Kernel)
    with connection.governed_session(correlation_id, actor_id) as session:
        result = session.run(query, params)
else:
    # Regular execution (PolicyResolver filtering)
    result = connection.execute_query(query, params)
```

---

## Integration Points - Where They Meet

### Integration Point 1: GovernanceContext

**موجود در هر دو**:

```python
# Governance Kernel GovernanceContext
@dataclass
class GovernanceContext:  # در governance_kernel/__init__.py
    correlation_id: str
    actor_id: str
    scope_id: Optional[str] = None
    query_type: Optional[QueryType] = None

# PolicyResolver استفاده می‌کند از:
policy = resolver.resolve_policy(governance_context)
# ✅ استفاده از correlation_id و actor_id برای audit trail
```

**✅ Compatible**: PolicyResolver از همان GovernanceContext استفاده می‌کند!

---

### Integration Point 2: Query Execution Flow

```python
# محل ادغام: mahoun/graph/graph_query_service.py

class GraphQueryService:
    def execute_query(self, query: str, params: Dict, policy: ExecutionPolicy):
        """
        Integrated execution with both layers:
        1. Governance Kernel: authorization
        2. PolicyResolver: view filtering
        """
        
        # Step 1: Classify query (Governance Kernel)
        query_type = classify_query(query)
        
        # Step 2: Enforce governance (Governance Kernel)
        enforce_governance(
            query_type,
            policy.correlation_id,  # از PolicyResolver
            policy.actor_id,        # از PolicyResolver
        )
        
        # Step 3: Apply view mode filtering (PolicyResolver)
        if not policy.allow_tombstones and query_type == QueryType.READ:
            query = inject_tombstone_filter(query)
        
        # Step 4: Apply depth limits (PolicyResolver)
        if policy.max_graph_depth:
            query = limit_traversal_depth(query, policy.max_graph_depth)
        
        # Step 5: Execute with appropriate method
        if query_type == QueryType.WRITE:
            # Governed session (Governance Kernel)
            with connection.governed_session(
                correlation_id=policy.correlation_id,
                actor_id=policy.actor_id
            ) as session:
                return session.run(query, params)
        else:
            # Regular execution (PolicyResolver governs filtering)
            return connection.execute_query(query, params)
```

---

### Integration Point 3: Audit Trail

**دو لایه audit** که باید یکپارچه شوند:

| Layer | Audit Target | Data Logged |
|-------|--------------|-------------|
| **Governance Kernel** | Mutation operations | correlation_id, actor_id, query_type, authorization result |
| **PolicyResolver** | Policy decisions | policy_id, view_mode, justification, resolved_at |

**ادغام در audit trail**:

```python
# هر دو در یک audit entry
audit_entry = {
    # از Governance Kernel
    "correlation_id": governance_context.correlation_id,
    "actor_id": governance_context.actor_id,
    "query_type": query_type.value,
    "authorization_result": "granted",
    
    # از PolicyResolver
    "policy_id": policy.policy_id,
    "view_mode": policy.view_mode.value,
    "allow_tombstones": policy.allow_tombstones,
    "max_graph_depth": policy.max_graph_depth,
    "justification": policy.justification,
    
    # مشترک
    "timestamp": datetime.now(UTC).isoformat(),
    "execution_result": "success"
}
```

---

## Implementation Recommendations

### ✅ Best Practice Integration Pattern

```python
# محل پیشنهادی: mahoun/core/unified_governance.py

from mahoun.core.governance_kernel import (
    QueryType,
    enforce_governance,
    classify_query,
    GovernanceContext as KernelContext
)
from mahoun.core.policy_resolver import (
    PolicyResolver,
    ExecutionPolicy,
    ViewMode
)

class UnifiedGovernanceController:
    """
    Unified controller coordinating both governance layers.
    
    Architecture:
    - Governance Kernel: Mutation authorization
    - PolicyResolver: View mode & resource limits
    
    This controller ensures:
    1. Mutations go through Governance Kernel
    2. View filtering comes from PolicyResolver
    3. Audit trail captures both layers
    """
    
    def __init__(self, policy_resolver: PolicyResolver):
        self.policy_resolver = policy_resolver
    
    def prepare_query_execution(
        self,
        query: str,
        governance_context: KernelContext
    ) -> tuple[str, ExecutionPolicy, QueryType]:
        """
        Unified preparation for query execution.
        
        Returns:
            (modified_query, policy, query_type)
        """
        # Step 1: Resolve execution policy (PolicyResolver)
        policy = self.policy_resolver.resolve_policy(governance_context)
        
        # Step 2: Classify query (Governance Kernel)
        query_type = classify_query(query)
        
        # Step 3: Enforce governance (Governance Kernel)
        enforce_governance(
            query_type,
            governance_context.correlation_id,
            governance_context.actor_id
        )
        
        # Step 4: Apply policy transformations (PolicyResolver)
        modified_query = query
        
        if query_type == QueryType.READ:
            # Apply tombstone filtering
            if not policy.allow_tombstones:
                modified_query = self._inject_tombstone_filter(modified_query)
            
            # Apply depth limits
            if policy.max_graph_depth:
                modified_query = self._limit_depth(
                    modified_query,
                    policy.max_graph_depth
                )
        
        return modified_query, policy, query_type
    
    def _inject_tombstone_filter(self, query: str) -> str:
        """Inject WHERE n._deleted IS NULL"""
        # Simplified - production needs proper Cypher AST manipulation
        if "WHERE" in query.upper():
            return query.replace("WHERE", "WHERE n._deleted IS NULL AND")
        else:
            return f"{query} WHERE n._deleted IS NULL"
    
    def _limit_depth(self, query: str, max_depth: int) -> str:
        """Limit graph traversal depth"""
        # Simplified - production needs proper pattern matching
        import re
        pattern = r'\[.*?\*(\d+)\.\.(\d+)\]'
        def replacer(match):
            start, end = match.groups()
            limited_end = min(int(end), max_depth)
            return f'[*{start}..{limited_end}]'
        return re.sub(pattern, replacer, query)
```

---

## Current Status vs Required Status

### ✅ What Works Today

1. **Governance Kernel** ✅
   - Mutation authorization کار می‌کند
   - GovernedNeo4jSession از correlation_id استفاده می‌کند
   - MutationAuthorizationBoundary mutations را بررسی می‌کند

2. **PolicyResolver** ✅
   - Policy resolution کار می‌کند
   - ViewMode تعریف شده
   - Audit trail موجود است

### ❌ What's Missing

1. **Integration Layer** ❌
   - هیچ UnifiedGovernanceController وجود ندارد
   - Query services از PolicyResolver استفاده نمی‌کنند
   - Tombstone filtering خودکار نیست

2. **Unified Audit Trail** ❌
   - دو audit trail جداگانه
   - correlation بین Governance Kernel و PolicyResolver وجود ندارد

---

## Recommended Next Steps

### Phase 1.5: Governance Integration (2-3 days)

1. **Create UnifiedGovernanceController** ✅
   - یکپارچه‌سازی Governance Kernel + PolicyResolver
   - Unified audit trail
   - Tests for integration

2. **Update Graph Query Services** 🔜
   - `graph_query_service.py` استفاده از UnifiedGovernanceController
   - Automatic tombstone filtering
   - Automatic depth limiting

3. **Integration Tests** 🔜
   - Test both layers working together
   - Test audit trail completeness
   - Test security enforcement

---

## Conclusion

**Governance Kernel** و **PolicyResolver** دو لایه مکمل هستند:

| Layer | Focus | When Applied |
|-------|-------|--------------|
| **Governance Kernel** | 🔒 امنیت mutation | قبل از WRITE/DELETE |
| **PolicyResolver** | 👁️ view mode | قبل از READ |

**استراتژی ادغام**:
- ✅ هر دو مستقل باقی بمانند (separation of concerns)
- ✅ UnifiedGovernanceController آنها را هماهنگ کند
- ✅ Audit trail هر دو را capture کند
- ✅ Query services از هر دو استفاده کنند

**وضعیت**: PolicyResolver ساخته شد، حالا نیاز به integration layer داریم! 🚀

---

**Report Generated**: 2026-06-18  
**Phase**: 1.5 - Governance Integration Analysis  
**Status**: Analysis Complete - Ready for Implementation  
**Next**: Build UnifiedGovernanceController
