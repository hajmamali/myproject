import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ErrorBoundary from "./components/ErrorBoundary";
import { ToastContainer } from "./components/Toast";
import AppLayout from "./components/AppLayout";

// Lazy load components for code splitting
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

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});


// Loading fallback component
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700"></div>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ToastContainer />
          <Suspense fallback={<LoadingFallback />}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="upload" element={<AdvancedDocumentUpload />} />
                <Route path="delay" element={<DelayAnalysisDashboard />} />
                <Route path="timeline" element={<TimelineVisualization />} />
                <Route path="contract-qa" element={<ContractQA />} />
                <Route path="search" element={<LegalSearchPage />} />
                <Route path="models" element={<ModelSelector onSelect={() => {}} />} />
                <Route path="training" element={<TrainingDashboard onStartTraining={async () => {}} />} />
                <Route path="finetuning" element={<FineTuningDashboard />} />
                <Route path="monitoring" element={<MonitoringDashboard />} />
                <Route path="experiments" element={<ABTestingDashboard />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
