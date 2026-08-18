/**
 * MAHOUN Performance Monitoring Service
 * =====================================
 * 
 * Comprehensive performance monitoring for frontend operations.
 * Tracks metrics, measures performance, and reports to backend.
 * 
 * Constitutional Authority: mahoun/constitutional/constitution/CONSTITUTION.md
 */

export interface PerformanceMetric {
  name: string;
  value: number;
  unit: 'ms' | 'bytes' | 'count' | 'percentage';
  timestamp: string;
  context?: Record<string, any>;
}

export interface PerformanceReport {
  session_id: string;
  metrics: PerformanceMetric[];
  summary: {
    total_metrics: number;
    avg_response_time: number;
    slowest_operation: string;
    error_count: number;
  };
}

class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private sessionId: string;
  private maxMetrics = 1000;
  private flushInterval = 60000; // 1 minute
  private flushTimer: NodeJS.Timeout | null = null;

  constructor() {
    this.sessionId = this.generateSessionId();
    this.startFlushTimer();
    this.initWebVitals();
  }

  /**
   * Generate session ID
   */
  private generateSessionId(): string {
    return `perf_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 11)}`;
  }

  /**
   * Measure execution time of a function
   */
  async measure<T>(
    name: string,
    fn: () => Promise<T>,
    context?: Record<string, any>
  ): Promise<T> {
    const startTime = performance.now();
    try {
      const result = await fn();
      const duration = performance.now() - startTime;
      
      this.recordMetric({
        name,
        value: duration,
        unit: 'ms',
        timestamp: new Date().toISOString(),
        context: { ...context, success: true },
      });

      return result;
    } catch (error) {
      const duration = performance.now() - startTime;
      
      this.recordMetric({
        name,
        value: duration,
        unit: 'ms',
        timestamp: new Date().toISOString(),
        context: { ...context, success: false, error: String(error) },
      });

      throw error;
    }
  }

  /**
   * Record a performance metric
   */
  recordMetric(metric: PerformanceMetric): void {
    this.metrics.push(metric);

    // Trim if exceeds max size
    if (this.metrics.length > this.maxMetrics) {
      this.metrics = this.metrics.slice(-this.maxMetrics);
    }

    // Persist to localStorage
    this.persistToStorage();
  }

  /**
   * Get metrics by name
   */
  getMetrics(name?: string): PerformanceMetric[] {
    if (name) {
      return this.metrics.filter(m => m.name === name);
    }
    return [...this.metrics];
  }

  /**
   * Get performance summary
   */
  getSummary(): PerformanceReport['summary'] {
    const responseTimeMetrics = this.metrics.filter(m => m.unit === 'ms');
    const avgResponseTime = responseTimeMetrics.length > 0
      ? responseTimeMetrics.reduce((sum, m) => sum + m.value, 0) / responseTimeMetrics.length
      : 0;

    const slowest = responseTimeMetrics.length > 0
      ? responseTimeMetrics.reduce((max, m) => m.value > max.value ? m : max)
      : null;

    const errorCount = this.metrics.filter(m => m.context?.success === false).length;

    return {
      total_metrics: this.metrics.length,
      avg_response_time: avgResponseTime,
      slowest_operation: slowest?.name || 'N/A',
      error_count: errorCount,
    };
  }

  /**
   * Get full report
   */
  getReport(): PerformanceReport {
    return {
      session_id: this.sessionId,
      metrics: [...this.metrics],
      summary: this.getSummary(),
    };
  }

  /**
   * Persist to localStorage
   */
  private persistToStorage(): void {
    try {
      localStorage.setItem('mahoun_perf_metrics', JSON.stringify(this.metrics));
    } catch (error) {
      console.error('Failed to persist performance metrics:', error);
    }
  }

  /**
   * Load from localStorage
   */
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem('mahoun_perf_metrics');
      if (stored) {
        this.metrics = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Failed to load performance metrics:', error);
    }
  }

  /**
   * Flush to backend
   */
  private async flushToBackend(): Promise<void> {
    if (this.metrics.length === 0) return;

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      await fetch(`${API_BASE_URL}/api/v1/metrics/performance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.getReport()),
      });

      // Clear after successful flush
      this.metrics = [];
      this.persistToStorage();
    } catch (error) {
      console.error('Failed to flush performance metrics:', error);
    }
  }

  /**
   * Start flush timer
   */
  private startFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      this.flushToBackend();
    }, this.flushInterval);
  }

  /**
   * Stop flush timer
   */
  private stopFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  /**
   * Initialize Web Vitals monitoring
   */
  private initWebVitals(): void {
    if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
      return;
    }

    // Monitor Core Web Vitals
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.recordWebVital(entry);
        }
      });

      observer.observe({ entryTypes: ['navigation', 'resource', 'paint', 'largest-contentful-paint'] });
    } catch (error) {
      console.error('Failed to initialize PerformanceObserver:', error);
    }
  }

  /**
   * Record Web Vitals
   */
  private recordWebVital(entry: PerformanceEntry): void {
    const metric: PerformanceMetric = {
      name: entry.entryType,
      value: entry.duration || entry.startTime,
      unit: 'ms',
      timestamp: new Date().toISOString(),
      context: {
        entry_name: entry.name,
        entry_type: entry.entryType,
      },
    };

    this.recordMetric(metric);
  }

  /**
   * Clear metrics
   */
  clear(): void {
    this.metrics = [];
    this.persistToStorage();
  }

  /**
   * Export metrics
   */
  export(): string {
    return JSON.stringify(this.getReport(), null, 2);
  }
}

// Singleton instance
export const performanceMonitor = new PerformanceMonitor();

/**
 * Hook for using performance monitor in components
 */
export function usePerformanceMonitor() {
  return {
    measure: <T>(name: string, fn: () => Promise<T>, context?: Record<string, any>) =>
      performanceMonitor.measure(name, fn, context),
    recordMetric: (metric: PerformanceMetric) => 
      performanceMonitor.recordMetric(metric),
    getMetrics: (name?: string) => performanceMonitor.getMetrics(name),
    getSummary: () => performanceMonitor.getSummary(),
    getReport: () => performanceMonitor.getReport(),
    clear: () => performanceMonitor.clear(),
    export: () => performanceMonitor.export(),
  };
}

/**
 * Higher-order function to wrap async functions with performance monitoring
 */
export function withPerformanceMonitoring<T extends (...args: any[]) => Promise<any>>(
  name: string,
  fn: T,
  context?: Record<string, any>
): T {
  return (async (...args: Parameters<T>) => {
    return performanceMonitor.measure(name, () => fn(...args), context);
  }) as T;
}
