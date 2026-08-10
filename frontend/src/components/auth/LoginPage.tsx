/**
 * MAHOUN Login Page
 * 
 * Comprehensive authentication interface with:
 * - Persian/English support
 * - Governance integration
 * - Security features
 * - Audit logging
 */

import React, { useState } from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth, LoginCredentials } from '../../store/authStore';
import { useGovernanceStore } from '../../store/governanceStore';
import { EyeIcon, EyeSlashIcon, LockClosedIcon } from '@heroicons/react/24/outline';

interface LocationState {
  from?: Location;
}

export const LoginPage: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated, login } = useAuth();
  const { logAuditEvent } = useGovernanceStore();
  
  const [credentials, setCredentials] = useState<LoginCredentials>({
    username: '',
    password: '',
  });
  
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);

  const state = location.state as LocationState;
  const from = state?.from?.pathname || '/dashboard';

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      // Validate input
      if (!credentials.username.trim() || !credentials.password) {
        throw new Error('نام کاربری و رمز عبور الزامی است');
      }

      // Log login attempt
      logAuditEvent({
        user_id: credentials.username,
        action: 'login_attempt',
        resource: 'authentication',
        outcome: 'success', // Will be updated based on result
        context: {
          username: credentials.username,
          timestamp: new Date().toISOString(),
          ip_address: 'unknown', // Would be populated by backend
        },
        governance_context: {
          request_id: generateRequestId(),
          trace_id: generateTraceId(),
          audit_reference: generateAuditReference(),
        },
      });

      // Attempt login
      await login(credentials);

      // Success - redirect handled by auth state change

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'خطا در ورود به سیستم';
      setError(errorMessage);
      setAttempts(prev => prev + 1);

      // Log failed login
      logAuditEvent({
        user_id: credentials.username,
        action: 'login_failed',
        resource: 'authentication',
        outcome: 'failure',
        context: {
          username: credentials.username,
          error: errorMessage,
          attempt_count: attempts + 1,
        },
        governance_context: {
          request_id: generateRequestId(),
          trace_id: generateTraceId(),
          audit_reference: generateAuditReference(),
        },
      });

    } finally {
      setIsLoading(false);
    }
  };

  // Handle input changes
  const handleInputChange = (field: keyof LoginCredentials) => 
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setCredentials(prev => ({
        ...prev,
        [field]: e.target.value,
      }));
      
      // Clear error when user starts typing
      if (error) {
        setError(null);
      }
    };

  // Check for too many attempts
  const isBlocked = attempts >= 5;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 flex items-center justify-center bg-primary-600 rounded-full">
            <LockClosedIcon className="h-8 w-8 text-white" />
          </div>
          
          <h2 className="mt-6 text-3xl font-bold text-slate-100">
            ورود به سیستم ماحون
          </h2>
          
          <p className="mt-2 text-sm text-slate-400">
            سیستم هوش مصنوعی حقوقی با ضمانت صفر توهم
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-xl p-8">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Username Field */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-300 mb-2">
                نام کاربری
              </label>
              <input
                id="username"
                type="text"
                required
                disabled={isBlocked || isLoading}
                value={credentials.username}
                onChange={handleInputChange('username')}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                placeholder="نام کاربری خود را وارد کنید"
                dir="rtl"
              />
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
                رمز عبور
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  disabled={isBlocked || isLoading}
                  value={credentials.password}
                  onChange={handleInputChange('password')}
                  className="w-full px-3 py-2 pr-10 bg-slate-800 border border-slate-600 rounded-md text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                  placeholder="رمز عبور خود را وارد کنید"
                  dir="rtl"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-300"
                  disabled={isBlocked || isLoading}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-5 w-5" />
                  ) : (
                    <EyeIcon className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-900/50 border border-red-700 rounded-md p-3">
                <p className="text-sm text-red-300 text-center" dir="rtl">
                  {error}
                </p>
              </div>
            )}

            {/* Blocked Message */}
            {isBlocked && (
              <div className="bg-yellow-900/50 border border-yellow-700 rounded-md p-3">
                <p className="text-sm text-yellow-300 text-center" dir="rtl">
                  تعداد تلاش‌های ناموفق زیاد است. لطفاً چند دقیقه صبر کرده و دوباره تلاش کنید.
                </p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isBlocked || isLoading || !credentials.username || !credentials.password}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>در حال ورود...</span>
                </div>
              ) : (
                'ورود به سیستم'
              )}
            </button>
          </form>

          {/* Additional Links */}
          <div className="mt-6 text-center space-y-2">
            <Link 
              to="/forgot-password" 
              className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
            >
              فراموشی رمز عبور
            </Link>
            
            <div className="text-xs text-slate-500">
              سیستم ماحون v2.0.0 - {new Date().getFullYear()}
            </div>
          </div>
        </div>

        {/* Security Notice */}
        <div className="text-center">
          <p className="text-xs text-slate-500">
            این سیستم دارای نظارت امنیتی کامل و ثبت تمامی فعالیت‌ها می‌باشد
          </p>
        </div>
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

export default LoginPage;