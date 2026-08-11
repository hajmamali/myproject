/**
 * Authentication Store
 * Manages user authentication and authorization state
 */

import { create } from 'zustand';

export enum Role {
  ADMIN = 'admin',
  ANALYST = 'analyst',
  VIEWER = 'viewer',
  GUEST = 'guest',
}

export enum Permission {
  READ = 'read',
  WRITE = 'write',
  DELETE = 'delete',
  ADMIN = 'admin',
  APPROVE = 'approve',
  GOVERN = 'govern',
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  permissions: Permission[];
  lastLogin?: string;
  createdAt?: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
  hasPermission: (permission: Permission) => boolean;
  hasRole: (role: Role) => boolean;
  validateSession: () => Promise<void>;
  logUserAction: (action: string, metadata?: Record<string, any>) => void;
}

const useAuth = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email: string, _password: string) => {
    set({ isLoading: true, error: null });
    try {
      // Mock login - replace with actual API call
      const mockUser: User = {
        id: '1',
        email,
        name: email.split('@')[0],
        role: Role.ANALYST,
        permissions: [Permission.READ, Permission.WRITE],
      };
      set({ user: mockUser, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Login failed',
        isLoading: false,
      });
    }
  },

  logout: () => {
    set({ user: null, isAuthenticated: false, error: null });
  },

  setUser: (user: User | null) => {
    set({ user, isAuthenticated: user !== null });
  },

  hasPermission: (permission: Permission) => {
    const { user } = get();
    return user ? user.permissions.includes(permission) : false;
  },

  hasRole: (role: Role) => {
    const { user } = get();
    return user ? user.role === role : false;
  },

  validateSession: async () => {
    const { user, isAuthenticated } = get();
    if (isAuthenticated && user) {
      return;
    }
    set({ isLoading: false });
  },

  logUserAction: (action: string, metadata: Record<string, any> = {}) => {
    const { user } = get();
    console.log('User Action:', { action, userId: user?.id, ...metadata });
  },
}));

export { useAuth };
