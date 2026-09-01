/**
 * System Health Dashboard
 * 
 * Real-time monitoring of knowledge graph integrity and model performance
 * Shows live health scores, violations, and system status
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ChartBarIcon,
  ClockIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
  HeartIcon,
  PlayIcon,
  ShieldCheckIcon,
  SparklesIcon,
  XCircleIcon,
  CheckCircleIcon,
  LinkIcon,
  TrendingUpIcon,
} from "@heroicons/react/24/outline";

interface GraphHealth {
  health_score: number;
  status: "healthy" | "degraded" | "critical";
  timestamp: string;
  validation_results: any;
  component_scores: {
    orphaned_nodes: number;
    circular_refs: number;
    hash_integrity: number;
    temporal_consistency: number;
    anomalies: number;
  };
  recommendations: string[];
}

interface ModelPerformance {
  timestamp: string;
  time_window_seconds: number;
  models: Record<string, {
    total_requests: number;
    request_rate: number;
    latency: {
      avg_ms: number;
      p50_ms: number;
      p95_ms: number;
      p99_ms: number;
    };
    errors: {
      total: number;
      rate: number;
    };
    success_rate: number;
    active: boolean;
    health_score: number;
  }>;
}

interface ModelLeaderboard {
  timestamp: string;
  ranking: Array<{
    rank: number;
    model_id: string;
    model_type: string;
    composite_score: number;
    score_breakdown: {
      success_rate_score: number;
      latency_score: number;
      throughput_score: number;
      reliability_score: number;
    };
    metrics: {
      total_requests: number;
      success_rate: number;
      avg_latency_ms: number;
      error_rate: number;
    };
    active: boolean;
  }>;
  total_models: number;
}

interface SystemOverview {
  timestamp: string;
  graph: {
    health_score: number;
    status: string;
    violations: {
      total: number;
      critical: number;
      high: number;
    };
  };
  models: {
    total: number;
    active: number;
    avg_success_rate: number;
    avg_latency_ms: number;
    top_performer: string;
  };
  system: {
    uptime_seconds: number;
    version: string;
  };
}

interface HealthStatus {
  status: "healthy" | "warning" | "critical";
  message: string;
  icon: React.ComponentType<any>;
}

export default function SystemHealthDashboard() {
  const [graphHealth, setGraphHealth] = useState<GraphHealth | null>(null);
  const [modelPerformance, setModelPerformance] = useState<ModelPerformance | null>(null);
  const [modelLeaderboard, setModelLeaderboard] = useState<ModelLeaderboard | null>(null);
  const [systemOverview, setSystemOverview] = useState<SystemOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);
  const navigate = useNavigate();

  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // Fetch all health data
  const fetchHealthData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch graph health
      const graphResponse = await fetch(`${API_BASE_URL}/monitoring/graph/health`);
      if (!graphResponse.ok) {
        throw new Error(`Graph health failed: ${graphResponse.status}`);
      }
      const graphData: GraphHealth = await graphResponse.json();
      setGraphHealth(graphData);

      // Fetch model performance
      const perfResponse = await fetch(`${API_BASE_URL}/monitoring/models/performance`);
      if (!perfResponse.ok) {
        throw new Error(`Model performance failed: ${perfResponse.status}`);
      }
      const perfData: ModelPerformance = await perfResponse.json();
      setModelPerformance(perfData);

      // Fetch model leaderboard
      const leaderboardResponse = await fetch(`${API_BASE_URL}/monitoring/models/leaderboard`);
      if (!leaderboardResponse.ok) {
        throw new Error(`Model leaderboard failed: ${leaderboardResponse.status}`);
      }
      const leaderboardData: ModelLeaderboard = await leaderboardResponse.json();
      setModelLeaderboard(leaderboardData);

      // Fetch system overview
      const overviewResponse = await fetch(`${API_BASE_URL}/monitoring/system/overview`);
      if (!overviewResponse.ok) {
        throw new Error(`System overview failed: ${overviewResponse.status}`);
      }
      const overviewData: SystemOverview = await overviewResponse.json();
      setSystemOverview(overviewData);
    } catch (err) {
      console.error("Failed to fetch health data:", err);
      setError(err instanceof Error ? err.message : "Error loading health data");
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchHealthData();
    
    // Set up refresh interval (every 30 seconds)
    const interval = setInterval(fetchHealthData, 30000);
    setRefreshInterval(interval);
    
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  }, []);

  // Get health status based on scores
  const getGraphStatus = (score: number): HealthStatus => {
    if (score >= 90) {
      return {
        status: "healthy",
        message: "Graph is healthy",
        icon: CheckCircleIcon
      };
    } else if (score >= 70) {
      return {
        status: "warning",
        message: "Graph needs review",
        icon: WarningIcon
      };
    } else {
      return {
        status: "critical",
        message: "Graph has critical issues",
        icon: ExclamationTriangleIcon
      };
    }
  };

  const getModelStatus = (score: number): HealthStatus => {
    if (score >= 85) {
      return {
        status: "healthy",
        message: "Model performing well",
        icon: CheckCircleIcon
      };
    } else if (score >= 60) {
      return {
        status: "warning",
        message: "Model needs review",
        icon: WarningIcon
      };
    } else {
      return {
        status: "critical",
        message: "Model performing poorly",
        icon: ExclamationTriangleIcon
      };
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-red-50">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 flex items-center justify-center bg-red-200 rounded-full">
            <XCircleIcon className="h-8 w-8 text-red-600" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-red-800">Error Loading Data</h2>
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <button 
            onClick={() => fetchHealthData()}
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Calculate average model health score
  const avgModelHealth = modelPerformance !== null ? 
    Object.values(modelPerformance.models).reduce((avg, m) => avg + m.health_score, 0) / 
    Math.max(Object.keys(modelPerformance.models).length, 1) : 0;

  const graphStatus = graphHealth ? getGraphStatus(graphHealth.health_score) : null;
  const modelStatus = getModelStatus(avgModelHealth);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
                <HeartIcon className="h-6 w-6 text-indigo-600" />
                System Health Dashboard
              </h1>
              <p className="mt-1 text-sm text-slate-600">
                Real-time monitoring of knowledge graph and model performance
              </p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => fetchHealthData()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <ClockIcon className="h-4 w-4" /> Refresh
              </button>
              <button
                onClick={() => navigate("/")}
                className="px-4 py-2 bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300 transition-colors"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Status Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6 mb-8">
          {/* Graph Health Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              {graphStatus ? (
                graphStatus.icon
              ) : (
                <ClockIcon className="h-6 w-6 text-slate-500" />
              )}
              <h3 className="text-lg font-medium text-slate-800">Graph Health</h3>
            </div>
            <div className="text-3xl font-bold text-slate-900 mb-2">
              {graphHealth !== null ? `${graphHealth.health_score.toFixed(1)}%` : "--"}
            </div>
            <p className="text-sm text-slate-600">
              {graphHealth ? graphStatus?.message : "Loading..."}
            </p>
            
            {/* Mini progress bar */}
            {graphHealth !== null && (
              <div className="w-full bg-slate-200 rounded-full h-2.5 mt-2">
                <div
                  className={`${graphStatus?.status === "healthy" ? "bg-green-600" : graphStatus?.status === "warning" ? "bg-yellow-600" : "bg-red-600"} h-2.5 rounded-full transition-all duration-300`}
                  style={{ width: `${Math.min(graphHealth.health_score, 100)}%` }}
                ></div>
              </div>
            )}
          </div>

          {/* Model Performance Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
<div className="flex items-center gap-3 mb-4">
              <ChartBarIcon className="h-6 w-6 text-indigo-600" />
              <h3 className="text-lg font-medium text-slate-800">Model Performance</h3>
            </div>
            <div className="text-3xl font-bold text-slate-900 mb-2">
              {avgModelHealth.toFixed(1)}%
            </div>
            <p className="text-sm text-slate-600">
              {modelPerformance !== null ? modelStatus.message : "Loading..."}
            </p>
            
            {/* Mini progress bar */}
            {modelPerformance !== null && (
              <div className="w-full bg-slate-200 rounded-full h-2.5 mt-2">
                <div
                  className={`${modelStatus.status === "healthy" ? "bg-green-600" : modelStatus.status === "warning" ? "bg-yellow-600" : "bg-red-600"} h-2.5 rounded-full transition-all duration-300`}
                  style={{ width: `${Math.min(avgModelHealth, 100)}%` }}
                ></div>
              </div>
            )}
          </div>

          {/* System Uptime Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <ClockIcon className="h-6 w-6 text-indigo-600" />
              <h3 className="text-lg font-medium text-slate-800">System Uptime</h3>
            </div>
            <div className="text-3xl font-bold text-slate-900 mb-2">
              {systemOverview !== null ? 
                `${Math.floor(systemOverview.system.uptime_seconds / 86400)}d ${Math.floor((systemOverview.system.uptime_seconds % 86400) / 3600)}h` : 
                "--"
              }
            </div>
            <p className="text-sm text-slate-600">
              {systemOverview !== null ? 
                `Started: ${new Date(Date.now() - systemOverview.system.uptime_seconds * 1000).toLocaleString("fa-IR")}` : 
                "Loading..."
              }
            </p>
          </div>

          {/* Active Violations Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              {systemOverview !== null && systemOverview.graph.violations.critical > 0 ? (
                <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
              ) : systemOverview !== null && systemOverview.graph.violations.high > 0 ? (
                <ExclamationTriangleIcon className="h-6 w-6 text-amber-600" />
              ) : (
                <CheckCircleIcon className="h-6 w-6 text-green-600" />
              )}
              <h3 className="text-lg font-medium text-slate-800">Graph Violations</h3>
            </div>
            <div className="text-3xl font-bold text-slate-900 mb-2">
              {systemOverview !== null ? 
                `${systemOverview.graph.violations.total}` : 
                "--"
              }
            </div>
            <p className="text-sm text-slate-600">
              {systemOverview !== null ? 
                `${systemOverview.graph.violations.critical} critical, ${systemOverview.graph.violations.high} high` : 
                "Loading..."
              }
            </p>
          </div>
        </div>

        {/* Detailed Sections */}
        <div className="space-y-8">
          {/* Graph Health Details */}
          {graphHealth && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200">
              <div className="p-6 border-b border-slate-200">
                <h2 className="text-lg font-medium text-slate-900 flex items-center gap-3">
                  <ShieldCheckIcon className="h-5 w-5 text-indigo-600" />
                  Graph Health Breakdown
                </h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
                {[
                  { label: "Orphaned Nodes", value: graphHealth.component_scores.orphaned_nodes, icon: ChartBarIcon, color: "bg-blue-500" },
                  { label: "Circular Refs", value: graphHealth.component_scores.circular_refs, icon: ExclamationTriangleIcon, color: "bg-red-500" },
                  { label: "Hash Integrity", value: graphHealth.component_scores.hash_integrity, icon: LinkIcon, color: "bg-green-500" },
                  { label: "Temporal Consistency", value: graphHealth.component_scores.temporal_consistency, icon: ClockIcon, color: "bg-purple-500" },
                  { label: "Anomalies", value: graphHealth.component_scores.anomalies, icon: SparklesIcon, color: "bg-yellow-500" },
                ].map((item, index) => (
                  <div key={index} className="bg-slate-50 rounded-lg p-4 text-center">
                    <div className="flex items-center justify-center mb-3">
                      <div className={`${item.color} p-2 rounded-full`}>
                        <item.icon className="h-4 w-4 text-white" />
                      </div>
                    </div>
                    <div className="text-2xl font-bold text-slate-900">{item.value.toFixed(1)}%</div>
                    <p className="text-sm text-slate-600">{item.label}</p>
                  </div>
                ))}
              </div>
              
              {/* Recommendations */}
              {graphHealth.recommendations.length > 0 && (
                <div className="p-6 pt-4 border-t border-slate-200">
                  <h3 className="text-lg font-medium text-slate-900 mb-4">Recommendations</h3>
                  <div className="space-y-3">
                    {graphHealth.recommendations.map((rec, index) => (
                      <div key={index} className="bg-slate-50 rounded-lg p-4">
                        <p className="text-sm text-slate-700">
                          {rec}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Model Performance Details */}
          {modelPerformance && modelLeaderboard && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200">
              <div className="p-6 border-b border-slate-200">
                <h2 className="text-lg font-medium text-slate-900 flex items-center gap-3">
                  <TrendingUpIcon className="h-5 w-5 text-indigo-600" />
                  Model Performance & Leaderboard
                </h2>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  {/* Model Leaderboard */}
                  <div>
                    <h3 className="text-md font-medium text-slate-900 mb-3">Model Leaderboard (Composite Score)</h3>
                    <div className="overflow-y-auto max-h-64 border border-slate-200 rounded-lg">
                      {modelLeaderboard.ranking.map((model) => (
                        <div key={model.rank} className="p-3 border-b border-slate-100 last:border-0 flex items-center justify-between">
                          <div className="flex-1 text-right">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-slate-900">#{model.rank}</span>
                              <span className="ml-2 text-indigo-600 font-medium">{model.model_id.split('/').pop() || model.model_id}</span>
                            </div>
                          </div>
                          <div className="text-slate-600 space-y-1">
                            <div className="text-sm font-medium">Score: {model.composite_score.toFixed(1)}%</div>
                            <div className="text-xs">Type: {model.model_type} | Requests: {model.metrics.total_requests.toLocaleString()} | Latency: {model.metrics.avg_latency_ms.toFixed(1)}ms</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {/* Overall Model Stats */}
                  <div className="mt-4">
                    <h3 className="text-md font-medium text-slate-900 mb-3">Model Overview</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-sm text-slate-600">
                        <p><span className="font-medium">Total Models:</span> {modelLeaderboard.total_models}</p>
                        <p><span className="font-medium">Active Models:</span> {Object.values(modelPerformance.models).filter(m => m.active).length}</p>
                        <p><span className="font-medium">Avg Success Rate:</span> {Object.values(modelPerformance.models).reduce((avg, m) => avg + m.success_rate, 0) / Math.max(Object.keys(modelPerformance.models).length, 1).toFixed(1)}%</p>
                        <p><span className="font-medium">Avg Latency:</span> {Object.values(modelPerformance.models).reduce((avg, m) => avg + m.latency.avg_ms, 0) / Math.max(Object.keys(modelPerformance.models).length, 1).toFixed(1)}ms</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* System Overview Details */}
          {systemOverview && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200">
              <div className="p-6 border-b border-slate-200">
                <h2 className="text-lg font-medium text-slate-900 flex items-center gap-3">
                  <ChartBarIcon className="h-5 w-5 text-indigo-600" />
                  System Overview
                </h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Left Column - Graph Info */}
                  <div>
                    <h3 className="text-md font-medium text-slate-900 mb-3">Graph Information</h3>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Status:</span>
                        <span className={`${systemOverview.graph.status === "healthy" ? "text-green-600" : systemOverview.graph.status === "degraded" ? "text-yellow-600" : "text-red-600"} font-medium`}>
                          {systemOverview.graph.status === "healthy" ? "Healthy" : systemOverview.graph.status === "degraded" ? "Degraded" : "Critical"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Last Check:</span>
                        <span className="text-xs text-slate-500">{new Date(systemOverview.timestamp).toLocaleTimeString("fa-IR")}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Health Score:</span>
                        <span className="text-lg font-bold text-slate-900">{systemOverview.graph.health_score.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Right Column - Models & System Info */}
                  <div>
                    <h3 className="text-md font-medium text-slate-900 mb-3">Models & System Info</h3>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Active Models:</span>
                        <span className="text-md font-bold text-slate-900">{systemOverview.models.active}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Avg Success Rate:</span>
                        <span className="text-md font-bold text-slate-900">{systemOverview.models.avg_success_rate.toFixed(1)}%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Avg Latency (ms):</span>
                        <span className="text-md font-bold text-slate-900">{systemOverview.models.avg_latency_ms.toFixed(1)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Top Performer:</span>
                        <span className="text-md font-bold text-slate-900">{systemOverview.models.top_performer}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">System Version:</span>
                        <span className="text-md font-bold text-slate-900">{systemOverview.system.version}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Uptime:</span>
                        <span className="text-md font-bold text-slate-900">{Math.floor(systemOverview.system.uptime_seconds / 86400)}d {Math.floor((systemOverview.system.uptime_seconds % 86400) / 3600)}h {Math.floor((systemOverview.system.uptime_seconds % 3600) % 60)}m</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}