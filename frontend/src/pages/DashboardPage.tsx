import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Link2,
  LogOut,
  User,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Zap,
  ExternalLink,
  Settings,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../context/useAuth';
import api from '../lib/api';
import toast from 'react-hot-toast';

export const DashboardPage: React.FC = () => {
  const { user, logout, refetchUser } = useAuth();
  const navigate = useNavigate();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      toast.success('Logged out successfully');
      navigate('/login');
    } catch {
      toast.error('Logout failed');
    }
  };

  const handleTestRefresh = async () => {
    setIsRefreshing(true);
    try {
      const res = await api.post('/auth/refresh');
      toast.success(res.data.message || 'Token rotated successfully!');
      await refetchUser();
    } catch {
      toast.error('Token refresh failed');
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-gray-100 flex flex-col">
      {/* Navigation Header */}
      <header className="border-b border-white/10 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2.5 font-bold text-lg text-white">
              <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-indigo-500/25 shadow-md">
                <Link2 className="w-5 h-5" />
              </div>
              <span>SphereSphere</span>
            </Link>

            <nav className="hidden md:flex items-center gap-1 text-sm">
              <Link
                to="/dashboard"
                className="px-3 py-1.5 rounded-lg bg-white/10 text-white font-medium"
              >
                Dashboard
              </Link>
              <Link
                to="/links"
                className="px-3 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors flex items-center gap-1.5"
              >
                <Zap className="w-3.5 h-3.5 text-indigo-400" />
                <span>Links</span>
              </Link>
              <Link
                to="/bio"
                className="px-3 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors flex items-center gap-1.5"
              >
                <User className="w-3.5 h-3.5 text-indigo-400" />
                <span>Bio-Link</span>
              </Link>
              <span
                className="px-3 py-1.5 rounded-lg text-gray-500 cursor-not-allowed flex items-center gap-1"
                title="Available in Phase 9"
              >
                <Settings className="w-3.5 h-3.5" />
                Settings
              </span>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-gray-300 font-medium">@{user?.username}</span>
            </div>

            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-red-500/20 text-gray-300 hover:text-red-300 border border-white/10 transition-colors text-xs font-semibold cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Welcome Banner */}
        <div className="rounded-2xl bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-slate-900/50 border border-indigo-500/20 p-6 sm:p-8 backdrop-blur-sm">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                  Hello, {user?.name}!
                </h1>
                {user?.isEmailVerified ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Verified
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Unverified
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-400">
                You are securely signed in using httpOnly cookies and Argon2id password encryption.
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={handleTestRefresh}
                disabled={isRefreshing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                <span>Rotate Session</span>
              </button>
            </div>
          </div>
        </div>

        {/* Verification Alert if not verified */}
        {!user?.isEmailVerified && (
          <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-amber-300">Email Address Unverified</p>
                <p className="text-xs text-amber-200/80">Please check your inbox or simulation link to verify your account.</p>
              </div>
            </div>
            <Link
              to="/verify-email"
              className="px-3.5 py-1.5 rounded-lg bg-amber-500 text-black text-xs font-semibold hover:bg-amber-400 transition-colors"
            >
              Verify Token
            </Link>
          </div>
        )}

        {/* Security & Authentication Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-2xl bg-white/5 border border-white/10 p-6 space-y-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Auth Architecture</h2>
              <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                15-minute access token + 7-day refresh token stored strictly in httpOnly cookies. LocalStorage/sessionStorage remain 100% token-free.
              </p>
            </div>
            <div className="text-xs text-indigo-300 font-mono bg-black/40 rounded-lg p-2.5 border border-white/5">
              Argon2id + SHA-256 Rotation
            </div>
          </div>

          <div className="rounded-2xl bg-white/5 border border-white/10 p-6 space-y-4">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 flex items-center justify-center border border-purple-500/30">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Account Profile</h2>
              <div className="mt-2 space-y-1 text-xs text-gray-300">
                <p><strong className="text-gray-400">User ID:</strong> <span className="font-mono text-gray-200">{user?.id}</span></p>
                <p><strong className="text-gray-400">Email:</strong> {user?.email}</p>
                <p><strong className="text-gray-400">Username:</strong> @{user?.username}</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white/5 border border-white/10 p-6 space-y-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-600/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Short-Link Engine</h2>
              <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                Phase 3 short-link engine active. Create 6-character short codes and custom vanity slugs.
              </p>
            </div>
            <Link
              to="/links"
              className="w-full py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Manage Short Links</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
};
