/**
 * Landing Page Component
 */

import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h1 className="text-5xl font-bold mb-4">MahouN</h1>
        <p className="text-xl text-slate-300 mb-8">
          Advanced Legal Search & Automated Verdict Platform
        </p>
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => navigate('/dashboard')}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium"
          >
            Get Started
          </button>
          <button
            onClick={() => navigate('/search')}
            className="px-8 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium"
          >
            Search Verdicts
          </button>
        </div>
      </div>
    </div>
  );
}
