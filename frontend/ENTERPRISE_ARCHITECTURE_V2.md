# MahouN Frontend - Enterprise Architecture v2.0

## 🎯 Vision: Role-Based, Domain-Driven Interface

پس از بررسی دقیق و feedback معماری، این طراحی نهایی است که **نقش‌محور** و **قابل‌رشد** است.

---

## 📐 معماری سطح بالا

```
MahouN Enterprise Platform
│
├── 🏠 User Portal              # End-user legal reasoning interface
├── 🔬 Workbench               # Operational capabilities (NOT just developers!)
├── 🛡️ Governance Center        # Constitutional compliance & audit
├── 📊 Operations Center        # System health & infrastructure
└── ⚙️ Administration          # Platform administration
```

---

## 🏗️ 1. User Portal (`/app/portal/`)

**نقش‌ها:** Legal Professionals, Analysts, End Users  
**هدف:** استفاده از قابلیت‌های AI برای استدلال حقوقی

### صفحات اصلی:
```
/app/portal/
├── dashboard          # خلاصه فعالیت‌ها و نتایج اخیر
├── search             # جستجوی پیشرفته حقوقی
├── reasoning          # AI Chat و استدلال تعاملی
├── documents          # مدیریت اسناد حقوقی
├── cases              # مدیریت پرونده‌ها
├── analysis           # تحلیل‌های آماده (تاخیر، timeline)
└── reports            # گزارشات و خروجی‌ها
```

### ویژگی‌های کلیدی:
- ✅ Zero-hallucination reasoning
- ✅ Evidence-based answers
- ✅ Audit trail integration
- ✅ Simple, user-friendly UI
- ✅ Persian/English bilingual support

---

## 🔬 2. Workbench (`/app/workbench/`)

**نقش‌ها:** ML Engineers, Data Engineers, Legal Curators, AI Operators  
**هدف:** ابزارهای عملیاتی برای ساخت و بهبود سیستم

> ⚠️ **Important:** این بخش فقط برای Developer نیست!  
> Data Engineer، Legal Curator، ML Operator همه اینجا کار می‌کنند.

### Domain-Driven Structure:

```typescript
/app/workbench/
│
├── 🤖 AI Studio                    # مدل‌ها و هوش مصنوعی
│   ├── models                     # Model selection & switching
│   ├── fine-tuning               # Fine-tune models
│   ├── evaluation                # Model evaluation & benchmarking
│   ├── experiments               # A/B testing
│   └── deployment                # Model deployment pipeline
│
├── 🕸️ Knowledge Graph              # گراف دانش
│   ├── builder                   # Interactive graph construction
│   ├── explorer                  # Graph navigation & search
│   ├── validation                # Integrity & quality checks
│   ├── analytics                 # Graph metrics & insights
│   └── provenance                # Data lineage tracking
│
├── 📊 Datasets                     # مدیریت داده
│   ├── browser                   # Browse & search datasets
│   ├── uploader                  # Upload new data
│   ├── annotator                 # Data annotation tools
│   ├── quality                   # Quality control dashboard
│   └── versioning                # Dataset versioning
│
├── 🎯 Training Pipeline            # آموزش و فاین‌تیونینگ
│   ├── jobs                      # Training job management
│   ├── configs                   # Training configurations
│   ├── monitoring                # Real-time training monitoring
│   ├── artifacts                 # Model artifacts & checkpoints
│   └── registry                  # Model registry
│
├── 🔍 Evaluation Suite             # ارزیابی و آزمایش
│   ├── benchmarks                # Standard benchmarks
│   ├── test-sets                 # Test dataset management
│   ├── metrics                   # Performance metrics
│   ├── reports                   # Evaluation reports
│   └── comparison                # Model comparison
│
├── 🧪 Experiments Lab              # آزمایش‌های A/B
│   ├── designer                  # Experiment design
│   ├── tracker                   # Active experiments
│   ├── results                   # Results analysis
│   └── insights                  # Statistical insights
│
├── 👁️ Observability                # نظارت سیستم
│   ├── metrics                   # System & model metrics
│   ├── logs                      # Centralized logging
│   ├── traces                    # Distributed tracing
│   ├── alerts                    # Alert management
│   └── dashboards                # Custom dashboards
│
├── ⚡ Runtime Management           # مدیریت Runtime
│   ├── profiles                  # Runtime profiles (minimal/full)
│   ├── resources                 # Resource allocation
│   ├── scaling                   # Auto-scaling config
│   └── health                    # Health monitoring
│
├── 🛡️ Governance Integration       # یکپارچگی با Governance
│   ├── policies                  # Policy management
│   ├── validation                # Compliance validation
│   ├── audit-logs                # Audit event viewer
│   └── permissions               # RBAC management
│
└── 🔧 Administration               # مدیریت پلتفرم
    ├── users                     # User management
    ├── roles                     # Role & permission config
    ├── settings                  # System settings
    └── backups                   # Backup & restore
```

### Key Features:

#### AI Studio
```typescript
interface AIStudioFeatures {
  // Model Management
  modelSelection: {
    baseModels: ModelOption[];
    fineTunedModels: ModelOption[];
    activeModel: ModelOption;
  };
  
  // Fine-Tuning Workflow with Evaluation Gate
  fineTuning: {
    stages: [
      'Data Preparation',
      'Training Configuration',
      'Training Execution',
      'Validation',           // ✅ Evaluation Gate
      'Benchmark Testing',    // ✅ Evaluation Gate
      'Governance Approval',  // ✅ Evaluation Gate
      'Model Registry',
      'Deployment'
    ];
  };
  
  // Experiments
  abTesting: {
    variants: ModelVariant[];
    traffic: TrafficSplit;
    metrics: ExperimentMetrics;
    winner: WinnerAnalysis;
  };
}
```

#### Knowledge Graph Explorer
```typescript
interface GraphExplorerFeatures {
  // Interactive Visualization
  visualization: {
    layout: 'force-directed' | 'hierarchical' | 'circular';
    nodeTypes: EntityType[];
    relationTypes: RelationType[];
  };
  
  // Not just visualization - EXPLORATION!
  exploration: {
    search: (query: string) => GraphNode[];
    expand: (node: GraphNode) => GraphNode[];
    explain: (node: GraphNode) => ExplanationPath[];
    trace: (evidence: Evidence) => ProvenancePath[];
    compare: (nodes: GraphNode[]) => ComparisonResult;
    timeline: (entity: Entity) => TimelineEvent[];
  };
  
  // Quality & Validation
  validation: {
    integrity: IntegrityReport;
    completeness: CompletenessScore;
    confidence: ConfidenceMetrics;
  };
}
```

---

## 🛡️ 3. Governance Center (`/app/governance/`)

**نقش‌ها:** Governance Officers, Compliance Auditors, Security Teams  
**هدف:** نمایش و مدیریت constitutional compliance

> 🎯 **این مهم‌ترین صفحه کل سیستم است!**  
> چون Governance قلب MahouN است، باید جلو هم دیده شود.

```typescript
/app/governance/
│
├── 📜 Constitution Dashboard       # وضعیت قانون اساسی
│   ├── status                     # Constitutional health status
│   ├── violations                 # Active violations
│   ├── compliance-score           # Overall compliance score
│   └── drift-detection            # Architectural drift alerts
│
├── 📝 Audit Center                 # مرکز ممیزی
│   ├── events                     # Real-time audit events
│   ├── timeline                   # Chronological audit timeline
│   ├── search                     # Advanced audit search
│   ├── analytics                  # Audit analytics & trends
│   └── export                     # Compliance report export
│
├── 🔐 Policy Engine                # موتور سیاست
│   ├── active-policies            # Active governance policies
│   ├── policy-editor              # Policy definition editor
│   ├── testing                    # Policy testing sandbox
│   └── enforcement                # Policy enforcement metrics
│
├── 🚨 Fail-Closed Monitor          # نظارت Fail-Closed
│   ├── events                     # Fail-closed events log
│   ├── impact-analysis            # Impact of each event
│   ├── recovery                   # Recovery actions
│   └── prevention                 # Prevention recommendations
│
├── 🎯 Mutation Authorization       # مجوز تغییرات
│   ├── pending                    # Pending write requests
│   ├── authorized                 # Authorized mutations
│   ├── rejected                   # Rejected mutations
│   ├── patterns                   # Common mutation patterns
│   └── risk-analysis              # Mutation risk assessment
│
├── ✅ Runtime Validation            # اعتبارسنجی Runtime
│   ├── active-checks              # Active validation checks
│   ├── results                    # Validation results
│   ├── failures                   # Validation failures
│   └── coverage                   # Validation coverage
│
└── 📊 Compliance Reports           # گزارشات Compliance
    ├── regulatory                 # Regulatory compliance
    ├── internal                   # Internal audits
    ├── security                   # Security posture
    └── performance                # Performance vs compliance
```

### Governance Dashboard Example:

```typescript
interface GovernanceDashboard {
  constitutionalHealth: {
    status: 'healthy' | 'degraded' | 'critical';
    score: number;  // 0-100
    issues: Issue[];
    lastValidation: Date;
  };
  
  auditMetrics: {
    totalEvents: number;
    criticalEvents: number;
    complianceRate: number;
    trends: TrendData[];
  };
  
  failClosedEvents: {
    total: number;
    byType: Record<string, number>;
    recentEvents: FailClosedEvent[];
    preventedViolations: number;
  };
  
  mutationAuthorization: {
    pendingRequests: number;
    approvalRate: number;
    averageReviewTime: number;
    riskDistribution: RiskDistribution;
  };
}
```

---

## 📊 4. Operations Center (`/app/operations/`)

**نقش‌ها:** Platform Operators, SREs, DevOps  
**هدف:** سلامت و عملکرد زیرساختار

```typescript
/app/operations/
│
├── 🏥 Health Dashboard
│   ├── system-status
│   ├── service-health
│   ├── dependency-map
│   └── incidents
│
├── 📈 Performance Metrics
│   ├── latency
│   ├── throughput
│   ├── error-rates
│   └── resource-usage
│
├── 🔍 Logs & Traces
│   ├── log-explorer
│   ├── trace-viewer
│   ├── correlation
│   └── analysis
│
├── 🚨 Alerts & Incidents
│   ├── active-alerts
│   ├── alert-rules
│   ├── incident-management
│   └── on-call-rotation
│
└── 🔧 Infrastructure
    ├── containers
    ├── databases
    ├── queues
    └── storage
```

---

## ⚙️ 5. Administration (`/app/admin/`)

**نقش‌ها:** Platform Administrators  
**هدف:** مدیریت کلی پلتفرم

```typescript
/app/admin/
├── 👥 User Management
├── 🔑 Access Control
├── ⚙️ System Configuration
├── 📦 Backup & Restore
└── 🔄 Updates & Migrations
```

---

## 🎭 نقش‌ها و دسترسی‌ها (RBAC)

```typescript
enum Role {
  // End Users
  LEGAL_PROFESSIONAL = 'legal_professional',    // Portal access
  ANALYST = 'analyst',                          // Portal + limited workbench
  
  // Operators
  ML_ENGINEER = 'ml_engineer',                  // AI Studio + Training
  DATA_ENGINEER = 'data_engineer',              // Datasets + Knowledge Graph
  LEGAL_CURATOR = 'legal_curator',              // Knowledge Graph + Datasets
  AI_OPERATOR = 'ai_operator',                  // All Workbench
  
  // Governance & Ops
  GOVERNANCE_OFFICER = 'governance_officer',    // Governance Center
  COMPLIANCE_AUDITOR = 'compliance_auditor',    // Governance (read-only)
  PLATFORM_OPERATOR = 'platform_operator',      // Operations Center
  
  // Admin
  ADMIN = 'admin',                              // Full access
}

interface RolePermissions {
  [Role.LEGAL_PROFESSIONAL]: {
    portal: ['read', 'write'];
    workbench: [];
    governance: [];
  };
  
  [Role.ML_ENGINEER]: {
    portal: ['read'];
    workbench: {
      ai_studio: ['read', 'write'],
      training: ['read', 'write', 'execute'],
      evaluation: ['read', 'write'],
      experiments: ['read', 'write'],
    };
    governance: ['read'];
  };
  
  [Role.DATA_ENGINEER]: {
    portal: ['read'];
    workbench: {
      datasets: ['read', 'write', 'upload'],
      knowledge_graph: ['read', 'write', 'build'],
    };
    governance: ['read'];
  };
  
  [Role.GOVERNANCE_OFFICER]: {
    portal: ['read'];
    workbench: ['read'];
    governance: ['read', 'write', 'authorize'];
    operations: ['read'];
  };
  
  // ... other roles
}
```

---

## 🚀 پیاده‌سازی مرحله‌ای

### Phase 1: Foundation (Week 1-2)
- ✅ Restructure routes to role-based architecture
- ✅ Implement RBAC system
- ✅ Create Layout components for each section
- ✅ Navigation system with role awareness

### Phase 2: Governance Center (Week 3-4) 🎯 **PRIORITY**
- ✅ Constitution Dashboard
- ✅ Audit Event Viewer
- ✅ Fail-Closed Monitor
- ✅ Mutation Authorization Panel
- ✅ Compliance Reports

### Phase 3: Workbench - Knowledge Graph (Week 5-6)
- ✅ Interactive Graph Builder
- ✅ Graph Explorer (search, expand, explain, trace)
- ✅ Timeline visualization
- ✅ Provenance tracking
- ✅ Quality validation

### Phase 4: Workbench - AI Studio (Week 7-8)
- ✅ Model Management Dashboard
- ✅ Fine-Tuning Pipeline with Evaluation Gates
  - Training → Validation → Benchmark → Approval → Deploy
- ✅ A/B Testing Dashboard
- ✅ Model Registry Integration

### Phase 5: Operations & Observability (Week 9-10)
- ✅ Health Dashboard
- ✅ Metrics & Monitoring
- ✅ Log Explorer
- ✅ Alert Management

### Phase 6: User Portal Enhancement (Week 11-12)
- ✅ Improved UX for end users
- ✅ Streamlined workflows
- ✅ Better evidence presentation
- ✅ Integrated help system

---

## 📊 مقایسه معماری

### ❌ قبل (Developer-centric):
```
/app/
├── user/          # کاربران عادی
└── developer/     # همه چیز توی یک جا!
    ├── fine-tuning
    ├── graph
    ├── monitoring
    └── ...
```

**مشکلات:**
- محدود به "Developer"
- دامنه‌های کاری مخلوط
- Governance پنهان
- غیرقابل‌رشد

### ✅ بعد (Enterprise Architecture):
```
MahouN/
├── Portal          # نقش: Legal Professionals
├── Workbench       # نقش: ML/Data Engineers, Curators
├── Governance      # نقش: Governance Officers
├── Operations      # نقش: SREs, Operators
└── Administration  # نقش: Admins
```

**مزایا:**
- ✅ نقش‌محور و قابل‌رشد
- ✅ Domain-driven organization
- ✅ Governance به عنوان first-class citizen
- ✅ واضح و maintainable
- ✅ Scalable for team growth

---

## 🎯 تفاوت کلیدی با Proposal اولیه

### 1. Naming
- ❌ `/developer/` → ✅ `/workbench/`
- Reasoning: Workbench برای همه operators است، نه فقط developers

### 2. Domain Organization
- ❌ همه در یک دایرکتوری
- ✅ جدا شده به AI, Graph, Datasets, Training, Evaluation, etc.

### 3. Governance Visibility
- ❌ Governance پنهان در monitoring
- ✅ **Governance Center** به عنوان بخش اصلی

### 4. Evaluation Gates
- ❌ Training → Deploy مستقیم
- ✅ Training → Validation → Benchmark → Approval → Deploy

### 5. Graph Explorer
- ❌ فقط Visualization
- ✅ Search + Expand + Explain + Trace + Compare + Timeline

---

## 💡 الهام از سیستم‌های Enterprise

| System | Inspired Feature |
|--------|------------------|
| **Kibana** | Domain-driven dashboards |
| **Grafana** | Role-based access to observability |
| **GitLab** | Integrated governance (CI/CD + Security) |
| **Kubernetes Dashboard** | Workbench for operators |
| **HuggingFace** | Model registry & evaluation |
| **OpenShift** | Multi-role platform architecture |

---

## 🎖️ نتیجه

این معماری:
- ✅ **Role-based**: برای تیم‌های واقعی طراحی شده
- ✅ **Domain-driven**: هر بخش یک مسئولیت واضح
- ✅ **Governance-first**: Governance به عنوان first-class citizen
- ✅ **Scalable**: با رشد تیم و محصول رشد می‌کند
- ✅ **Enterprise-ready**: شبیه محصولات بالغ

**این دیگر فقط یک Frontend نیست - یک Enterprise Platform است!** 🚀

---

## 🤝 آماده برای پیاده‌سازی؟

بگو از کجا شروع کنیم:
1. 🛡️ Governance Center (پیشنهاد من - مهم‌ترین!)
2. 🕸️ Knowledge Graph Explorer  
3. 🤖 AI Studio با Evaluation Gates
4. 📐 Route Restructuring و RBAC

کدوم اولویت اول؟
