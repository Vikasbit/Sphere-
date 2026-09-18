import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Link2, CheckCircle2, AlertCircle, Loader2, ArrowRight } from 'lucide-react';
import api from '../lib/api';
import { AxiosError } from 'axios';
import toast from 'react-hot-toast';

export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get('token') || '';

  const [token, setToken] = useState(tokenFromUrl);
  const [statusState, setStatusState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const executeVerification = async (verifyToken: string) => {
    if (!verifyToken.trim()) {
      setErrorMessage('Please provide a verification token.');
      setStatusState('error');
      return;
    }

    setStatusState('loading');
    setErrorMessage(null);

    try {
      await api.post('/auth/verify-email', { token: verifyToken.trim() });
      setStatusState('success');
      toast.success('Email successfully verified!');
    } catch (err) {
      setStatusState('error');
      if (err instanceof AxiosError && err.response?.data?.detail) {
        setErrorMessage(err.response.data.detail);
      } else {
        setErrorMessage('Verification failed. Token may be invalid or expired.');
      }
    }
  };

  useEffect(() => {
    if (tokenFromUrl) {
      const timer = setTimeout(() => {
        executeVerification(tokenFromUrl);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [tokenFromUrl]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 px-4 py-12 text-gray-100">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 shadow-indigo-500/30 shadow-lg text-white mb-4 hover:scale-105 transition-transform">
            <Link2 className="w-7 h-7" />
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Email Verification
          </h1>
          <p className="mt-2 text-sm text-gray-400">
            Confirm your email address to unlock full platform features
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/10 backdrop-blur-md border border-white/10 rounded-2xl p-8 shadow-2xl">
          {statusState === 'loading' && (
            <div className="text-center py-8 space-y-4">
              <Loader2 className="w-10 h-10 animate-spin text-indigo-400 mx-auto" />
              <p className="text-sm text-gray-300 font-medium">Verifying your token with the security server...</p>
            </div>
          )}

          {statusState === 'success' && (
            <div className="text-center space-y-5 animate-in fade-in zoom-in-95 duration-300 py-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-white">Email Confirmed!</h2>
              <p className="text-sm text-gray-300">
                Your email address has been verified. You can now access your dashboard and short links.
              </p>
              <div className="pt-4">
                <Link
                  to="/login"
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-medium text-sm shadow-lg shadow-indigo-500/25 transition-all"
                >
                  <span>Sign In to Your Account</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}

          {(statusState === 'idle' || statusState === 'error') && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                executeVerification(token);
              }}
              className="space-y-4"
            >
              {errorMessage && (
                <div className="flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/30 p-4 text-red-300 text-sm animate-in fade-in duration-200">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <div>
                <label htmlFor="verify-token" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                  Verification Token
                </label>
                <input
                  id="verify-token"
                  type="text"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste your verification token here..."
                  className="w-full px-4 py-2.5 rounded-xl bg-black/30 border border-white/15 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm font-mono"
                />
              </div>

              <button
                type="submit"
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-medium text-sm shadow-lg shadow-indigo-500/25 transition-all"
              >
                <span>Verify Email</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="pt-4 border-t border-white/10 text-center">
                <Link to="/login" className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
                  Back to Sign In
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
