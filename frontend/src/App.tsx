import { Routes, Route, Link } from 'react-router-dom';
import { Link2, Zap, BarChart3, ArrowRight, ShieldCheck, Share2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from './lib/api';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/useAuth';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { LinksPage } from './pages/LinksPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { PublicBioPage } from './pages/PublicBioPage';
import { BioBuilderPage } from './pages/BioBuilderPage';

function HomePage() {
  const { isAuthenticated, user } = useAuth();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await api.get('/health');
      return response.data;
    },
  });

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-gray-100 px-4 py-12">
      <div className="max-w-xl w-full mx-auto text-center">
        {/* Brand Icon & Heading */}
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600 text-white mb-6 shadow-xl shadow-indigo-500/25">
          <Link2 className="w-8 h-8" />
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl mb-3">
          SphereSphere
        </h1>
        <p className="text-gray-400 text-base sm:text-lg mb-8 max-w-md mx-auto">
          SphereSphere is a secure full-stack platform for creating short links, tracking privacy-conscious click analytics, generating customizable QR codes, and building public Bio-Link pages.
        </p>

        {/* Quick Auth Actions */}
        <div className="flex flex-wrap items-center justify-center gap-3 mb-10">
          {isAuthenticated ? (
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-500/30 transition-all"
            >
              <span>Go to Dashboard ({user?.name})</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          ) : (
            <>
              <Link
                to="/signup"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-500/30 transition-all"
              >
                <span>Get Started Free</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold text-sm border border-white/15 transition-all"
              >
                <span>Sign In</span>
              </Link>
            </>
          )}
        </div>

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 text-left">
          {[
            { icon: ShieldCheck, label: 'Authentication', desc: 'Argon2id + rotating httpOnly cookies' },
            { icon: Zap, label: 'Short Links & QR', desc: 'Custom vanity slugs & SVG/PNG QR codes' },
            { icon: BarChart3, label: 'Click Analytics', desc: 'Real-time aggregations, referrers & devices' },
            { icon: Share2, label: 'Bio-Link Pages', desc: 'Custom mobile landing pages with theme styling' },
          ].map(({ icon: Icon, label, desc }) => (
            <div
              key={label}
              className="bg-white/5 border border-white/10 rounded-xl p-4 backdrop-blur-sm hover:border-indigo-500/40 transition-colors"
            >
              <Icon className="w-5 h-5 text-indigo-400 mb-2" />
              <h3 className="font-semibold text-sm text-white">{label}</h3>
              <p className="text-xs text-gray-400 mt-1 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>

        {/* Backend & DB Health Indicator */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-left">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              System Infrastructure
            </span>
            <span className="text-xs font-mono text-indigo-400">Production Ready</span>
          </div>
          {isLoading && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <div className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-pulse" />
              <span>Verifying backend connections...</span>
            </div>
          )}
          {isError && (
            <div className="flex items-center gap-2 text-xs text-red-400">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <span>Backend server offline</span>
            </div>
          )}
          {data && (
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-2 bg-black/30 p-2 rounded-lg border border-white/5">
                <div className={`w-2 h-2 rounded-full ${data.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                <span className="text-gray-300">FastAPI: <span className="text-white font-medium">{data.status}</span></span>
              </div>
              <div className="flex items-center gap-2 bg-black/30 p-2 rounded-lg border border-white/5">
                <div className={`w-2 h-2 rounded-full ${data.database === 'connected' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <span className="text-gray-300">MongoDB: <span className="text-white font-medium">{data.database}</span></span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Public Bio Page (unauthenticated) */}
        <Route path="/bio/:username" element={<PublicBioPage />} />

        {/* Protected Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/links"
          element={
            <ProtectedRoute>
              <LinksPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics/:linkId"
          element={
            <ProtectedRoute>
              <AnalyticsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/bio"
          element={
            <ProtectedRoute>
              <BioBuilderPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;
