/**
 * Protected Route Component
 * Wraps routes that require authentication
 */

import { Navigate } from 'react-router-dom';
import { useAuth, Permission, Role } from '../../store/authStore';
import type { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
  requireAuth?: boolean;
  requiredPermission?: Permission;
  requiredPermissions?: Permission[];
  requiredRoles?: Role[];
}

export default function ProtectedRoute({
  children,
  requireAuth = true,
  requiredPermission,
  requiredPermissions,
  requiredRoles,
}: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuth();

  if (requireAuth && (!isAuthenticated || !user)) {
    return <Navigate to="/login" replace />;
  }

  if (requiredPermission && !user?.permissions.includes(requiredPermission)) {
    return <Navigate to="/" replace />;
  }

  if (requiredPermissions && requiredPermissions.length > 0) {
    const hasAllPermissions = requiredPermissions.every((perm) => user?.permissions.includes(perm));
    if (!hasAllPermissions) {
      return <Navigate to="/" replace />;
    }
  }

  if (requiredRoles && requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some((role) => user?.role === role);
    if (!hasRequiredRole) {
      return <Navigate to="/" replace />;
    }
  }

  return <>{children}</>;
}

// For backwards compatibility with singular permission prop
export type { ProtectedRouteProps };
