/**
 * React Error Boundary
 * Catches React errors and displays a fallback UI
 */

import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-800">
          <div className="max-w-md w-full bg-slate-900 rounded-xl shadow-lg border border-slate-700 p-8 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-red-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-slate-100 mb-2">
              خطای غیرمنتظره
            </h2>
            <p className="text-slate-400 mb-4">
              متأسفانه خطایی در برنامه رخ داده است.
            </p>
            {this.state.error && (
              <details className="text-right text-sm text-slate-500 mb-4 p-3 bg-slate-800 rounded-lg">
                <summary className="cursor-pointer font-medium">
                  جزئیات خطا
                </summary>
                <pre className="mt-2 text-xs overflow-auto">
                  {this.state.error.toString()}
                </pre>
              </details>
            )}
            <button
              onClick={() => window.location.reload()}
              className="w-full px-4 py-2 bg-primary-700 text-white rounded-lg hover:bg-primary-800 transition-colors"
            >
              بارگذاری مجدد
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

