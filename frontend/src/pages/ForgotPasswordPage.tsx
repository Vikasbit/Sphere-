import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Link2, Mail, Loader2, ArrowRight, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import api from '../lib/api';
import type { MessageResponse } from '../types/auth';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MessageResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.post<MessageResponse>('/auth/forgot-password', { email: cleanEmail });
      setResult(response.data);
    } catch {
      setErrorMessage('An error occurred. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 px-4 py-12 text-gray-100">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 shadow-indigo-500/30 shadow-lg text-white mb-4 hover:scale-105 transition-transform">
            <Link2 className="w-7 h-7" />
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Reset your password
          </h1>
          <p className="mt-2 text-sm text-gray-400">
            Enter your email and we&apos;ll send you a secure recovery link
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/10 backdrop-blur-md border border-white/10 rounded-2xl p-8 shadow-2xl">
          {result ? (
            <div className="text-center space-y-5 animate-in fade-in zoom-in-95 duration-300">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-white">Check your inbox</h2>
              <p className="text-sm text-gray-300">{result.message}</p>

              {/* Dev Simulation Helper */}
              {result.devResetUrl && (
                <div className="rounded-xl bg-indigo-500/10 border border-indigo-500/30 p-4 text-left">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-300 mb-2">
                    <Mail className="w-4 h-4" />
                    <span>Dev Reset Simulation</span>
                  </div>
                  <p className="text-xs text-gray-300 mb-3">
                    Development mode active. You can proceed with password reset directly:
                  </p>
                  <Link
                    to={`/reset-password?token=${result.devResetToken}`}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 px-3 py-2 rounded-lg transition-colors"
                  >
                    <span>Simulate: Click Reset Link</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              <div className="pt-4 border-t border-white/10">
                <Link
                  to="/login"
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium text-sm transition-all"
                >
                  Return to Sign In
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {errorMessage && (
                <div className="flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/30 p-4 text-red-300 text-sm animate-in fade-in duration-200">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <div>
                <label htmlFor="forgot-email" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                  Account Email
                </label>
                <input
                  id="forgot-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isLoading}
                  placeholder="alex@example.com"
                  className="w-full px-4 py-2.5 rounded-xl bg-black/30 border border-white/15 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-medium text-sm shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed mt-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Sending reset link...</span>
                  </>
                ) : (
                  <>
                    <span>Send Reset Instructions</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              <div className="pt-4 border-t border-white/10 text-center">
                <Link to="/login" className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
                  Remember your password? Sign in
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
