/**
 * Login Page Component - User Facing
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../store/authStore';
import { LockClosedIcon, ShieldCheckIcon } from '@heroicons/react/24/outline';

export default function LoginPage() {
  const [email, setEmail] = useState('');
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
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-950 via-blue-900 to-indigo-800 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="text-center mb-8">
            <div className="mx-auto h-16 w-16 flex items-center justify-center bg-blue-600 rounded-full">
              <LockClosedIcon className="h-8 w-8 text-white" />
            </div>
            <h1 className="mt-6 text-2xl font-bold text-slate-900">ماحون</h1>
            <p className="mt-2 text-slate-600">پلتفرم جستجوی آراء حقوقی</p>
            <p className="mt-1 text-xs text-slate-500">نسخه کاربری - پیشرو در هوش مصنوعی حقوقی</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700">
                ایمیل
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700">
                رمز عبور
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>

            {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">{error}</div>}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white font-medium py-2 rounded-lg transition"
            >
              {isLoading ? 'در حال ورود...' : 'ورود به سیستم'}
            </button>
          </form>
          
          <div className="mt-6 text-center">
            <p className="text-xs text-slate-500">
              <ShieldCheckIcon className="inline h-4 w-4 text-green-500" /> امنیت و حریم خصوصی تضمین شده
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
