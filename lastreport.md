# گزارش کامل وضعیت حاکمیت و توصیه‌ها

تاریخ: 2026-06-19

خلاصهٔ اجرایی
- وضعیت فعلی: بخشی از موارد حیاتی پیاده‌سازی شده‌اند اما چندین مسیر اجرای پرس‌وجو (graph service، retrieval، RAG) هنوز از کنترل مرکزی سیاست و فیلتر tombstone عبور نمی‌کنند.
- موارد حل‌شده (پوشش P0/P1 اولیه): PolicyResolver، UnifiedGovernanceController، soft-delete و مرزِ مجازسازی نوشتن، و الزامات EL‑I8 در موتور استدلال.
- موارد باقیمانده: یکپارچه‌سازی `UnifiedGovernanceController` در سرویس‌های پرس‌وجو عمومی (`mahoun/graph/graph_query_service.py`)، ایجاد wrapper مرکزی برای اجرای پرس‌وجو با سیاست (policy-enforced query wrapper)، و ثبتِ هم‌زمان (persistent unified audit) تصمیمات ترکیبی Kernel+Policy به دفتر کلِ غیرقابل‌تغییر.

فهرست تسک‌ها (مطابقت با 10 تسک اولیه)
- 1) Verify PolicyResolver: انجام شده ✅
- 2) Verify UnifiedGovernanceController: انجام شده ✅
- 3) Check soft-delete and mutation boundary: انجام شده ✅
- 4) Scan graph query services for tombstone filtering: در جریان (چندین query محلی دارای فیلتر هستند اما `GraphQueryService` عمومی هنوز یکپارچه نشده) ⚠️
- 5) Scan reasoning services for EL‑I8 enforcement: انجام شده ✅
- 6) Search for policy-enforced query wrapper: پیدا نشده ❌
- 7) Search for profile-based depth limits & enforcement: در جریان (قواعد وجود دارند اما باید در سرویس‌های فراگیر اعمال شوند) ⚠️
- 8) Search for unified audit trail integration: پیدا نشده — تصمیمات unified هنوز به دفتر کل غیرقابل‌تغییر نوشته نمی‌شوند ❌
- 9) Check semantic search & retrieval integration: در جریان — ماژول‌ها وجود دارند اما مشورت با ExecutionPolicy کامل نیست ⚠️
- 10) Produce final report mapping issues to status: انجام شده ✅

یافته‌های فنی جزئی‌شده

1) `mahoun/core/policy_resolver.py`
- وضعیت: پیاده‌سازی کامل با `ExecutionPolicy` و `ViewMode`؛ آدیت‌تریلِ تصمیمات policy به‌صورت درون‌حافظه ثبت می‌شود.
- نکتهٔ مهم: منطقِ ACTIVE vs HISTORICAL برای tombstone مشخص شده؛ اما نیاز است که هر اجرای پرس‌وجو از این resolver استفاده کند تا سیاست‌ها اعمال شوند.

2) `mahoun/core/unified_governance.py`
- وضعیت: کنترلر آماده است؛ وظایفش شامل تزریق فیلتر tombstone، محدودسازی عمق مسیر و اضافه کردن LIMIT پیش‌فرض است.
- نکتهٔ مهم: کنترلر audit درون‌حافظه ذخیره می‌کند اما هنوز تصمیمات ترکیبی به دفتر کل پایدار نوشته نمی‌شوند.

3) `mahoun/core/governance/mutation_boundary.py`
- وضعیت: مرز نوشتن (GovernedNeo4jSession) و مکانیزم soft-delete پیاده شده؛ تابع `_append_governance_audit` وجود دارد که dual-write محلی و remote ledger mock انجام می‌دهد.
- نکتهٔ مهم: این مکانیزم برای عملیات نوشتن اعمال می‌شود و رفتار fail-closed برای append audit رعایت شده است.

4) `mahoun/reasoning/evidence_linked_verdict.py`
- وضعیت: EL‑I8 اعمال شده — هر ورودی با `_deleted == True` موجب خطا/رد می‌شود.
- نکتهٔ مهم: این گارد باعث جلوگیری از استفاده صریح شواهد حذف‌شده در مراحل استدلال می‌شود، اما بهتر است قبل از تولید نتایج، از ورود آنها جلوگیری شود (یعنی در لایهٔ پرس‌وجو فیلتر شود).

5) `mahoun/graph/graph_query_service.py` و سایر سرویس‌های گراف
- وضعیت: برخی queryهای حوزه‌ای (`legal_cypher_queries.py`, `ultra_graph_query_service.py`) فیلتر tombstone دارند اما `GraphQueryService` عمومی هنوز از `UnifiedGovernanceController.prepare_query_execution()` استفاده نمی‌کند.
- ریسک: هر مسیر که از `GraphQueryService` یا retrieval مستقیم به‌عنوان منبع حقیقت استفاده کند میتواند bypass ایجاد کند و دادهٔ tombstoned وارد downstream (مثلاً موتور استدلال یا RAG) شود.

6) Retrieval / RAG (`mahoun/retrieval/*`, `mahoun/rag/*`)
- وضعیت: ماژول‌های بازیابی و RAG موجودند؛ اما تماس سیستماتیک با `ExecutionPolicy.semantic_enabled` و محدودیت‌های policy کم‌بسامد است.

7) Audit trail متحد
- وضعیت: هر لایه (kernel mutation boundary، policy resolver، unified controller) آدیته خاص خودش را درون‌حافظه یا در فایل‌های محلی ثبت می‌کند؛ اما یک خط لولهٔ یکپارچه که `UnifiedGovernanceDecision`ها را به دفتر کل غیرقابل‌تغییر (logs/remote_immutable.ledger) بنویسد وجود ندارد.

توصیه‌های اصلاحی (اولویت‌بندی شده)

P0 — فوری
- A) یکپارچه‌سازی `UnifiedGovernanceController` در `GraphQueryService`:
  - چرا: این نقطهٔ ورود عمومی برای پرس‌وجوها است؛ اگر کنترلر تزریق نشود، فیلترهای domain-specific قابل دور زدن‌اند.
  - چگونگی اجرا (خلاصه): در `mahoun/graph/graph_query_service.py` قبل از اجرای هر cypher/graph query، فراخوانی `controller.prepare_query_execution(query, operation='read', profile=profile)` و سپس اجرای `decision.transformed_query` یا اجرای یک wrapper که تصمیم را اعمال می‌کند.
  - تست‌های پیشنهادی: تست واحدی که یک query حاوی نود حذف‌شده را از طریق `GraphQueryService` درخواست می‌کند و اطمینان می‌دهد که خروجی فاقد آن نود است.

- B) جلوگیری از نشت tombstone به موتور استدلال و RAG:
  - چرا: حتی با EL‑I8 در موتور استدلال، بهتر است از منبع داده جلوگیری شود تا از خطاهای غیرمنتظره و هزینه‌های محاسباتی محفوظ بمانیم.
  - چگونگی اجرا: تمامی pathهای بازیابی (graph queries, retrieval, hybrid_search) باید قبل از اجرا تصمیم policy را دریافت کنند و بر اساس آن فیلتر tombstone/حد عمق/semantic toggle اعمال گردد.

P1 — مهم
- C) پیاده‌سازی `PolicyEnforcedQueryExecutor` wrapper:
  - API ساده: `execute_query(query, operation='read', profile=None, engine=...)` که به ترتیب: resolve policy، prepare unified decision، persist decision (see D)، و اجرا/لاگ نهایی را انجام می‌دهد.
  - فایده: یک نقطهٔ واحد برای telemetry، آدیته و خطاهای fail-closed.

- D) نوشتن persistent unified audit (Dual-write):
  - چرا: برای انطباق و بررسی باید هر تصمیم ترکیبی Kernel+Policy به دفتر کل غیرقابل‌تغییر نوشته شود.
  - چگونگی اجرا: گسترش `_append_governance_audit` یا اضافه کردن یک pipeline در `UnifiedGovernanceController` تا قبل از اجرای query تصمیم را به `logs/governance.audit` و `logs/remote_immutable.ledger` append کند؛ رفتار fail-closed یعنی در صورت خطای نوشتن، اجرای پرس‌وجو متوقف شود یا به حالت safe fallback برود.

P2 — بهبودها و نرمال‌سازی
- E) تسری profile-based depth limits: mapping پروفایل‌ها در `PolicyResolver` را به اجراگرها متصل کنید و default profile برای سرویس‌ها را تعریف کنید.
- F) سازوکار تست و نظارت: اضافه کردن unit/integration tests و یک test matrix که سناریوهای tombstone, historical view, semantic_enabled و depth-limit را پوشش دهد.
- G) مستندسازی API: مستند کنید که چگونه سرویس‌های جدید باید از `PolicyEnforcedQueryExecutor` استفاده کنند.

محدودهٔ کاری پیشنهادی (تخمینی)
- ادغام `UnifiedGovernanceController` در `GraphQueryService`: 2-4 ساعت کدنویسی + 1 ساعت تست محلی.
- گسترش به retrieval/RAG: 3-6 ساعت بسته به تعداد نقاط تماس و پیچیدگی تست‌های RAG.
- پیاده‌سازی persistent unified audit: 2-3 ساعت برای pipeline نوشتن و بررسی fail-closed.

مراحل عملی و گام‌های بعدی (پیشنهاد برای اجرای فوری)
1) تأیید کنید که می‌خواهم ادغام کنترلر در `mahoun/graph/graph_query_service.py` را انجام دهم — من می‌توانم همین الآن آن را پیاده‌سازی و تست کنم.
2) پس از ادغام گام 1، اجرای تست‌های بازیابی برای بررسی اینکه tombstone دیگر نشت نمی‌کند.
3) پیاده‌سازی `PolicyEnforcedQueryExecutor` و روتینگ retrieval/RAG به آن.
4) پیاده‌سازی dual-write برای unified audit و افزایش تست‌های مربوطه.

فایل‌ها و نقاطی که باید تغییر کنند (فهرست مستقیم)
- `mahoun/graph/graph_query_service.py` — تزریق `UnifiedGovernanceController` و استفاده از `prepare_query_execution()` پیش از اجرا.
- `mahoun/retrieval/*` و `mahoun/rag/*` — فراخوانی policy resolver / unified controller برای هر فراخوانی بازیابی.
- `mahoun/core/unified_governance.py` — افزودن نقطهٔ persistence برای `UnifiedGovernanceDecision` یا فراهم کردن یک callback برای dual-write.
- `mahoun/core/policy_resolver.py` — (اختیاری) افزودن API ساده برای fetch profile defaults به‌صورت برنامه‌محور.

پیوست: نمونهٔ pseudo-change برای `GraphQueryService` (کد خلاصه)

```python
# قبل از اجرای query
decision = unified_controller.prepare_query_execution(query, operation='read', profile=profile)
# بررسی و اجرا
transformed = decision.transformed_query or query
result = neo4j_driver.run(transformed, **params)
```

خاتمه
- گزارش فوق در سطح فایل نوشته و در `lastreport.md` ذخیره شده است.
- اگر تأیید کنید، من بلافاصله ادغام `UnifiedGovernanceController` را در `mahoun/graph/graph_query_service.py` انجام می‌دهم و سپس گزارش موفقیت آن را اینجا آپدیت می‌کنم.

---
فایل ایجاد شد و آمادهٔ ویرایش یا commit است.

تغییرات اخیر و جزئیات پیاده‌سازی
--------------------------------

این بخش تمام تغییرات کدی که در جلسهٔ اخیر انجام گرفته را با جزئیات فنی و مسیر فایل‌ها فهرست می‌کند.

1) `mahoun/core/unified_governance.py`
- عمل: افزودن persistence آدیته unified به دفتر آدیته غیرقابل‌تغییر (dual-write) پیش از بازگشت تصمیم.
- فایل/تابع: در انتهای `prepare_query_execution()` پس از append کردن تصمیم به `_audit_trail` خط‌هایی اضافه شد که:
  - `decision.to_dict()` را ایجاد می‌کنند و با `source: unified_governance_controller` علامت می‌زنند.
  - سپس با فراخوانی `_append_governance_audit(entry)` از `mahoun.core.governance.mutation_boundary` هر تصمیم را به دو لاگ محلی و remote ledger می‌نویسند.
  - خطاها logged و در صورت فعال بودن `strict_mode` موجب raise می‌شوند (fail-closed).

نمونهٔ خلاصهٔ اثر:
```py
entry = decision.to_dict()
entry.update({"source": "unified_governance_controller"})
_append_governance_audit(entry)
```

2) `mahoun/graph/graph_query_service.py` (Neo4jConnectionManager & execute_query)
- عمل: یکپارچه‌سازی تصمیم‌گیری unified در مسیر اجرای کوئری گراف.
- تغییرات اصلی:
  - در سازندهٔ `Neo4jConnectionManager` یک نمونهٔ `UnifiedGovernanceController` ساخته و در `self._unified_controller` نگهداری می‌شود (fallback با لاگ در صورت خطا).
  - در `execute_query()` و `execute_query_async()` قبل از ارزیابی kernel، اگر controller موجود باشد `prepare_query_execution(query, context)` فراخوانی می‌شود.
  - در صورتی که تصمیم `approved == False` باشد، برای کوئری‌های حساس deny رخ می‌دهد؛ برای READهای غیرحساس نتیجهٔ خالی برگردانده می‌شود.
  - اگر `decision.query_transformed` فعال باشد، `query` با `decision.transformed_query` جایگزین می‌شود.
  - در صورت خطای controller لاگ ثبت و fallback به enforcement قدیمی kernel انجام می‌شود.

نمونهٔ خلاصهٔ اثر:
```py
decision = self._unified_controller.prepare_query_execution(query=query, context=ctx)
if not decision.approved:
    raise GovernanceError(...)
if decision.query_transformed:
    query = decision.transformed_query
```

توجه: مسیر async نیز مشابه مسیر sync به‌روز شد تا تضمین کند رفتار یکسان است.

3) `mahoun/retrieval/ultra_hybrid_search.py`
- عمل: محافظت از اجرای dense/semantic retrieval با توجه به policy.
- تغییرات اصلی:
  - در متد `DenseRetriever.search()` قبل از استفاده از embeddingها، یک `ExecutionPolicy` از `create_default_policy_resolver().resolve_policy(...)` خوانده می‌شود.
  - اگر `policy.semantic_enabled == False` یا resolution شکست بخورد، dense retrieval نادیده گرفته شده و اجرای fallback (یا نتیجهٔ خالی) برگردانده می‌شود.

نمونهٔ خلاصهٔ اثر:
```py
policy = create_default_policy_resolver().resolve_policy(context=SimpleNamespace(...))
if not policy.semantic_enabled:
    return []  # skip dense
```

4) جدید: `mahoun/core/query_executor.py` (ماژول ایجاد شده)
- عمل: افزودن wrapper مرکزی `execute_cypher` و `execute_cypher_async` که همهٔ فراخوانی‌های Cypher را از طریق `GraphQueryService` عبور می‌دهد.
- مزایا:
  - مسیر ساده و قابل import برای سایر ماژول‌ها تا اجرای کوئری‌ها policy-aware شود.
  - نقطهٔ واحد برای telemetry و آینده‌نگری (قابلیت جایگزینی با `PolicyEnforcedQueryExecutor`).

نمونهٔ استفاده:
```py
from mahoun.core.query_executor import execute_cypher
results = execute_cypher("MATCH (n) RETURN n LIMIT 10", correlation_id="cid", actor_id="user")
```

فایل‌های تغییر کرده و دلایل اصلی آن‌ها
- `mahoun/core/unified_governance.py`: ذخیرهٔ تصمیم‌ها در دفتر آدیت غیرقابل‌تغییر برای انطباق و شواهد.
- `mahoun/graph/graph_query_service.py`: اعمال تصمیم unified قبل از اجرای کوئری و جلوگیری از bypass حوزه‌ای.
- `mahoun/retrieval/ultra_hybrid_search.py`: جلوگیری از اجرای semantic در صورتی که policy آن را خاموش کند.
- `mahoun/core/query_executor.py`: wrapper برای مسیر امن اجرای Cypher.

ملاحظات اجرایی و تستی بلافاصله پس از این تغییرات
- اجرای smoke testها: اطمینان از اینکه `logs/governance.audit` و `logs/remote_immutable.ledger` نوشته می‌شوند.
- بررسی fallbacks: وقتی `UnifiedGovernanceController` خطا دهد، سیستم باید به enforcement kernel برگردد و لاگ ثبت کند.
- بررسی performance: تبدیل کوئری‌ها و resolve policy ممکن است latency اضافه کند؛ اندازه‌گیری p50/p95 بعد از deploy ضروری است.

نکتهٔ امنیتی
- آدیته unified اکنون قبل از اجرای read/write ثبت می‌شود؛ در `strict_mode` اگر append به لاگ fail کند، اجرای query متوقف می‌شود — این رفتار باید هنگام rollout به دقت مانیتور شود تا false positiveهای ناشی از مشکلات I/O باعث وقفهٔ غیرضروری نشوند.

چند گام پیشنهادی بعدی (اولویت‌بندی):
1. Inventory کامل نقاط تماس retrieval/RAG و جایگزینی گام‌به‌گام با `execute_cypher` (این مورد را من می‌توانم شروع کنم).
2. نوشتن 3 تست کلیدی: tombstone exclusion، historical view justification، semantic toggle fallback.
3. اجرای smoke روی staging و بازبینی لاگ‌های audit برای چندین درخواست واقعی.

این تغییرات اکنون در مخزن اعمال شده‌اند — در صورت نیاز می‌توانم patchهای کوچک بعدی برای وصل کردن سایر modules (مثلاً `graph_hop.py`, `ultra_graph_query_service.py`, `hybrid_rag_service.py`) آماده کنم و تست‌های مرتبط را اجرا کنم.

