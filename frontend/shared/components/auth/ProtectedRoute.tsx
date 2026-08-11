/**
 * MAHOUN Protected Route Component
 * 
 * Comprehensive route protection with:
 * - Authentication validation
 * - Permission-based access control
 * - Governance integration
 * - Audit logging
 */

import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth, Permission, Role } from '../../stores/authStore';
import { useGovernanceStore } from '../../stores/governanceStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermissions?: Permission[];
  requiredRoles?: Role[];
  fallback?: React.ReactNode;
  requireAuth?: boolean;
}

/**
 * Protected Route wrapper with comprehensive access control
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredPermissions = [],
  requiredRoles = [],
  fallback,
  requireAuth = true,
}) => {
  const location = useLocation();
  const { 
    isAuthenticated, 
    user, 
    permissions, 
    validateSession, 
    isSessionValid,
    logUserAction 
  } = useAuth();
  const { logAuditEvent } = useGovernanceStore();

  // Validate session on mount and route change
  useEffect(() => {
    if (isAuthenticated) {
      validateSession();
    }
  }, [location.pathname, isAuthenticated]);

  // Log route access attempt
  useEffect(() => {
    logAuditEvent({
      user_id: user?.user_id || 'anonymous',
      action: 'route_access_attempt',
      resource: location.pathname,
      outcome: 'success', // Will be updated based on access decision
      context: {
        path: location.pathname,
        required_permissions: requiredPermissions,
        required_roles: requiredRoles,
      },
      governance_context: {
        request_id: generateRequestId(),
        trace_id: generateTraceId(),
        audit_reference: generateAuditReference(),
      },
    });
  }, [location.pathname]);

  // Authentication check
  if (requireAuth && !isAuthenticated) {
    logUserAction('route_access_denied', {
      reason: 'not_authenticated',
      path: location.pathname,
    });

    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Session validity check
  if (requireAuth && isAuthenticated && !isSessionValid) {
    logUserAction('route_access_denied', {
      reason: 'invalid_session',
      path: location.pathname,
    });

    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Permission check
  if (requiredPermissions.length > 0) {
    const hasPermissions = requiredPermissions.every(permission => 
      permissions.includes(permission)
    );

    if (!hasPermissions) {
      logUserAction('route_access_denied', {
        reason: 'insufficient_permissions',
        path: location.pathname,
        required_permissions: requiredPermissions,
        user_permissions: permissions,
      });

      return fallback || <UnauthorizedPage />;
    }
  }

  // Role check
  if (requiredRoles.length > 0 && user) {
    const hasRole = requiredRoles.includes(user.role);

    if (!hasRole) {
      logUserAction('route_access_denied', {
        reason: 'insufficient_role',
        path: location.pathname,
        required_roles: requiredRoles,
        user_role: user.role,
      });

      return fallback || <UnauthorizedPage />;
    }
  }

  // Log successful access
  logUserAction('route_access_granted', {
    path: location.pathname,
    user_id: user?.user_id,
    permissions: permissions,
  });

  return <>{children}</>;
};

/**
 * Unauthorized access page
 */
const UnauthorizedPage: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="max-w-md w-full bg-slate-900 rounded-lg border border-slate-700 p-8 text-center">
        <div className="mb-6">
          <svg
            className="mx-auto h-16 w-16 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>
        
        <h1 className="text-2xl font-bold text-slate-100 mb-4">
          دسترسی غیرمجاز
        </h1>
        
        <p className="text-slate-400 mb-6">
          شما اجازه دسترسی به این صفحه را ندارید. لطفاً با مدیر سیستم تماس بگیرید.
        </p>
        
        <button
          onClick={() => window.history.back()}
          className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg transition-colors"
        >
          بازگشت
        </button>
      </div>
    </div>
  );
};

/**
 * Login required page
 */
export const LoginRequired: React.FC = () => {
  const location = useLocation();

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="max-w-md w-full bg-slate-900 rounded-lg border border-slate-700 p-8 text-center">
        <div className="mb-6">
          <svg
            className="mx-auto h-16 w-16 text-primary-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
        </div>
        
        <h1 className="text-2xl font-bold text-slate-100 mb-4">
          ورود به سیستم لازم است
        </h1>
        
        <p className="text-slate-400 mb-6">
          برای دسترسی به این صفحه باید وارد سیستم شوید.
        </p>
        
        <Navigate to="/login" state={{ from: location }} replace />
      </div>
    </div>
  );
};

// Utility functions
function generateRequestId(): string {
  return 'req_' + Math.random().toString(36).substr(2, 16);
}

function generateTraceId(): string {
  return 'trace_' + Math.random().toString(36).substr(2, 16);
}

function generateAuditReference(): string {
  const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
  const time = Date.now().toString(36);
  return `audit_${date}_${time}`;
}

export default ProtectedRoute;
