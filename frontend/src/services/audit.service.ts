/**
 * MAHOUN Audit Service
 * 
 * Handles all audit-related API communications
 */

import { BaseAPIService } from './api.service';
import { LoggerService } from './logger.service';
import { IdGenerator } from '../utils/id.generator.ts';

export interface AuditEvent {
  id: string;
  timestamp: string;
  user_id: string;
  action: string;
  resource: string;
  outcome: 'success' | 'failure' | 'warning';
  context: Record<string, any>;
  governance_context: {
    request_id: string;
    trace_id: string;
    audit_reference: string;
  };
}

export class AuditService extends BaseAPIService {
  private static instance: AuditService;
  private logger: LoggerService;
  private pendingEvents: AuditEvent[] = [];
  private isOnline: boolean = navigator.onLine;
  
  private constructor() {
    super();
    this.logger = LoggerService.getInstance();
    this.setupOfflineHandling();
  }
  
  public static getInstance(): AuditService {
    if (!AuditService.instance) {
      AuditService.instance = new AuditService();
    }
    return AuditService.instance;
  }
  
  /**
   * Log audit event with offline support
   */
  public async logEvent(event: Omit<AuditEvent, 'id' | 'timestamp'>): Promise<void> {
    const fullEvent: AuditEvent = {
      ...event,
      id: IdGenerator.generate('audit'),
      timestamp: new Date().toISOString(),
    };
    
    try {
      if (this.isOnline) {
        await this.sendEvent(fullEvent);
      } else {
        this.queueEvent(fullEvent);
      }
    } catch (error) {
      this.logger.error('Failed to log audit event', { error, event: fullEvent });
      this.queueEvent(fullEvent); // Queue for retry
    }
  }
  
  /**
   * Send event to backend
   */
  private async sendEvent(event: AuditEvent): Promise<void> {
    await this.request('/api/audit/events', {
      method: 'POST',
      body: JSON.stringify(event),
      headers: {
        'X-Request-ID': IdGenerator.generate('req'),
      },
    });
  }
  
  /**
   * Queue event for offline processing
   */
  private queueEvent(event: AuditEvent): void {
    this.pendingEvents.push(event);
    
    // Store in localStorage for persistence
    try {
      localStorage.setItem('mahoun-audit-queue', JSON.stringify(this.pendingEvents));
    } catch (error) {
      this.logger.error('Failed to queue audit event', { error });
    }
  }
  
  /**
   * Process queued events when back online
   */
  private async processQueue(): Promise<void> {
    if (!this.isOnline || this.pendingEvents.length === 0) return;
    
    const eventsToProcess = [...this.pendingEvents];
    this.pendingEvents = [];
    
    for (const event of eventsToProcess) {
      try {
        await this.sendEvent(event);
      } catch (error) {
        this.logger.error('Failed to process queued audit event', { error, event });
        this.queueEvent(event); // Re-queue on failure
      }
    }
    
    // Update localStorage
    try {
      localStorage.setItem('mahoun-audit-queue', JSON.stringify(this.pendingEvents));
    } catch (error) {
      this.logger.error('Failed to update audit queue', { error });
    }
  }
  
  /**
   * Setup offline/online handling
   */
  private setupOfflineHandling(): void {
    // Load queued events from localStorage
    try {
      const stored = localStorage.getItem('mahoun-audit-queue');
      if (stored) {
        this.pendingEvents = JSON.parse(stored);
      }
    } catch (error) {
      this.logger.error('Failed to load audit queue', { error });
    }
    
    // Listen for online/offline events
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.processQueue();
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }
  
  /**
   * Get queue status
   */
  public getQueueStatus(): { pending: number; isOnline: boolean } {
    return {
      pending: this.pendingEvents.length,
      isOnline: this.isOnline,
    };
  }
}