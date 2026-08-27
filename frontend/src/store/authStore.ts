/**
 * Authentication Store
 * Manages user authentication, token persistence, and role authorization state.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { loginAPI, getCurrentUserAPI, refreshTokenAPI, logoutAPI, UserResponse } from '../api/client';

export enum Role {
  ADMIN = 'admin',
  ANALYST = 'analyst',
  VIEWER = 'viewer',
  GUEST = 'guest',
  LEGAL_PROFESSIONAL = 'legal_professional',
  USER = 'user',
}

export enum Permission {
  READ = 'read',
  WRITE = 'write',
  DELETE = 'delete',
  ADMIN = 'admin',
  APPROVE = 'approve',
  GOVERN = 'govern',
  EXPORT = 'export',
  ANONYMIZE = 'anonymize',
}

export interface User {
  id: string;
  username: string;
  email: string;
  name: string;
  role: Role | string;
  permissions: (Permission | string)[];
  lastLogin?: string;
  createdAt?: string;
  is_active?: boolean;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  token: string | null; // Alias for backward compatibility
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
  hasPermission: (permission: Permission | string) => boolean;
  hasRole: (role: Role | string) => boolean;
  validateSession: () => Promise<void>;
  logUserAction: (action: string, metadata?: Record<string, any>) => void;
}

function mapUserResponse(data: UserResponse): User {
  return {
    id: String(data.id),
    username: data.username,
    email: data.email,
    name: data.full_name || data.username,
    role: (data.role?.toLowerCase() as Role) || Role.ANALYST,
    permissions: (data.permissions || []).map((p) => p.toLowerCase()),
    is_active: data.is_active,
    createdAt: data.created_at,
    lastLogin: new Date().toISOString(),
  };
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (usernameOrEmail: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          // 1. Call OAuth2 Login API (application/x-www-form-urlencoded)
          const tokenData = await loginAPI(usernameOrEmail, password);
          const accessToken = tokenData.access_token;
          const refreshToken = tokenData.refresh_token;

          // Temporarily store token for getCurrentUserAPI call
          set({
            accessToken,
            refreshToken,
            token: accessToken,
          });

          // 2. Fetch full current user info (/api/v1/auth/me)
          const userData = await getCurrentUserAPI(accessToken);
          const user = mapUserResponse(userData);

          set({
            user,
            accessToken,
            refreshToken,
            token: accessToken,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          const message = error instanceof Error ? error.message : 'نام کاربری یا رمز عبور اشتباه است';
          set({
            error: message,
            isLoading: false,
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
            token: null,
          });
          throw new Error(message);
        }
      },

      logout: () => {
        const { accessToken } = get();
        if (accessToken) {
          logoutAPI(accessToken).catch(() => {});
        }
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },

      setUser: (user: User | null) => {
        set({ user, isAuthenticated: user !== null });
      },

      hasPermission: (permission: Permission | string) => {
        const { user } = get();
        if (!user) return false;
        if (String(user.role).toLowerCase() === 'admin') return true;
        const target = String(permission).toLowerCase();
        return user.permissions.some((p) => String(p).toLowerCase() === target);
      },

      hasRole: (role: Role | string) => {
        const { user } = get();
        if (!user) return false;
        const currentRole = String(user.role).toLowerCase();
        const targetRole = String(role).toLowerCase();
        return currentRole === targetRole || currentRole === 'admin';
      },

      validateSession: async () => {
        const { accessToken, refreshToken, logout } = get();
        if (!accessToken) {
          set({ isAuthenticated: false, user: null, isLoading: false });
          return;
        }

        try {
          const userData = await getCurrentUserAPI(accessToken);
          const user = mapUserResponse(userData);
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (err) {
          // If access token expired, attempt refresh token
          if (refreshToken) {
            try {
              const refreshed = await refreshTokenAPI(refreshToken);
              set({
                accessToken: refreshed.access_token,
                refreshToken: refreshed.refresh_token,
                token: refreshed.access_token,
              });
              const userData = await getCurrentUserAPI(refreshed.access_token);
              const user = mapUserResponse(userData);
              set({ user, isAuthenticated: true, isLoading: false });
              return;
            } catch (refreshErr) {
              logout();
            }
          } else {
            logout();
          }
        }
      },

      logUserAction: (action: string, metadata: Record<string, any> = {}) => {
        const { user } = get();
        console.log('User Action:', { action, userId: user?.id, username: user?.username, ...metadata });
      },
    }),
    {
      name: 'mahoun-auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        token: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
