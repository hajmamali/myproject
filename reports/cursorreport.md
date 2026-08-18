# گزارش بررسی فرانت‌اند MahouN

**تاریخ:** ۱۸ آگوست ۲۰۲۶  
**ابزار:** Cursor Agent (بررسی استاتیک + اجرای lint/tsc/test/contract check)  
**دامنه:** پوشه `frontend/`  
**وضعیت کلی:** ⚠️ **آماده production نیست** — build شکسته، drift API، auth mock، و technical debt ساختاری

---

## خلاصه اجرایی

فرانت‌اند MahouN از نظر پوشش feature (جستجوی حقوقی، chat، upload، governance، training، A/B test و …) غنی است، اما در وضعیت فعلی **سه blocker اصلی** دارد:

1. **خطاهای JSX/TypeScript** در ۳ فایل که `npm run build` را fail می‌کند
2. **دو لایه API client موازی** (`src/api/` vs `shared/api/`) با endpointهای ناسازگار با بک‌اند
3. **Authentication و داده mock** بدون wire واقعی به API

علاوه بر این، **۲۳ نقض API contract**، **۴۹ تست fail از ۶۰**، و **تکرار گسترده کامپوننت‌ها** بین `src/` و `shared/` وجود دارد.

---

## ۱. معماری پراکنده و تکراری (اولویت: بالا)

### ۱.۱ ساختار سه‌گانه entry point

| دستور npm | root Vite | entry | App | پورت |
|---|---|---|---|---|
| `npm run dev` | `frontend/` (پیش‌فرض) | `index.html` → `src/main.tsx` | `src/App.tsx` | vite default |
| `npm run dev:user` | `frontend/user/` | `user/main.tsx` | `user/App.tsx` | 3000 |
| `npm run dev:developer` | `frontend/developer/` | `developer/main.tsx` | `developer/App.tsx` | 3001 |

**مشکل:** توسعه‌دهنده بسته به دستور، اپ متفاوتی می‌بیند:
- `src/App.tsx` — monolith کامل با auth، ProtectedRoute، governance، studio
- `user/App.tsx` — فقط user-facing، **بدون ProtectedRoute**، import از `@shared`
- `developer/App.tsx` — فقط dev tools، import از `@shared`

### ۱.۲ تکرار کامپوننت بین `src/components/` و `shared/components/`

**۲۲ کامپوننت** در هر دو مسیر وجود دارد (احتمال drift بالا):

| کامپوننت | `src/components/` | `shared/components/` |
|---|---|---|
| LegalSearchPage | ✅ | ✅ |
| Dashboard | ✅ | ✅ |
| AIChat | ✅ | ✅ |
| AdvancedDocumentUpload | ✅ | ✅ |
| ContractQA | ✅ | ✅ |
| DelayAnalysisDashboard | ✅ | ✅ |
| TimelineVisualization | ✅ | ✅ |
| TrainingDashboard | ✅ | ✅ |
| MonitoringDashboard | ✅ | ✅ |
| ABTestingDashboard | ✅ | ✅ |
| ModelSelector | ✅ | ✅ |
| AppLayout | ✅ | ✅ |
| StudioLayout | ✅ | ✅ |
| CommandPalette | ✅ | ✅ |
| SearchFilters | ✅ | ✅ |
| ResultsList | ✅ | ✅ |
| ResultCard | ✅ | ✅ |
| ExportButton | ✅ | ✅ |
| UploadModal | ✅ | ✅ |
| StatsPanel | ✅ | ✅ |

**فقط در `src/components/` (بدون نسخه shared):**
AuditCenter, DatasetBrowser, DatasetUploader, ErrorBoundary, ExperimentDesigner, FailClosedMonitor, GraphQualityValidation, JobStatusMonitor, MutationAuthorization, NavigationSidebar, ResultsAnalysis, Toast

**فقط در `shared/components/` (بدون نسخه src):**
CryptographicProofBadge, EvidenceTrail

### ۱.۳ دو لایه API client

| مسیر | فایل‌ها | مصرف‌کننده |
|---|---|---|
| `frontend/src/api/` | `client.ts`, `trainingClient.ts`, `mahounClient.ts`, `types.ts` | `src/components/*` |
| `frontend/shared/api/` | `client.ts`, `trainingClient.ts`, `mahounClient.ts`, `chatClient.ts`, `searchClient.ts`, `experimentsClient.ts`, `finetuningClient.ts`, `monitoringClient.ts`, `types.ts` | `shared/components/*`, `user/App.tsx`, `developer/App.tsx` |

**نمونه drift بحرانی — جستجوی آراء:**

| Client | فایل:خط | Method | Endpoint |
|---|---|---|---|
| `src/api/client.ts` | 73 | **GET** | `/api/search/verdicts?...` |
| `shared/api/client.ts` | 283 | **POST** | `/v1/search/verdicts` |
| **بک‌اند واقعی** | `api/routers/search.py:156-197` | **POST** | `/v1/search/verdicts` |

→ `src/components/LegalSearchPage.tsx` (via `src/api/client`) endpoint **اشتباه** دارد.  
→ `shared/components/LegalSearchPage.tsx` (via `shared/api/client`) endpoint **درست** دارد.  
→ `user/App.tsx` از `@shared/components/LegalSearchPage` استفاده می‌کند (درست).  
→ `src/App.tsx` از `./components/LegalSearchPage` استفاده می‌کند (اشتباه).

---

## ۲. خطاهای Build / TypeScript (اولویت: بحرانی)

`npx tsc --noEmit` — **fail** با ۲۰+ خطا  
`npm run lint` — **۵ error + ۵۳ warning**

### ۲.۱ JSX syntax errors (blocker build)

#### `frontend/src/components/TrainingDashboard.tsx:183-186`

```tsx
{models.map(model => (
  <option key={model.id} value={model.id}>
    {model.name} ({model.provider} {model.version})
  >                          // ❌ باید </option> باشد
))}
```

**خطای tsc:** `TS1382: Unexpected token. Did you mean {'>'} or &gt;?`  
**خطای eslint:** `Parsing error: Unexpected token` (خط 185)

---

#### `frontend/src/components/FineTuningDashboard.tsx:240` و `:294`

**خط 240** — `<li>` بسته نشده:
```tsx
                    >
                  ))}          // ❌ </li> گم شده
```

**خط 292-294** — همان الگو در `<option>`:
```tsx
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider} {model.version})
                    >          // ❌ باید </option> باشد
```

**خطای tsc:** `TS17008: JSX element 'div' has no corresponding closing tag` (cascade)

---

#### `frontend/src/components/GraphQualityValidation.tsx:209`

```tsx
<h3 className="text-white font-medium mb-2">یال‌های گمشده</h33>
                                                          ^^^^
                                                          typo: h33
```

**خطای tsc:** `TS17002: Expected corresponding JSX closing tag for 'h3'`  
**خطای eslint:** `Expected corresponding JSX closing tag for 'h3'` (خط 209)

---

### ۲.۲ ESLint errors (غیر JSX)

#### `frontend/shared/utils/security.ts:39`

```tsx
.replace(/[<>\"\']/g, '')   // ❌ unnecessary escape: \" و \'
```

**خطا:** `no-useless-escape` (۲ مورد)

---

### ۲.۳ HTML syntax error

#### `frontend/index.html:22`

```html
<meta http-equiv="X-Content-Type-Options" content="nosniff />
                                                              ^ quote بسته نشده
```

---

## ۳. نقض API Contract — ۲۳ violation (اولویت: بالا)

**اسکریپت:** `scripts/check_api_contracts.py`  
**تاریخ اجرا:** ۱۸ آگوست ۲۰۲۶  
**نتیجه:** ❌ FAILED — ۲۳ violation، ۰ warning  
**بک‌اند routes:** ۱۳۷ | **فرانت‌اند API calls:** ۴۱

### ۳.۱ لیست کامل violations

| # | فایل:خط | Method | Endpoint (normalized) | وضعیت بک‌اند |
|---|---|---|---|---|
| 1 | `api/client.ts:73` | GET | `/api/search/verdicts` | ❌ — بک‌اند: `POST /v1/search/verdicts` |
| 2 | `api/client.ts:77` | GET | `/api/verdicts/{param}` | ❌ route وجود ندارد |
| 3 | `api/client.ts:81` | POST | `/api/verdicts` | ❌ route وجود ندارد |
| 4 | `api/mahounClient.ts:13` | GET | `/api/jobs/{param}` | ❌ |
| 5 | `api/mahounClient.ts:17` | POST | `/api/jobs/{param}/cancel` | ❌ |
| 6 | `api/mahounClient.ts:21` | POST | `/api/jobs/{param}/retry` | ❌ |
| 7 | `api/mahounClient.ts:34` | GET | `/api/jobs` | ❌ |
| 8 | `api/mahounClient.ts:38` | GET | `/api/documents/{param}/ocr-status` | ❌ |
| 9 | `api/mahounClient.ts:42` | POST | `/api/documents/{param}/ocr-retry` | ❌ |
| 10 | `api/trainingClient.ts:20` | GET | `/api/training/jobs` | ❌ |
| 11 | `api/trainingClient.ts:24` | GET | `/api/training/jobs/{param}` | ❌ |
| 12 | `api/trainingClient.ts:33` | POST | `/api/training/jobs` | ❌ |
| 13 | `api/trainingClient.ts:37` | POST | `/api/training/jobs/{param}/stop` | ❌ |
| 14 | `api/trainingClient.ts:41` | DELETE | `/api/training/jobs/{param}` | ❌ |
| 15 | `api/trainingClient.ts:45` | GET | `/api/training/models` | ❌ |
| 16 | `api/trainingClient.ts:49` | GET | `/api/training/models/{param}` | ❌ |
| 17 | `api/trainingClient.ts:53` | POST | `/api/training/jobs/{param}/deploy` | ❌ |
| 18 | `components/ABTestingDashboard.tsx:41` | GET | `/api/v1/experiments` | ❌ |
| 19 | `components/GraphQualityValidation.tsx:48` | GET | `/api/v1/graph/quality/metrics` | ❌ |
| 20 | `components/GraphQualityValidation.tsx:55` | GET | `/api/v1/graph/integrity/issues` | ❌ |
| 21 | `components/GraphQualityValidation.tsx:62` | GET | `/api/v1/graph/completeness/report` | ❌ |
| 22 | `components/ResultsAnalysis.tsx:48` | GET | `/api/v1/experiments/{param}/results` | ❌ |
| 23 | `components/StudioLayout.tsx:95` | GET | `/api/system/health` | ❌ |

> **نکته:** اسکریپت contract check مسیرهای `frontend/src/` را اسکن می‌کند. `shared/api/client.ts` که endpoint درست (`POST /v1/search/verdicts`) دارد در این ۲۳ violation نیست — اما `src/api/` که default monolith از آن استفاده می‌کند، همه violations مربوط به search/verdicts/training/jobs را دارد.

**Enforcement chain:**
- PRE-COMMIT: (contract check اجرا نمی‌شود)
- PRE-PUSH: `scripts/check_api_contracts.py`
- CI: wired via pre-push + workflow

---

## ۴. Mock Data / Fabrication (اولویت: بالا)

طبق `AGENTS.md` §1-J و gate `ci/first_step/gate_4b_frontend_antimock.sh`، نمایش داده ساختگی به‌جای API واقعی **fabrication violation** است. هیچ marker `fabrication-check-ok` در کل `frontend/` یافت نشد.

### ۴.۱ Authentication mock

#### `frontend/src/store/authStore.ts:54-65`

```typescript
login: async (email: string, _password: string) => {
  // Mock login - replace with actual API call
  const mockUser: User = {
    id: '1',
    email,
    name: email.split('@')[0],
    role: Role.ANALYST,
    permissions: [Permission.READ, Permission.WRITE],
  };
  set({ user: mockUser, isAuthenticated: true, isLoading: false });
},
```

→ هیچ درخواست HTTP به بک‌اند نمی‌رود. password نادیده گرفته می‌شود (`_password`).

#### `frontend/shared/stores/authStore.ts:122-137`

```typescript
// Development hardcoded user for demo purposes
if (import.meta.env.DEV && credentials.username === 'haji' && credentials.password === 'haji') {
  const mockUser = { username: 'haji', user_id: 'user_haji_001', role: Role.ADMIN, ... };
  set({ isAuthenticated: true, user: mockUser, token: 'mock_token_dev_haji', ... });
}
```

→ hardcoded credential `haji/haji` با token ثابت.

### ۴.۲ Mock data در صفحات UI

| فایل | خط | نوع mock |
|---|---|---|
| `shared/pages/KnowledgeGraphCenter.tsx` | 25-31 | `useState<GraphNode[]>` با ۴ گره حقوقی ثابت + SVG canvas mock |
| `shared/pages/ModelRegistry.tsx` | 25-48 | `MOCK_MODELS` — ۲ مدل Persian-Legal-7B و Persian-Embedding |
| `shared/pages/DatasetEngineering.tsx` | 25-38 | `MOCK_DATA_SOURCES`, `MOCK_DATASETS` — fetch functions مستقیم mock برمی‌گردانند |
| `shared/api/trainingClient.ts` | 189-208 | fallback mock models وقتی `/api/v1/training/models` fail شود |

### ۴.۳ ProtectedRoute ناقص در user app

`frontend/user/App.tsx` — همه routeها (`/search`, `/chat`, `/upload`, …) **بدون auth guard**:
```tsx
<Route path="/search" element={<LegalSearchPage />} />
<Route path="/chat" element={<AIChat />} />
```

در مقابل `src/App.tsx` از `<ProtectedRoute requireAuth={true}>` استفاده می‌کند — اما auth خودش mock است.

---

## ۵. وضعیت تست‌ها (اولویت: متوسط)

**دستور:** `npm test -- --run`  
**نتیجه:**

```
Test Files:  6 failed | 2 passed (8)
Tests:       49 failed | 11 passed (60)
نرخ fail:    ~82%
```

### ۵.۱ فایل‌های test fail

| فایل test | وضعیت | علت محتمل |
|---|---|---|
| `src/test/trainingClient.test.ts` | ❌ همه fail | import `getAvailableModels`, `getTrainingPresets` — **export نشده** در `src/api/trainingClient.ts` |
| `src/test/TrainingDashboard.test.tsx` | ❌ fail | JSX syntax error در component under test |
| `src/test/ABTestingDashboard.test.tsx` | ❌ ۱۵+ test fail | component/API mismatch |
| `src/test/ModelSelector.test.tsx` | ❌ fail | component rendering/API |
| `src/test/MonitoringDashboard.test.tsx` | ❌ fail | mock training client |
| `src/test/ErrorBoundary.test.ts` | ✅ pass | — |
| `src/test/Toast.test.ts` | ✅ pass | — |

### ۵.۲ نمونه خطای trainingClient

```
TypeError: getAvailableModels is not a function
  at src/test/trainingClient.test.ts:157
```

`src/api/trainingClient.ts` فقط export می‌کند:
- `listTrainingJobs`, `getTrainingJob`, `createTrainingJob`, `stopTrainingJob`, `deleteTrainingJob`

اما test انتظار دارد:
- `getAvailableModels`, `getTrainingPresets` (که در `shared/api/trainingClient.ts` وجود دارند)

---

## ۶. ESLint warnings (اولویت: پایین)

**۵۳ warning** — دسته‌بندی:

| Rule | تعداد تقریبی | فایل‌های نمونه |
|---|---|---|
| `no-console` | ~۱۰ | `authStore.ts`, `governanceStore.ts`, `errorService.ts`, `user/App.tsx` |
| `react-hooks/exhaustive-deps` | ~۵ | `useError.ts` |
| `react-refresh/only-export-components` | ~۴ | error boundary files |
| `@typescript-eslint/no-unused-vars` | ۲ | `vite.user.config.ts:5`, `vite.developer.config.ts:5` (`mode` unused) |

---

## ۷. مشکلات امنیتی و CSP

### ۷.۱ Content-Security-Policy در `index.html`

```html
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net;
```

→ `'unsafe-eval'` و `'unsafe-inline'` در production توصیه نمی‌شود.

### ۷.۲ Vite proxy (dev only)

`vite.base.config.ts:64-75` — proxy `/v1` و `/api` به `localhost:8000`. در production nginx باید همین routing را handle کند (`frontend/nginx.conf` موجود است — verify wiring لازم است).

---

## ۸. مستندات stale در `frontend/`

فایل‌های markdown داخل `frontend/` که ممکن است وضعیت واقعی را misrepresent کنند:

| فایل | ریسک |
|---|---|
| `COMPLETE_IMPLEMENTATION_SUMMARY.md` | claim completion بدون evidence |
| `HARVEY_STYLE_ROADMAP.md` | roadmap — نه وضعیت فعلی |
| `HARVEY_STYLE_UI.md` | design doc |
| `DEVELOPER_DASHBOARD_PROPOSAL.md` | proposal |
| `ENTERPRISE_ARCHITECTURE_V2.md` | architecture doc |
| `tsc_output.txt` | **۳ خط قدیمی** — با وضعیت فعلی (۲۰+ error) هم‌خوان نیست |

---

## ۹. آنچه درست کار می‌کند ✅

| مورد | evidence |
|---|---|
| `shared/api/client.ts` — endpoint search درست | `POST /v1/search/verdicts` (خط 283) |
| `shared/components/LegalSearchPage.tsx` — pattern canonical | real `await searchVerdicts(...)` + error/loading states |
| Architecture check user app | `npm run check-architecture` — ✅ no forbidden developer imports |
| Vite dual-app split design | `user/` (3000) + `developer/` (3001) با alias `@shared` |
| Test infrastructure | vitest + testing-library setup در `src/test/setup.ts` |
| Governance headers در shared API client | `X-Request-ID`, `X-Trace-ID`, `X-Governance-Context` |

---

## ۱۰. ماتریس اولویت‌بندی رفع

| # | اقدام | فایل(ها) | تأثیر | تلاش |
|---|---|---|---|---|
| **P0** | Fix JSX syntax errors | `TrainingDashboard.tsx:185`, `FineTuningDashboard.tsx:240,294`, `GraphQualityValidation.tsx:209` | build unblock | ~۳۰ دقیقه |
| **P0** | Fix `index.html:22` quote | `frontend/index.html` | HTML valid | ۱ دقیقه |
| **P1** | حذف/redirect `src/api/` → `shared/api/` | `src/api/*`, imports در `src/components/*` | API drift رفع | ۲-۴ ساعت |
| **P1** | Wire auth به بک‌اند واقعی | `src/store/authStore.ts`, `shared/stores/authStore.ts` | امنیت | ۴-۸ ساعت |
| **P1** | ProtectedRoute در `user/App.tsx` | `user/App.tsx` | امنیت user app | ۱-۲ ساعت |
| **P2** | رفع ۲۳ API contract violations | clients + components listed in §3 | pre-push gate | ۱-۳ روز |
| **P2** | حذف mock data یا wire به API | KnowledgeGraphCenter, ModelRegistry, DatasetEngineering | fabrication compliance | ۱-۲ روز |
| **P2** | Sync tests با exports واقعی | `src/test/trainingClient.test.ts`, `src/api/trainingClient.ts` | CI green | ۲-۴ ساعت |
| **P3** | یکپارچه‌سازی `src/components/` → `shared/components/` | ۲۲ duplicate | technical debt | ۱-۲ هفته |
| **P3** | تصمیم canonical entry: monolith vs split | `src/App.tsx` vs `user/`/`developer/` | clarity | architectural decision |

---

## ۱۱. جمع‌بندی

فرانت‌اند MahouN **پتانسیل بالایی** دارد: UI فارسی RTL، feature coverage گسترده، split user/developer، و shared API client با governance headers. اما **در وضعیت فعلی production-ready نیست** به‌دلیل:

1. **Build شکسته** — ۳ فایل JSX syntax error
2. **API drift** — `src/api/` endpointهای اشتباه؛ ۲۳ contract violation
3. **Auth mock** — login واقعی وجود ندارد
4. **Fabrication** — mock data در صفحات کلیدی بدون suppression marker
5. **Test suite 82% fail**
6. **Technical debt** — ۲۲ کامپوننت duplicate بین src/ و shared/

**مسیر پیشنهادی:** ابتدا P0 (JSX fixes) → P1 (API unification + auth) → P2 (contracts + tests) → P3 (architectural consolidation).

---

*این گزارش بر اساس بررسی کد در تاریخ ۱۸ آگوست ۲۰۲۶ تهیه شده. برای verify مجدد:*

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run lint
cd frontend && npm test -- --run
cd .. && python scripts/check_api_contracts.py
cd frontend && npm run check-architecture
```
