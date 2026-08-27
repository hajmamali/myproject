/**
 * Login Page Component - User Facing
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../store/authStore';
import { LockClosedIcon, ShieldCheckIcon } from '@heroicons/react/24/outline';

export default function LoginPage() {
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(usernameOrEmail, password);
      navigate('/app/portal/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'نام کاربری یا رمز عبور اشتباه است');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-950 via-blue-900 to-indigo-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl p-8 border border-slate-100">
          <div className="text-center mb-8">
            <div className="mx-auto h-16 w-16 flex items-center justify-center bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/30">
              <LockClosedIcon className="h-8 w-8 text-white" />
            </div>
            <h1 className="mt-6 text-2xl font-bold text-slate-900">ماحون</h1>
            <p className="mt-2 text-slate-600 text-sm">پلتفرم استدلال و تحلیل حقوقی</p>
            <p className="mt-1 text-xs text-slate-400">سامانه هوشمند تحلیل آراء و قراردادهای قضایی</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-700 mb-1">
                نام کاربری یا ایمیل
              </label>
              <input
                id="username"
                type="text"
                value={usernameOrEmail}
                onChange={(e) => setUsernameOrEmail(e.target.value)}
                placeholder="admin یا admin@mahoun.ai"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white transition"
                required
                dir="ltr"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">
                رمز عبور
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white transition"
                required
                dir="ltr"
              />
            </div>

            {error && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm flex items-center gap-2">
                <span>⚠️</span>
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white font-medium py-3 rounded-xl shadow-lg shadow-blue-500/25 transition flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>در حال ورود...</span>
                </>
              ) : (
                'ورود به سیستم'
              )}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-500 flex items-center justify-center gap-1.5">
              <ShieldCheckIcon className="h-4 w-4 text-emerald-500 inline" />
              <span>محیط امن و تحت نظارت ساختار حاکمیتی</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
