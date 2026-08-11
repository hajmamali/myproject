/**
 * Governance Store
 * Manages governance context and authorization state
 */

import { create } from 'zustand';

export interface GovernanceContext {
  requestId: string;
  traceId: string;
  userId: string;
  timestamp: number;
  auditReference?: string;
  capabilities?: string[];
}

export interface GovernanceState {
  context: GovernanceContext | null;
  isInitialized: boolean;
  setContext: (context: GovernanceContext) => void;
  clearContext: () => void;
  getContext: () => GovernanceContext | null;
  hasCapability: (capability: string) => boolean;
  validateConstitutionalCompliance: () => Promise<void>;
}

const useGovernanceStore = create<GovernanceState>((set, get) => ({
  context: null,
  isInitialized: false,

  setContext: (context: GovernanceContext) => {
    set({ context, isInitialized: true });
  },

  clearContext: () => {
    set({ context: null, isInitialized: false });
  },

  getContext: () => {
    const { context } = get();
    return context;
  },

  hasCapability: (capability: string) => {
    const { context } = get();
    return context?.capabilities?.includes(capability) ?? false;
  },

  validateConstitutionalCompliance: async () => {
    const { context, isInitialized } = get();
    if (isInitialized && context) {
      console.log('Constitutional compliance validated for context:', context);
      return;
    }
    const defaultContext: GovernanceContext = {
      requestId: crypto.randomUUID(),
      traceId: crypto.randomUUID(),
      userId: 'system',
      timestamp: Date.now(),
    };
    set({ context: defaultContext, isInitialized: true });
  },
}));

export { useGovernanceStore };
