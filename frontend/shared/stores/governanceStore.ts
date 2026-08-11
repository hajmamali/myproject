/**
 * MAHOUN Governance Store
 * 
 * Comprehensive governance state management with:
 * - Constitutional compliance tracking
 * - Audit event logging
 * - Policy enforcement
 * - Error tracking and recovery
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Types
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

export interface PolicyViolation {
  id: string;
  timestamp: string;
  policy_id: string;
  violation_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  details: string;
  context: Record<string, any>;
}

export interface ConstitutionalCompliance {
  framework_version: string;
  compliance_level: 'compliant' | 'warning' | 'violation';
  last_check: string;
  violations: PolicyViolation[];
}

export interface GovernanceState {
  // Audit Tracking
  auditEvents: AuditEvent[];
  pendingAudits: number;
  
  // Policy Enforcement
  activePolicies: string[];
  policyViolations: PolicyViolation[];
  
  // Constitutional Compliance
  constitutionalCompliance: ConstitutionalCompliance;
  
  // Error Tracking
  errorEvents: Array<{
    id: string;
    timestamp: string;
    error: string;
    context: Record<string, any>;
    recovery_attempted: boolean;
  }>;
  
  // Actions
  logAuditEvent: (event: Omit<AuditEvent, 'id' | 'timestamp'>) => void;
  reportPolicyViolation: (violation: Omit<PolicyViolation, 'id' | 'timestamp'>) => void;
  validateConstitutionalCompliance: () => Promise<void>;
  logError: (error: string, context: Record<string, any>) => void;
  clearAuditEvents: () => void;
  
  // Governance Helpers
  generateTraceId: () => string;
  generateAuditReference: () => string;
  validateAction: (action: string, resource: string) => Promise<boolean>;
}

// Create governance store
export const useGovernanceStore = create<GovernanceState>()(
  devtools((set, get) => ({
    // Initial State
    auditEvents: [],
    pendingAudits: 0,
    activePolicies: [
      'data_protection_policy',
      'access_control_policy', 
      'audit_logging_policy',
      'constitutional_compliance_policy',
    ],
    policyViolations: [],
    constitutionalCompliance: {
      framework_version: '1.0.0',
      compliance_level: 'compliant',
      last_check: new Date().toISOString(),
      violations: [],
    },
    errorEvents: [],

    // Actions
    logAuditEvent: (event: Omit<AuditEvent, 'id' | 'timestamp'>) => {
      const newEvent: AuditEvent = {
        ...event,
        id: generateId(),
        timestamp: new Date().toISOString(),
      };

      set((state) => ({
        auditEvents: [...state.auditEvents.slice(-99), newEvent], // Keep last 100 events
      }));

      // Send to backend
      sendAuditToBackend(newEvent).catch(console.error);
    },

    reportPolicyViolation: (violation: Omit<PolicyViolation, 'id' | 'timestamp'>) => {
      const newViolation: PolicyViolation = {
        ...violation,
        id: generateId(),
        timestamp: new Date().toISOString(),
      };

      set((state) => ({
        policyViolations: [...state.policyViolations, newViolation],
        constitutionalCompliance: {
          ...state.constitutionalCompliance,
          compliance_level: newViolation.severity === 'critical' ? 'violation' : 'warning',
        },
      }));

      // Send violation to backend
      sendViolationToBackend(newViolation).catch(console.error);
    },

    validateConstitutionalCompliance: async () => {
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        
        const response = await fetch(`${API_BASE_URL}/api/governance/compliance-check`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'X-Request-ID': generateId(),
          },
        });

        if (response.ok) {
          const compliance = await response.json();
          set({ constitutionalCompliance: compliance });
        }

      } catch (error) {
        console.error('Failed to validate constitutional compliance:', error);
        get().logError('compliance_validation_failed', { error: String(error) });
      }
    },

    logError: (error: string, context: Record<string, any>) => {
      const errorEvent = {
        id: generateId(),
        timestamp: new Date().toISOString(),
        error,
        context,
        recovery_attempted: false,
      };

      set((state) => ({
        errorEvents: [...state.errorEvents.slice(-49), errorEvent], // Keep last 50 errors
      }));

      // Also log as audit event
      get().logAuditEvent({
        user_id: 'system',
        action: 'error_logged',
        resource: 'frontend',
        outcome: 'failure',
        context: { error, ...context },
        governance_context: {
          request_id: generateId(),
          trace_id: generateId(),
          audit_reference: get().generateAuditReference(),
        },
      });
    },

    clearAuditEvents: () => {
      set({ auditEvents: [] });
    },

    generateTraceId: () => {
      return 'trace_' + Math.random().toString(36).substr(2, 16) + '_' + Date.now();
    },

    generateAuditReference: () => {
      const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
      const time = Date.now().toString(36);
      return `audit_${date}_${time}`;
    },

    validateAction: async (action: string, resource: string) => {
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        
        const response = await fetch(`${API_BASE_URL}/api/governance/validate-action`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': generateId(),
          },
          body: JSON.stringify({ action, resource }),
        });

        if (response.ok) {
          const result = await response.json();
          
          // Log validation result
          get().logAuditEvent({
            user_id: 'system',
            action: 'action_validation',
            resource,
            outcome: result.allowed ? 'success' : 'failure',
            context: { action, validation_result: result },
            governance_context: {
              request_id: generateId(),
              trace_id: get().generateTraceId(),
              audit_reference: get().generateAuditReference(),
            },
          });

          return result.allowed;
        }

        return false;

      } catch (error) {
        console.error('Action validation failed:', error);
        get().logError('action_validation_error', { action, resource, error: String(error) });
        return false;
      }
    },
  }), {
    name: 'mahoun-governance',
  })
);

// Helper functions
function generateId(): string {
  return Math.random().toString(36).substr(2, 12) + Date.now().toString(36);
}

async function sendAuditToBackend(event: AuditEvent): Promise<void> {
  try {
    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    
    await fetch(`${API_BASE_URL}/api/audit/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': generateId(),
      },
      body: JSON.stringify(event),
    });

  } catch (error) {
    console.error('Failed to send audit event to backend:', error);
  }
}

async function sendViolationToBackend(violation: PolicyViolation): Promise<void> {
  try {
    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    
    await fetch(`${API_BASE_URL}/api/governance/violations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': generateId(),
      },
      body: JSON.stringify(violation),
    });

  } catch (error) {
    console.error('Failed to send policy violation to backend:', error);
  }
}

// Governance hooks
export const useAuditTrail = () => {
  const { logAuditEvent, auditEvents, pendingAudits } = useGovernanceStore();
  
  return {
    logEvent: logAuditEvent,
    events: auditEvents,
    pendingCount: pendingAudits,
  };
};

export const useConstitutionalCompliance = () => {
  const { 
    constitutionalCompliance, 
    validateConstitutionalCompliance, 
    policyViolations 
  } = useGovernanceStore();
  
  return {
    compliance: constitutionalCompliance,
    violations: policyViolations,
    validate: validateConstitutionalCompliance,
  };
};

export const useErrorTracking = () => {
  const { errorEvents, logError } = useGovernanceStore();
  
  return {
    errors: errorEvents,
    logError,
    hasErrors: errorEvents.length > 0,
    criticalErrors: errorEvents.filter(e => 
      e.context.severity === 'critical' || e.error.includes('critical')
    ),
  };
};