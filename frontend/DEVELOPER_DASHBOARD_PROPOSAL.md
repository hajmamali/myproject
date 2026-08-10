# MahouN Frontend - Developer Dashboard Proposal

## مشکل فعلی
فرانت‌اند فعلی همه چیز در یک interface داره:
- کاربران عادی با developer tools درهم
- UI شلوغ و پیچیده
- دسترسی‌های مختلف در یک مکان

## پیشنهاد: جداسازی Developer از User Interface

### 1. ساختار جدید

```
/app/
├── user/                    # کاربران عادی
│   ├── dashboard           # داشبورد اصلی
│   ├── search             # جستجوی قانونی
│   ├── chat               # AI Chat
│   ├── documents          # مدیریت اسناد
│   └── analysis           # تحلیل‌های آماده
│
└── developer/              # بخش توسعه‌دهندگان
    ├── fine-tuning        # فاین تیونینگ مدل‌ها
    ├── knowledge-graph    # ساخت گراف دانش
    ├── model-training     # آموزش مدل
    ├── experiments        # A/B Testing
    ├── monitoring         # نظارت سیستم
    └── data-pipeline      # پایپلاین داده
```

### 2. کامپوننت‌های پیشنهادی

#### A) Knowledge Graph Builder Panel

```typescript
interface GraphBuilderProps {
  // Document input
  documents: Document[];
  
  // Graph configuration
  extractionConfig: {
    enableEntityExtraction: boolean;
    enableRelationExtraction: boolean;
    confidenceThreshold: number;
  };
  
  // Visualization
  graphVisualization: {
    layout: 'force-directed' | 'hierarchical' | 'circular';
    nodeTypes: string[];
    edgeTypes: string[];
  };
}

const KnowledgeGraphBuilder: React.FC<GraphBuilderProps> = ({
  documents,
  extractionConfig,
  graphVisualization
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Document Input Panel */}
      <div className="space-y-4">
        <DocumentUploader onUpload={handleDocumentUpload} />
        <DocumentList documents={documents} />
        <ExtractionSettings config={extractionConfig} />
      </div>
      
      {/* Graph Builder */}
      <div className="lg:col-span-2">
        <GraphCanvas 
          nodes={graphData.nodes}
          edges={graphData.edges}
          layout={graphVisualization.layout}
          onNodeClick={handleNodeClick}
          onEdgeClick={handleEdgeClick}
        />
        
        <GraphControls
          onBuild={handleGraphBuild}
          onExport={handleGraphExport}
          onValidate={handleGraphValidate}
        />
      </div>
      
      {/* Graph Statistics */}
      <div className="lg:col-span-3">
        <GraphMetrics 
          totalNodes={graphMetrics.totalNodes}
          totalEdges={graphMetrics.totalEdges}
          entityTypes={graphMetrics.entityTypes}
          confidence={graphMetrics.averageConfidence}
        />
      </div>
    </div>
  );
};
```

#### B) Fine-Tuning Dashboard

```typescript
const FineTuningDashboard: React.FC = () => {
  const [trainingJobs, setTrainingJobs] = useState<TrainingJob[]>([]);
  const [selectedModel, setSelectedModel] = useState<ModelOption | null>(null);
  
  return (
    <div className="space-y-6">
      {/* Model Selection */}
      <ModelSelectionPanel 
        onModelSelect={setSelectedModel}
        baseModels={availableModels}
      />
      
      {/* Training Configuration */}
      <TrainingConfigPanel
        model={selectedModel}
        onConfigUpdate={handleConfigUpdate}
        config={{
          batchSize: 4,
          learningRate: 2e-4,
          epochs: 3,
          loraRank: 16,
          loraAlpha: 32,
        }}
      />
      
      {/* Dataset Management */}
      <DatasetPanel
        onDatasetUpload={handleDatasetUpload}
        onDatasetGenerate={handleDatasetGenerate}
        datasets={availableDatasets}
      />
      
      {/* Training Jobs */}
      <TrainingJobsPanel
        jobs={trainingJobs}
        onJobStart={handleJobStart}
        onJobStop={handleJobStop}
        onJobMonitor={handleJobMonitor}
      />
      
      {/* Model Registry */}
      <ModelRegistryPanel
        trainedModels={trainedModels}
        onModelDeploy={handleModelDeploy}
        onModelEvaluate={handleModelEvaluate}
      />
    </div>
  );
};
```

#### C) Developer Navigation

```typescript
const DeveloperLayout: React.FC = ({ children }) => {
  const navigate = useNavigate();
  
  const developerMenuItems = [
    {
      id: 'fine-tuning',
      label: 'Fine-Tuning',
      icon: <AdjustmentsHorizontalIcon />,
      path: '/app/developer/fine-tuning',
      description: 'آموزش و فاین‌تیونینگ مدل‌ها',
    },
    {
      id: 'knowledge-graph',
      label: 'Knowledge Graph',
      icon: <ShareIcon />,
      path: '/app/developer/knowledge-graph',
      description: 'ساخت و مدیریت گراف دانش',
    },
    {
      id: 'experiments',
      label: 'A/B Testing', 
      icon: <BeakerIcon />,
      path: '/app/developer/experiments',
      description: 'آزمایش‌های A/B و مقایسه مدل‌ها',
    },
    {
      id: 'monitoring',
      label: 'System Monitor',
      icon: <ChartBarIcon />,
      path: '/app/developer/monitoring', 
      description: 'نظارت و متریک‌های سیستم',
    },
    {
      id: 'data-pipeline',
      label: 'Data Pipeline',
      icon: <Cog6ToothIcon />,
      path: '/app/developer/data-pipeline',
      description: 'پایپلاین پردازش داده',
    },
  ];
  
  return (
    <div className="flex h-screen bg-gray-900">
      {/* Developer Sidebar */}
      <aside className="w-64 bg-gray-800 border-r border-gray-700">
        <div className="p-6">
          <h2 className="text-xl font-bold text-white mb-6">
            🛠️ Developer Tools
          </h2>
          
          <nav className="space-y-2">
            {developerMenuItems.map((item) => (
              <button
                key={item.id}
                onClick={() => navigate(item.path)}
                className="w-full flex items-center gap-3 p-3 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              >
                <span className="w-5 h-5">{item.icon}</span>
                <div className="text-right flex-1">
                  <div className="font-medium">{item.label}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {item.description}
                  </div>
                </div>
              </button>
            ))}
          </nav>
        </div>
        
        {/* Switch to User Mode */}
        <div className="absolute bottom-6 left-6 right-6">
          <button
            onClick={() => navigate('/app/user/dashboard')}
            className="w-full flex items-center gap-2 p-3 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors border border-gray-600"
          >
            <UserIcon className="w-4 h-4" />
            <span>حالت کاربری</span>
          </button>
        </div>
      </aside>
      
      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
};
```

### 3. API Endpoints موجود

Backend قبلا این endpoint ها رو داره:

```typescript
// Fine-tuning APIs - موجود در backend
POST /api/v1/finetuning/jobs
GET  /api/v1/finetuning/jobs/:id
POST /api/v1/finetuning/datasets
GET  /api/v1/finetuning/models

// Graph building APIs - موجود در backend  
POST /api/v1/graph/build
GET  /api/v1/graph/nodes
POST /api/v1/graph/extract-entities
GET  /api/v1/graph/metrics

// Model management - موجود در backend
GET  /api/v1/models
POST /api/v1/models/register
GET  /api/v1/models/:id/health
```

### 4. پیاده‌سازی مرحله‌ای

#### مرحله 1: جداسازی Route ها (1 روز)
- تغییر App.tsx برای جداسازی `/app/user/` و `/app/developer/`
- ایجاد Layout های جداگانه

#### مرحله 2: Knowledge Graph Builder (3 روز)  
- کامپوننت آپلود سند
- نمایش گراف interactive با D3.js یا Cytoscape
- اتصال به backend graph APIs

#### مرحله 3: Fine-tuning Panel (2 روز)
- Dashboard مدیریت training jobs  
- کانفیگ پارامترهای فاین‌تیونینگ
- نمایش progress و metrics

#### مرحله 4: Developer Tools (2 روز)
- Data pipeline monitor
- System health dashboard  
- Performance metrics

### 5. مزایای جداسازی

✅ **UX بهتر**: کاربران عادی UI ساده‌تر دارن  
✅ **Developer Experience**: ابزارهای تخصصی در یک مکان  
✅ **Scalability**: اضافه کردن features جدید آسان‌تر  
✅ **Security**: دسترسی‌های جداگانه برای هر بخش  
✅ **Performance**: Code splitting بهتر و load time کمتر  

## نظرتون چیه؟ بریم پیاده‌سازی کنیم؟ 🚀