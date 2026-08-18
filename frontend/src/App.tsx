import { lazy, Suspense, useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  AppErrorBoundary,
  errorService,
  initErrorService,
  setupGlobalErrorHandlers,
  ToastContainer,
  registerToastContainer,
} from "./shared/errors";
import CommandPalette from "./components/CommandPalette";
import AppLayout from "./components/AppLayout";
import StudioLayout from "./components/StudioLayout";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import LoginPage from "./components/auth/LoginPage";
import { useAuth, Permission, Role } from "./store/authStore";
import { useGovernanceStore } from "./store/governanceStore";

// Lazy load components for code splitting with governance integration
const LandingPage = lazy(() => import("./pages/LandingPage"));
const AIChat = lazy(() => import("./components/AIChat"));
const Dashboard = lazy(() => import("./components/Dashboard"));
const AdvancedDocumentUpload = lazy(() => import("./components/AdvancedDocumentUpload"));
const DelayAnalysisDashboard = lazy(() => import("./components/DelayAnalysisDashboard"));
const TimelineVisualization = lazy(() => import("./components/TimelineVisualization"));
const ContractQA = lazy(() => import("./components/ContractQA"));
const LegalSearchPage = lazy(() => import("./components/LegalSearchPage"));
const ModelSelector = lazy(() => import("./components/ModelSelector"));
const TrainingDashboard = lazy(() => import("./components/TrainingDashboard"));
const MonitoringDashboard = lazy(() => import("./components/MonitoringDashboard"));
const ABTestingDashboard = lazy(() => import("./components/ABTestingDashboard"));
const FineTuningDashboard = lazy(() => import("./pages/FineTuningDashboard"));
const KnowledgeGraphCenter = lazy(() => import("./pages/KnowledgeGraphCenter"));

// Governance Center - The heart of MahouN!
const GovernanceCenter = lazy(() => import("./pages/GovernanceCenter"));
const AuditCenter = lazy(() => import("./components/AuditCenter"));
const FailClosedMonitor = lazy(() => import("./components/FailClosedMonitor"));
const MutationAuthorization = lazy(() => import("./components/MutationAuthorization"));
const DatasetBrowser = lazy(() => import("./components/DatasetBrowser"));
const DatasetUploader = lazy(() => import("./components/DatasetUploader"));

// 🔍 Investigator Tools - Economic Crimes Branch Features
const SuspiciousPatternDetector = lazy(() => import("./components/SuspiciousPatternDetector"));
const AutoInformationExtractor = lazy(() => import("./components/AutoInformationExtractor"));

// Create React Query client with governance integration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // Add governance context to all queries
      meta: {
        governance: true,
      },
    },
    mutations: {
      // Add governance context to all mutations
      meta: {
        governance: true,
      },
    },
  },
});

// Enhanced loading fallback with governance context
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-950">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700 mx-auto mb-4"></div>
        <p className="text-slate-400">بارگذاری سیستم ماحون...</p>
      </div>
    </div>
  );
}

// Authentication provider wrapper
function AuthProvider({ children }: { children: React.ReactNode }) {
  const { validateSession, logUserAction } = useAuth();
  const { validateConstitutionalCompliance } = useGovernanceStore();

  useEffect(() => {
    // Initialize governance validation
    validateConstitutionalCompliance();
    
    // Set up session validation interval
    const interval = setInterval(() => {
      validateSession();
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Log application startup
    logUserAction('app_startup', {
      timestamp: new Date().toISOString(),
      user_agent: navigator.userAgent,
      screen_resolution: `${screen.width}x${screen.height}`,
    });
  }, []);

  return <>{children}</>;
}


function App() {
  // const commandPalette = useCommandPalette();

  // Initialize error handling service
  useEffect(() => {
    initErrorService({
      logToConsole: import.meta.env.DEV,
      reportToTrackingService: import.meta.env.PROD,
      showDetailsInDevelopment: import.meta.env.DEV,
    });
    
    setupGlobalErrorHandlers();
    
    // Set governance context for error tracking
    const governanceContext = {
      request_id: crypto.randomUUID(),
      trace_id: crypto.randomUUID(),
      audit_reference: `audit_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`,
    };
    errorService.setGovernanceContext(governanceContext);
    
    // Initialize Sentry if DSN is available
    if (import.meta.env.VITE_SENTRY_DSN) {
      errorService.initSentry({
        dsn: import.meta.env.VITE_SENTRY_DSN,
        environment: import.meta.env.MODE || 'development',
        tracesSampleRate: 1.0,
        replaySessionSampleRate: 0.1,
        release: `mahoun@${import.meta.env.VITE_VERSION || '1.0.0'}`,
        dist: 'frontend',
      });
    }
  }, []);

  // Toast container reference
  const toastContainerRef = useRef<{
    addToast: (toast: any) => string;
    dismissToast: (id: string) => void;
    clearToasts: () => void;
  }>(null);

  // Register toast container
  useEffect(() => {
    if (toastContainerRef.current) {
      registerToastContainer(toastContainerRef.current);
    }
  }, []);

  return (
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <CommandPalette />
            <ToastContainer ref={toastContainerRef} position="top-right" maxToasts={5} />
            <Suspense fallback={<LoadingFallback />}>
              <Routes>
                {/* Public Landing Page */}
                <Route path="/" element={<LandingPage />} />
                
                {/* Authentication Routes */}
                <Route path="/login" element={<LoginPage />} />
                
                {/* Protected Application Routes */}
                <Route path="/app" element={<Navigate to="/app/portal/dashboard" replace />} />
                
                {/* 1. User Portal Workspace */}
                <Route path="/app/portal" element={
                  <ProtectedRoute requireAuth={true}>
                    <AppLayout />
                  </ProtectedRoute>
                }>
                  <Route index element={<Navigate to="/app/portal/dashboard" replace />} />
                  
                  {/* Dashboard - Basic read access */}
                  <Route 
                    path="dashboard" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <Dashboard />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* AI Chat - Read access */}
                  <Route 
                    path="chat" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <AIChat />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* Document Upload - Write access required */}
                  <Route 
                    path="upload" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ, Permission.WRITE]}>
                        <AdvancedDocumentUpload />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* Legal Search - Read access */}
                  <Route 
                    path="search" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <LegalSearchPage />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* Analysis Tools */}
                  <Route 
                    path="delay" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <DelayAnalysisDashboard />
                      </ProtectedRoute>
                    } 
                  />
                  
                  <Route 
                    path="timeline" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <TimelineVisualization />
                      </ProtectedRoute>
                    } 
                  />
                  
                  <Route 
                    path="contract-qa" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <ContractQA />
                      </ProtectedRoute>
                    } 
                  />
                </Route>

                {/* 2. Operations / Engineer Workbench (Studio) */}
                <Route path="/app/studio" element={
                  <ProtectedRoute requireAuth={true} requiredRoles={[Role.ANALYST, Role.ADMIN]}>
                    <StudioLayout />
                  </ProtectedRoute>
                }>
                  <Route index element={<Navigate to="/app/studio/graph" replace />} />
                  
                  {/* Knowledge Graph Center */}
                  <Route 
                    path="graph" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <KnowledgeGraphCenter />
                      </ProtectedRoute>
                    } 
                  />

                  {/* Dataset Engineering */}
                  <Route 
                    path="datasets" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <DatasetBrowser />
                      </ProtectedRoute>
                    } 
                  />
                  
                  <Route 
                    path="datasets/upload" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.WRITE]}>
                        <DatasetUploader />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* Model Management */}
                  <Route 
                    path="models" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.ADMIN]}>
                        <ModelSelector onSelect={() => {}} />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* AI Training */}
                  <Route 
                    path="training" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.ADMIN]}>
                        <TrainingDashboard onStartTraining={() => undefined} />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* Fine-Tuning */}
                  <Route 
                    path="finetuning" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.ADMIN]}>
                        <FineTuningDashboard />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* System Monitor */}
                  <Route 
                    path="monitoring" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <MonitoringDashboard />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* A/B Testing */}
                  <Route 
                    path="experiments" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.ADMIN]}>
                        <ABTestingDashboard />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* Governance Center */}
                  <Route 
                    path="governance" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <GovernanceCenter />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* Governance Sub-routes */}
                  <Route 
                    path="governance/audit" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <AuditCenter />
                      </ProtectedRoute>
                    } 
                  />
                  
                  <Route 
                    path="governance/fail-closed" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <FailClosedMonitor />
                      </ProtectedRoute>
                    } 
                  />
                  
                  <Route 
                    path="governance/mutations" 
                    element={
                      <ProtectedRoute requiredPermissions={[Permission.READ]}>
                        <MutationAuthorization />
                      </ProtectedRoute>
                    } 
                  />
                </Route>
                
                {/* Fallback for unknown routes */}
                <Route path="*" element={<Navigate to="/app/portal/dashboard" replace />} />
              </Routes>
            </Suspense>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </AppErrorBoundary>
  );
}

export default App;
