/**
 * MAHOUN Authentication Store
 * 
 * Comprehensive authentication state management with:
 * - Governance integration
 * - RBAC permissions
 * - Audit trails
 * - Session management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

// Types
export interface UserIdentity {
  username: string;
  user_id: string;
  role: Role;
  permissions: Permission[];
  created_at: string;
  last_accessed: string;
}

export enum Role {
  ADMIN = 'admin',
  ANALYST = 'analyst', 
  VIEWER = 'viewer',
  API_USER = 'api_user',
}

export enum Permission {
  READ = 'read',
  WRITE = 'write',
  DELETE = 'delete',
  ADMIN = 'admin',
  EXPORT = 'export',
  ANONYMIZE = 'anonymize',
}

export interface GovernanceContext {
  request_id: string;
  trace_id: string;
  audit_reference: string;
  timestamp: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthState {
  // Authentication State
  isAuthenticated: boolean;
  user: UserIdentity | null;
  token: string | null;
  permissions: Permission[];
  
  // Governance Integration
  governanceContext: GovernanceContext;
  
  // Session Management
  sessionExpiry: Date | null;
  isSessionValid: boolean;
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateGovernanceContext: (context: Partial<GovernanceContext>) => void;
  validateSession: () => Promise<boolean>;
  checkPermission: (permission: Permission) => boolean;
  
  // Audit Actions
  logUserAction: (action: string, context: any) => Promise<void>;
}

// Governance middleware for audit logging
const governanceMiddleware = <T extends AuthState>(config: any) => (set: (state: Partial<T> | ((prev: T) => Partial<T>)) => void, get: () => T, api: any) =>
  config(
    (setArg: any) => {
      const result = set(setArg);
      
      // Log state changes for audit
      const state = get();
      if (state?.isAuthenticated && state?.governanceContext?.request_id) {
        console.log('Auth state change:', {
          timestamp: new Date().toISOString(),
          context: state.governanceContext,
          action: 'state_mutation',
        });
      }
      
      return result;
    },
    get,
    api
  );

// Create authentication store
export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      governanceMiddleware((set: any, get: any) => ({
        // Initial State
        isAuthenticated: false,
        user: null,
        token: null,
        permissions: [],
        governanceContext: {
          request_id: '',
          trace_id: '',
          audit_reference: '',
          timestamp: '',
        },
        sessionExpiry: null,
        isSessionValid: false,

        // Actions
        login: async (credentials: LoginCredentials) => {
          try {
            // Development hardcoded user for demo purposes
            if (import.meta.env.DEV && credentials.username === 'haji' && credentials.password === 'haji') {
              const mockUser = {
                username: 'haji',
                user_id: 'user_haji_001',
                role: Role.ADMIN,
                permissions: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN, Permission.EXPORT, Permission.ANONYMIZE],
                created_at: new Date().toISOString(),
                last_accessed: new Date().toISOString(),
              };

              set({
                isAuthenticated: true,
                user: mockUser,
                token: 'mock_token_dev_haji',
                permissions: mockUser.permissions,
                governanceContext: {
                  request_id: generateRequestId(),
                  trace_id: generateTraceId(),
                  audit_reference: generateAuditReference(),
                  timestamp: new Date().toISOString(),
                },
                sessionExpiry: new Date(Date.now() + 8 * 60 * 60 * 1000), // 8 hours
                isSessionValid: true,
              });

              // Log successful login
              await get().logUserAction('login_success', {
                username: credentials.username,
                timestamp: new Date().toISOString(),
              });
              return;
            }

            const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            
            const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-Request-ID': generateRequestId(),
              },
              body: JSON.stringify(credentials),
            });

            if (!response.ok) {
              throw new Error('Authentication failed');
            }

            const data = await response.json();
            
            set({
              isAuthenticated: true,
              user: data.user,
              token: data.token,
              permissions: data.user.permissions,
              governanceContext: {
                request_id: data.governance_context.request_id,
                trace_id: data.governance_context.trace_id,
                audit_reference: data.governance_context.audit_reference,
                timestamp: new Date().toISOString(),
              },
              sessionExpiry: new Date(Date.now() + data.expires_in * 1000),
              isSessionValid: true,
            });

            // Log successful login
            await get().logUserAction('login_success', {
              username: credentials.username,
              timestamp: new Date().toISOString(),
            });

          } catch (error) {
            // Log failed login attempt
            console.error('Login failed:', error);
            throw error;
          }
        },

        logout: () => {
          const { logUserAction } = get();
          
          // Log logout
          logUserAction('logout', {
            timestamp: new Date().toISOString(),
          }).catch(console.error);

          set({
            isAuthenticated: false,
            user: null,
            token: null,
            permissions: [],
            governanceContext: {
              request_id: '',
              trace_id: '',
              audit_reference: '',
              timestamp: '',
            },
            sessionExpiry: null,
            isSessionValid: false,
          });
        },

        refreshToken: async () => {
          try {
            const { token, user } = get();
            if (!token) throw new Error('No token to refresh');

            // For hardcoded dev user, just extend the session
            if (import.meta.env.DEV && user?.username === 'haji') {
              set({
                token: 'mock_token_dev_haji_refreshed',
                sessionExpiry: new Date(Date.now() + 8 * 60 * 60 * 1000), // Extend 8 hours
                isSessionValid: true,
              });
              return;
            }

            const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            
            const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-Request-ID': generateRequestId(),
              },
            });

            if (!response.ok) {
              throw new Error('Token refresh failed');
            }

            const data = await response.json();
            
            set({
              token: data.token,
              sessionExpiry: new Date(Date.now() + data.expires_in * 1000),
              isSessionValid: true,
            });

          } catch (error) {
            console.error('Token refresh failed:', error);
            get().logout();
            throw error;
          }
        },

        updateGovernanceContext: (context: Partial<GovernanceContext>) => {
          set((state: AuthState) => ({
            governanceContext: {
              ...state.governanceContext,
              ...context,
            },
          }));
        },

        validateSession: async () => {
          const { sessionExpiry, token } = get();
          
          if (!token || !sessionExpiry) {
            set({ isSessionValid: false });
            return false;
          }

          if (new Date() > sessionExpiry) {
            try {
              await get().refreshToken();
              return true;
            } catch {
              set({ isSessionValid: false });
              return false;
            }
          }

          set({ isSessionValid: true });
          return true;
        },

        checkPermission: (permission: Permission) => {
          const { permissions, isAuthenticated } = get();
          return isAuthenticated && permissions.includes(permission);
        },

        logUserAction: async (action: string, context: any) => {
          try {
            const { token, governanceContext } = get();
            if (!token) return;

            const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            
            await fetch(`${API_BASE_URL}/api/audit/log`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-Request-ID': generateRequestId(),
                'X-Governance-Context': JSON.stringify(governanceContext),
              },
              body: JSON.stringify({
                action,
                context,
                timestamp: new Date().toISOString(),
                governance_context: governanceContext,
              }),
            });

          } catch (error) {
            console.error('Failed to log user action:', error);
          }
        },
      })),
      {
        name: 'mahoun-auth-store',
        partialize: (state) => ({
          isAuthenticated: state.isAuthenticated,
          user: state.user,
          token: state.token,
          permissions: state.permissions,
          sessionExpiry: state.sessionExpiry,
        }),
      }
    ),
    {
      name: 'mahoun-auth',
    }
  )
);

// Utility functions
function generateRequestId(): string {
  return 'req_' + Math.random().toString(36).substr(2, 16);
}

// Auth hooks
export const useAuth = () => {
  const auth = useAuthStore();
  
  return {
    ...auth,
    isAuthorized: (permission: Permission) => auth.checkPermission(permission),
    hasRole: (role: Role) => auth.user?.role === role,
  };
};

export const useGovernance = () => {
  const { governanceContext, updateGovernanceContext, logUserAction } = useAuthStore();
  
  return {
    governanceContext,
    updateContext: updateGovernanceContext,
    logAction: logUserAction,
    generateRequestId,
  };
};