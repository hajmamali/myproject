# Audit Report — Canonical Governance Certification

تاریخ: 2026-06-26

خلاصه‌ی هدف
- هدف: ارزیابی خصمانه و اثباتی از وجود یک مرز حکمرانی کاننیکال برای دسترسی و تغییرات Neo4j و تولید گزارش PHASES 1–12، با مستندات فایل:خط:تابع برای هر ادعا.

نتیجه‌ی قطعی
- CANONICAL GOVERNANCE CERTIFIED

دلایل خلاصه (دلایل مهم)
- مرز تک کاننیکال برای اجرای Cypher وجود دارد: `Neo4jConnection._raw_execute()` که قبل از تماس با درایور، همیشه `MutationAuthorizationBoundary.inspect(query)` را فراخوانی می‌کند. (شواهد در بخش «شواهد دقیق»)
- مسیر نوشتن (mutation) تنها از طریق `GovernedNeo4jSession` مجاز است که `GovernanceContextManager` را الزامی می‌کند و تنها با تزریق `Neo4jConnection._raw_execute` کار می‌کند.
- تلاش‌های برای دور زدن در مسیر تولیدی وجود ندارد: هر آداپتور خام (`RawSessionRunner`) در حالت production به‌صورت fail-closed عمل می‌کند مگر اینکه صراحتاً `allow_unsafe=True` داده شود (آماده‌سازی برای تست‌ها).
- فراخوانی مستقیمِ `GraphDatabase.driver()` یا `session.run()` در فایل‌های تولیدی (خارج از مرز) یافت نشد — تنها نمونه‌های تولیدی مربوط به خودِ boundary و pool هستند.

PHASE 1 — Remaining Raw Neo4j Usage (production scope)
- بررسی شده: `mahoun/` و `api/` با استثنا کردن دایرکتوری‌های نادیده‌شده (tests, .kilo, .kiro, .cli, worktrees و ...).
- موارد تولیدی حاوی تماس مستقیم به درایور یا session.run (و وضعیت مجاز بودن):
	- `mahoun/graph/neo4j/connection.py` — `GraphDatabase.driver(...)` (canonical init). Allowed (کاننیکال).
	- `mahoun/graph/neo4j/connection.py` — `driver.session(...)` داخل `Neo4jConnection.session()` (کاننیکال، مورد استفاده توسط boundary).
	- `mahoun/graph/neo4j/connection.py` — `s.run(query, ...)` داخل `_raw_execute()` بعد از `MutationAuthorizationBoundary.inspect(query)` (تنها chokepoint اجرایی). Allowed (کاننیکال + بازرسی).
	- `mahoun/graph/neo4j/connection.py` — pool `GraphDatabase.driver(...)` و pool `session()` (کاننیکال).
	- سایر فراخوانی‌های `session.run` / `driver` در repo یا سندها صرفاً مستندسازی یا تست/آداپتورهای fail-closed بوده‌اند.

PHASE 2 — Execution chains (مثال‌ها با مسیر فایل:خط)
- Read path (نمونه: health check)
	- `api/routers/system.py` → `connection = get_connection()` → `connection.execute_query("RETURN 1 AS test")`
	- `get_connection()` → `mahoun/graph/neo4j/connection.py` (factory) → `Neo4jConnection` singleton
	- `Neo4jConnection.execute_query()` → `Neo4jConnection._raw_execute()` → `MutationAuthorizationBoundary.inspect(query)` → `with self.session() as s: s.run(...)`

- Write path (نمونه: `create_node`)
	- `mahoun/graph/neo4j/operations.py` (high-level) obtains `conn = get_connection()` then `with conn.governed_session(...) as session:`
	- `Neo4jConnection.governed_session()` yields `GovernedNeo4jSession(raw_executor=self._raw_execute, ...)`
	- `GovernedNeo4jSession.write_node()` → build Cypher → `_append_governance_audit(...)` → `self._execute_authorized(query, params)`
	- `_execute_authorized()` sets authorization token (`_authorized_write_ctx`) سپس فراخوانی `self._raw_executor(query, params)` (که همان `Neo4jConnection._raw_execute`) و سپس `s.run(...)` اجرا می‌شود.

PHASE 3 — Canonical matrix (counts & canonical locations)
- Driver creation: 2 canonical locations
	- `mahoun/graph/neo4j/connection.py` (constructor) — [connection.py#L150-L156]
	- `mahoun/graph/neo4j/connection.py` (pool init) — [connection.py#L523-L529]
- Session creation: 2 canonical surfaces
	- `mahoun/graph/neo4j/connection.py` — `session()` [connection.py#L195]
	- `mahoun/graph/neo4j/connection.py` — pool `session()` [connection.py#L545]
- Driver execution (`session.run`): canonical chokepoint
	- `mahoun/graph/neo4j/connection.py` — `_raw_execute()` calls `MutationAuthorizationBoundary.inspect()` then `s.run(...)` [connection.py#L216-L225]
	- `mahoun/graph/neo4j/runner.py` — `RawSessionRunner.run()` وجود دارد اما در سازنده در production fail-closed است (test-only) [runner.py#L36-L55].
- Read-path entry: `Neo4jConnection.execute_query()` [connection.py#L228-L252]
- Write-path entry: `Neo4jConnection.governed_session()` [connection.py#L253-L260]
- Factory: `get_connection()` singleton [connection.py#L571-L576]
- Mutation inspection (constitutional gate): `MutationAuthorizationBoundary.inspect()` [mahoun/core/governance/mutation_boundary.py#L315-L327]
- Governed write surface: `GovernedNeo4jSession` [mahoun/core/governance/mutation_boundary.py#L367-L379]
- Kernel classifier: `KernelMutationBoundary.classify_query()` [mahoun/core/governance_kernel/kernel.py#L100-L112]

PHASE 4 — Authorization checks outside kernel
- یافته‌ها (نمونه‌ها):
	- فراخوانی‌های `GovernanceContextManager.require_context()` و `active_context()` در نقاط متعدد تولیدی که نشان‌دهنده‌ی وابستگی به کانتکست حکمرانی است (نمونه‌ها):
		- `mahoun/llm/ultra_engine.py` (استفاده از `require_context()`)
		- `mahoun/core/unified_governance.py` (استفاده از `is_governance_authorized()` از kernel)
		- `mahoun/graph/optimizer/run_optimizer_job.py`، `mahoun/graph/optimizer/*`، `mahoun/graph/builders/*` و بسیاری سرویس‌های سطح بالا `require_context()` را فراخوانی می‌کنند — این‌ها مصرف‌کنندگان صحیحِ مرز حکمرانی‌اند (NOT bypasses).
	- هیچ مکان تولیدی یافت نشد که بدونه استفاده از `get_connection()` یا `governed_session()` عملیات نوشتن انجام دهد.

PHASE 5 — Policy duplication and drift
- نتیجه‌ی اولیه: قوانین اصلی (inspect/classify/gov-session/audit/receipt) تنها در هسته‌ی حکمرانی و boundary پیاده‌سازی شده‌اند؛ نسخه‌های تکراریِ تولیدی یا مسیرهای موازیِ اجرای mutation در فضای تولید یافت نشد.

PHASE 6 — Import-graph verification
- `get_connection()` به‌عنوان factory کاننیکال استفاده می‌شود و در bootstrap wiring و در سرویس‌های تولیدی فراخوانی شده (`mahoun/bootstrap/runtime.py`, Graph operations, GraphQueryService, API layers). این نشان می‌دهد همهٔ سرویس‌های تولیدی از factory واحد استفاده می‌کنند.

PHASE 7 — Hidden dirs & scan hygiene
- اسکریپت‌های اسکن حکومت (`scripts/verify_governance.py`, `ci/scripts/fortress_governance_gate.py`) لیست `IGNORE_DIRS`/`ALLOWED_GOVERNANCE_FILES` را دارند و کار اسکن تولیدی را طوری انجام می‌دهند که worktrees و دایرکتوری‌های پنهان را حذف کنند.

PHASE 8 — Test-only bypasses
- مواردی که صرفاً برای تست/fixtures یا ابزارهای MCP قرار داده شده‌اند و در production بسته‌اند یا fail-closed شده‌اند:
	- `mahoun/graph/neo4j/runner.py::RawSessionRunner` — بخاطر `raise RuntimeError(...)` در سازنده، در production غیرقابل‌استفاده است。

PHASE 9 — Import-graph convergence and anti-drift evidence
- Relevant production governance + Neo4j subgraph observed: 111 modules.
- Import graph analysis found no cycles (`CYCLES []`), which means the governance/Neo4j dependency subgraph is acyclic and deterministically wired.
- All production Neo4j consumers route through the canonical `mahoun.graph.neo4j.connection` factory surface or governance context.
- The bootstrap wiring is explicit: `api/database.py`, `mahoun/bootstrap/runtime.py`, and `mahoun.graph.neo4j.init_schema` all instantiate or consume `get_connection()` rather than direct driver/session factories.

PHASE 10 — Stage II invariant-proof and certification
- Canonical runtime invariant:
        1. All Cypher execution passes through `Neo4jConnection._raw_execute()`.
        2. `_raw_execute()` always calls `MutationAuthorizationBoundary.inspect(query)` before any `session.run()`.
        3. The only production path that can authorize mutations is `Neo4jConnection.governed_session()` yielding `GovernedNeo4jSession`.
        4. `Neo4jConnection.execute_write()` and `execute_batch()` are intentionally fail-closed and raise `GovernanceViolationError`.
- Duplicate-definition analysis confirms the production invariant is anchored in:
        - `mahoun.core.governance.mutation_boundary.py` (canonical `MutationAuthorizationBoundary`, `GovernedNeo4jSession`, `classify_cypher`)
        - `mahoun.core.governance.governance_context.py` (canonical `GovernanceContext`, `GovernanceContextManager`)
        - `mahoun.graph.neo4j.connection.py` (canonical `Neo4jConnection`, `_raw_execute`, `execute_query`, `governed_session`)
- Kernel compatibility duplicates in `mahoun.core.governance_kernel.__init__.py` are legacy interface shims and do not define a separate production mutation boundary.

PHASE 11 — Direct bypass scan proof
- Direct `GraphDatabase.driver(...)` appears only in `mahoun/graph/neo4j/connection.py`.
- `driver.session(...)` appears only in `mahoun/graph/neo4j/connection.py`.
- Raw `session.run(...)` in production appears only in the canonical `connection.py` paths that are protected by `MutationAuthorizationBoundary.inspect()`.
- The `scripts/validate_governance_compliance.py` validator codifies the exact invariant checks and can be used as a CI revalidation gate.

PHASE 12 — Certification conclusion
- CANONICAL GOVERNANCE CERTIFIED for the scanned production surface.
- The formal invariant proof is:
        - The only mutation-authorized execution path is `GovernedNeo4jSession` → `_raw_execute()` → `MutationAuthorizationBoundary.inspect()` → `session.run()`.
        - Any new bypass would require a new direct `Neo4j` entrypoint or removal of the inspect call from `_raw_execute`.
- Recommended hardening:
        - Add CI validation of `scripts/validate_governance_compliance.py`.
        - Preserve `governance_formal_audit.txt` as the duplicate-definition evidence artifact.
