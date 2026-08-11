/**
 * MAHOUN Logger Service
 * 
 * Centralized logging with levels and remote reporting
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'critical';

export interface LogEntry {
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
  timestamp: string;
  source: string;
}

export class LoggerService {
  private static instance: LoggerService;
  private isProduction: boolean = import.meta.env.PROD;
  private logBuffer: LogEntry[] = [];
  private readonly maxBufferSize = 100;
  
  private constructor() {
    // Setup global error handling
    this.setupGlobalErrorHandling();
  }
  
  public static getInstance(): LoggerService {
    if (!LoggerService.instance) {
      LoggerService.instance = new LoggerService();
    }
    return LoggerService.instance;
  }
  
  public debug(message: string, context?: Record<string, any>): void {
    this.log('debug', message, context);
  }
  
  public info(message: string, context?: Record<string, any>): void {
    this.log('info', message, context);
  }
  
  public warn(message: string, context?: Record<string, any>): void {
    this.log('warn', message, context);
  }
  
  public error(message: string, context?: Record<string, any>): void {
    this.log('error', message, context);
  }
  
  public critical(message: string, context?: Record<string, any>): void {
    this.log('critical', message, context);
  }
  
  private log(level: LogLevel, message: string, context?: Record<string, any>): void {
    const entry: LogEntry = {
      level,
      message,
      context,
      timestamp: new Date().toISOString(),
      source: 'frontend',
    };
    
    // Add to buffer
    this.addToBuffer(entry);
    
    // Console output (only in development or for critical errors)
    if (!this.isProduction || level === 'critical') {
      this.consoleOutput(entry);
    }
    
    // Send to backend for error and critical levels
    if (level === 'error' || level === 'critical') {
      this.sendToBackend(entry).catch(() => {
        // Fallback to console if backend fails
        console.error('Failed to send log to backend:', entry);
      });
    }
  }
  
  private addToBuffer(entry: LogEntry): void {
    this.logBuffer.push(entry);
    
    // Keep buffer size manageable
    if (this.logBuffer.length > this.maxBufferSize) {
      this.logBuffer.shift();
    }
  }
  
  private consoleOutput(entry: LogEntry): void {
    const { level, message, context } = entry;
    const logMethod = level === 'critical' ? 'error' : level;
    
    if (context) {
      console[logMethod](`[${level.toUpperCase()}] ${message}`, context);
    } else {
      console[logMethod](`[${level.toUpperCase()}] ${message}`);
    }
  }
  
  private async sendToBackend(entry: LogEntry): Promise<void> {
    try {
      const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      await fetch(`${baseURL}/api/logs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry),
      });
    } catch (error) {
      // Silently fail for logging - avoid infinite loops
    }
  }
  
  private setupGlobalErrorHandling(): void {
    // Catch unhandled errors
    window.addEventListener('error', (event) => {
      this.error('Unhandled JavaScript error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack,
      });
    });
    
    // Catch unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.error('Unhandled promise rejection', {
        reason: event.reason,
        promise: 'Promise rejected',
      });
    });
  }
  
  /**
   * Get recent logs for debugging
   */
  public getRecentLogs(count: number = 50): LogEntry[] {
    return this.logBuffer.slice(-count);
  }
  
  /**
   * Clear log buffer
   */
  public clearLogs(): void {
    this.logBuffer = [];
  }
}