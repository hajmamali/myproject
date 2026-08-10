/**
 * Harvey-Style Premium Landing Page
 * 
 * Features:
 * - Animated gradient hero
 * - Glassmorphism effects
 * - Smooth scroll animations
 * - Premium typography
 * - Modern CTA buttons
 */

import { Link } from "react-router-dom";
import { 
  SparklesIcon, 
  ShieldCheckIcon, 
  BoltIcon, 
  ChartBarIcon,
  DocumentTextIcon,
  ScaleIcon
} from "@heroicons/react/24/outline";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900 text-white overflow-hidden">
      
      {/* Animated Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10 animate-gradient-shift opacity-50" />
      
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center px-6">
        <div className="max-w-6xl mx-auto text-center z-10">
          
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 backdrop-blur-sm mb-8 animate-fade-in">
            <SparklesIcon className="h-4 w-4 text-blue-400" />
            <span className="text-sm text-blue-300">سیستم هوش مصنوعی حقوقی نسل بعدی</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-6xl md:text-8xl font-bold mb-6 animate-slide-up">
            <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              MahouN
            </span>
            <br />
            <span className="text-slate-100">
              هوش مصنوعی حقوقی
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-xl md:text-2xl text-slate-300 mb-12 max-w-3xl mx-auto animate-slide-up animation-delay-200">
            تنها پلتفرم هوش مصنوعی با تضمین صفر هالوسیناسیون برای تحلیل حقوقی سطح سازمانی
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16 animate-slide-up animation-delay-400">
            <Link
              to="/app/dashboard"
              className="group relative px-8 py-4 rounded-xl font-semibold text-lg overflow-hidden bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 transition-all duration-300 shadow-xl hover:shadow-2xl hover:scale-105"
            >
              <span className="relative z-10">شروع رایگان</span>
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
            </Link>
            
            <Link
              to="/demo"
              className="px-8 py-4 rounded-xl font-semibold text-lg border-2 border-slate-600 hover:border-slate-400 backdrop-blur-sm hover:bg-white/5 transition-all duration-300"
            >
              مشاهده دمو
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto animate-fade-in animation-delay-600">
            <div className="backdrop-blur-sm bg-white/5 rounded-xl p-6 border border-white/10">
              <div className="text-3xl font-bold text-blue-400 mb-2">0%</div>
              <div className="text-sm text-slate-400">نرخ هالوسیناسیون</div>
            </div>
            <div className="backdrop-blur-sm bg-white/5 rounded-xl p-6 border border-white/10">
              <div className="text-3xl font-bold text-purple-400 mb-2">100%</div>
              <div className="text-sm text-slate-400">قابلیت ممیزی</div>
            </div>
            <div className="backdrop-blur-sm bg-white/5 rounded-xl p-6 border border-white/10">
              <div className="text-3xl font-bold text-pink-400 mb-2">24/7</div>
              <div className="text-sm text-slate-400">پشتیبانی</div>
            </div>
            <div className="backdrop-blur-sm bg-white/5 rounded-xl p-6 border border-white/10">
              <div className="text-3xl font-bold text-green-400 mb-2">۱۰۰k+</div>
              <div className="text-sm text-slate-400">رأی تحلیل شده</div>
            </div>
          </div>
        </div>

        {/* Scroll Indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 border-2 border-white/30 rounded-full flex items-start justify-center p-2">
            <div className="w-1 h-3 bg-white/50 rounded-full animate-scroll" />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-6">
              چرا <span className="text-blue-400">MahouN</span>؟
            </h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              تنها راه‌حل حقوقی با تضمین ریاضی صفر هالوسیناسیون
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature Card 1 */}
            <div className="group relative backdrop-blur-sm bg-white/5 rounded-2xl p-8 border border-white/10 hover:border-blue-500/50 transition-all duration-300 hover:scale-105">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10">
                <ShieldCheckIcon className="h-12 w-12 text-blue-400 mb-4" />
                <h3 className="text-2xl font-bold mb-3">صفر هالوسیناسیون</h3>
                <p className="text-slate-400">
                  هر نتیجه با منابع قابل تأیید در گراف دانش ما پشتیبانی می‌شود
                </p>
              </div>
            </div>

            {/* Feature Card 2 */}
            <div className="group relative backdrop-blur-sm bg-white/5 rounded-2xl p-8 border border-white/10 hover:border-purple-500/50 transition-all duration-300 hover:scale-105">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10">
                <DocumentTextIcon className="h-12 w-12 text-purple-400 mb-4" />
                <h3 className="text-2xl font-bold mb-3">کامل قابل ممیزی</h3>
                <p className="text-slate-400">
                  مسیر کامل استدلال برای انطباق با مقررات
                </p>
              </div>
            </div>

            {/* Feature Card 3 */}
            <div className="group relative backdrop-blur-sm bg-white/5 rounded-2xl p-8 border border-white/10 hover:border-pink-500/50 transition-all duration-300 hover:scale-105">
              <div className="absolute inset-0 bg-gradient-to-br from-pink-500/10 to-red-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10">
                <BoltIcon className="h-12 w-12 text-pink-400 mb-4" />
                <h3 className="text-2xl font-bold mb-3">حل قطعی</h3>
                <p className="text-slate-400">
                  رسیدگی به تضادها با رویکردهای مبتنی بر ریاضیات
                </p>
              </div>
            </div>

            {/* Feature Card 4 */}
            <div className="group relative backdrop-blur-sm bg-white/5 rounded-2xl p-8 border border-white/10 hover:border-green-500/50 transition-all duration-300 hover:scale-105">
              <div className="absolute inset-0 bg-gradient-to-br from-green-500/10 to-blue-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10">
                <ChartBarIcon className="h-12 w-12 text-green-400 mb-4" />
                <h3 className="text-2xl font-bold mb-3">سطح سازمانی</h3>
                <p className="text-slate-400">
                  ساخته شده برای بهداشت، مالی و خدمات حقوقی
                </p>
              </div>
            </div>

            {/* Feature Card 5 */}
            <div className="group relative backdrop-blur-sm bg-white/5 rounded-2xl p-8 border border-white/10 hover:border-yellow-500/50 transition-all duration-300 hover:scale-105">
              <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/10 to-orange-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10">
                <ScaleIcon className="h-12 w-12 text-yellow-400 mb-4" />
                <h3 className="text-2xl font-bold mb-3">سیستم نظارت</h3>
                <p className="text-slate-400">
                  محافظت از حریم خصوصی و رعایت مقررات از طریق طراحی
                </p>
              </div>
            </div>

            {/* Feature Card 6 */}
            <div className="group relative backdrop-blur-sm bg-white/5 rounded-2xl p-8 border border-white/10 hover:border-cyan-500/50 transition-all duration-300 hover:scale-105">
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative z-10">
                <SparklesIcon className="h-12 w-12 text-cyan-400 mb-4" />
                <h3 className="text-2xl font-bold mb-3">RAG پیشرفته</h3>
                <p className="text-slate-400">
                  ترکیبی از BM25 + Dense + Rerank برای نتایج دقیق
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-32 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            آماده برای شروع؟
          </h2>
          <p className="text-xl text-slate-400 mb-12">
            به هزاران تیم حقوقی که به MahouN اعتماد می‌کنند بپیوندید
          </p>
          <Link
            to="/app/dashboard"
            className="inline-block px-12 py-5 rounded-xl font-bold text-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 transition-all duration-300 shadow-2xl hover:shadow-blue-500/50 hover:scale-105"
          >
            شروع رایگان امروز
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative border-t border-white/10 py-12 px-6">
        <div className="max-w-7xl mx-auto text-center text-slate-500">
          <p>© 2026 MahouN. تمامی حقوق محفوظ است.</p>
        </div>
      </footer>
    </div>
  );
}
