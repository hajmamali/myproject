import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@shared/styles/index.css";

// Lazy load USER-facing components ONLY (no developer tools)
const LandingPage = lazy(() => import("@shared/pages/LandingPage"));
const AIChat = lazy(() => import("@shared/components/AIChat"));
const AdvancedDocumentUpload = lazy(() => import("@shared/components/AdvancedDocumentUpload"));
const ContractQA = lazy(() => import("@shared/components/ContractQA"));
const LegalSearchPage = lazy(() => import("@shared/components/LegalSearchPage"));
const ModelSelector = lazy(() => import("@shared/components/ModelSelector"));
const LoginPage = lazy(() => import("@shared/components/auth/LoginPage"));

// Loading fallback
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-950">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700 mx-auto mb-4"></div>
        <p className="text-slate-400">در حال بارگذاری...</p>
      </div>
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  useEffect(() => {
    console.log("📱 MahouN User App loaded - Port 3000");
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/search" element={<LegalSearchPage />} />
            <Route path="/chat" element={<AIChat />} />
            <Route path="/upload" element={<AdvancedDocumentUpload />} />
            <Route path="/contract-qa" element={<ContractQA />} />
            <Route path="/models" element={<ModelSelector />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
