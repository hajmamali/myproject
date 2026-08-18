import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@shared/styles/index.css";
import { ProtectedRoute } from "@shared/components/auth/ProtectedRoute";

// Lazy load DEVELOPER tools and monitoring dashboards
const Dashboard = lazy(() => import("@shared/components/Dashboard"));
const DelayAnalysisDashboard = lazy(() => import("@shared/components/DelayAnalysisDashboard"));
const TimelineVisualization = lazy(() => import("@shared/components/TimelineVisualization"));
const TrainingDashboard = lazy(() => import("@shared/components/TrainingDashboard"));
const MonitoringDashboard = lazy(() => import("@shared/components/MonitoringDashboard"));
const ABTestingDashboard = lazy(() => import("@shared/components/ABTestingDashboard"));
const FineTuningDashboard = lazy(() => import("@shared/pages/FineTuningDashboard"));
const GovernanceCenter = lazy(() => import("@shared/pages/GovernanceCenter"));
const KnowledgeGraphCenter = lazy(() => import("@shared/pages/KnowledgeGraphCenter"));
const CaseReviewWorkspace = lazy(() => import("@shared/pages/CaseReviewWorkspace"));
const LoginPage = lazy(() => import("@shared/components/auth/LoginPage"));

// Loading fallback
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-950">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500 mx-auto mb-4"></div>
        <p className="text-slate-400">در حال بارگذاری Developer Console...</p>
      </div>
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 30, // 30 seconds (faster refresh for dev tools)
      refetchOnWindowFocus: true,
    },
  },
});

function App() {
  useEffect(() => {
    console.log("🛠️ MahouN Developer Console loaded - Port 3001");
    console.log("⚠️ WARNING: Developer tools enabled. Do not expose to public internet!");
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            
            {/* Protected Developer Routes */}
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/monitoring" element={<ProtectedRoute><MonitoringDashboard /></ProtectedRoute>} />
            <Route path="/delay-analysis" element={<ProtectedRoute><DelayAnalysisDashboard /></ProtectedRoute>} />
            <Route path="/timeline" element={<ProtectedRoute><TimelineVisualization /></ProtectedRoute>} />
            <Route path="/training" element={<ProtectedRoute><TrainingDashboard /></ProtectedRoute>} />
            <Route path="/ab-testing" element={<ProtectedRoute><ABTestingDashboard /></ProtectedRoute>} />
            <Route path="/fine-tuning" element={<ProtectedRoute><FineTuningDashboard /></ProtectedRoute>} />
            <Route path="/governance" element={<ProtectedRoute><GovernanceCenter /></ProtectedRoute>} />
            <Route path="/knowledge-graph" element={<ProtectedRoute><KnowledgeGraphCenter /></ProtectedRoute>} />
            <Route path="/case-review" element={<ProtectedRoute><CaseReviewWorkspace /></ProtectedRoute>} />
            
            {/* Catch-all redirect to login if not authenticated */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
