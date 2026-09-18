import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Link2, Eye, EyeOff, Loader2, ArrowRight, AlertCircle, CheckCircle2, Mail, ExternalLink } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import { AxiosError } from 'axios';
import type { SignupResponse } from '../types/auth';

export const SignupPage: React.FC = () => {
  const { signup } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [signupResult, setSignupResult] = useState<SignupResponse | null>(null);

  // Validation indicators
  const hasMinLength = password.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const isPasswordValid = hasMinLength && hasLetter && hasNumber;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanName = name.trim();
    const cleanEmail = email.trim().toLowerCase();
    const cleanUsername = username.trim().toLowerCase();

    if (cleanName.length < 2) {
      setErrorMessage('Full name must be at least 2 characters long.');
      return;
    }
    if (!/^[a-z0-9_-]{3,30}$/.test(cleanUsername)) {
      setErrorMessage('Username must be 3-30 characters (lowercase letters, numbers, hyphens, or underscores).');
      return;
    }
    if (!isPasswordValid) {
      setErrorMessage('Password must meet all minimum security requirements.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await signup(cleanName, cleanEmail, cleanUsername, password);
      setSignupResult(res);
    } catch (err) {
      if (err instanceof AxiosError && err.response?.data?.detail) {
        setErrorMessage(err.response.data.detail);
      } else {
        setErrorMessage('Failed to create account. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 px-4 py-12 text-gray-100">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 shadow-indigo-500/30 shadow-lg text-white mb-4 hover:scale-105 transition-transform">
            <Link2 className="w-7 h-7" />
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-gray-400">
            Start creating branded links and custom bio profiles
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/10 backdrop-blur-md border border-white/10 rounded-2xl p-8 shadow-2xl">
          {signupResult ? (
            /* Success State */
            <div className="text-center space-y-5 animate-in fade-in zoom-in-95 duration-300">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 mb-2">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-white">Account Created!</h2>
              <p className="text-sm text-gray-300">
                We sent a verification email to <strong className="text-indigo-300">{signupResult.user.email}</strong>.
              </p>

              {/* Dev simulation helper */}
              {signupResult.devVerificationUrl && (
                <div className="rounded-xl bg-indigo-500/10 border border-indigo-500/30 p-4 text-left">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-300 mb-2">
                    <Mail className="w-4 h-4" />
                    <span>Dev Email Simulation</span>
                  </div>
                  <p className="text-xs text-gray-300 mb-3">
                    Click the link below to verify your account immediately (no SMTP required):
                  </p>
                  <Link
                    to={`/verify-email?token=${signupResult.devVerificationToken}`}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 px-3 py-2 rounded-lg transition-colors"
                  >
                    <span>Simulate: Click Verification Link</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              <div className="pt-4 border-t border-white/10">
                <Link
                  to="/login"
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium text-sm transition-all"
                >
                  Proceed to Sign In
                </Link>
              </div>
            </div>
          ) : (
            /* Signup Form */
            <>
              {errorMessage && (
                <div className="mb-6 flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/30 p-4 text-red-300 text-sm animate-in fade-in duration-200">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Name */}
                <div>
                  <label htmlFor="signup-name" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                    Full Name
                  </label>
                  <input
                    id="signup-name"
                    type="text"
                    autoComplete="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    disabled={isLoading}
                    placeholder="Alex Morgan"
                    className="w-full px-4 py-2.5 rounded-xl bg-black/30 border border-white/15 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm"
                  />
                </div>

                {/* Email */}
                <div>
                  <label htmlFor="signup-email" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                    Email Address
                  </label>
                  <input
                    id="signup-email"
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

                {/* Username */}
                <div>
                  <label htmlFor="signup-username" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                    Username
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 text-sm">@</span>
                    <input
                      id="signup-username"
                      type="text"
                      autoComplete="username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value.toLowerCase())}
                      required
                      disabled={isLoading}
                      placeholder="alexm"
                      className="w-full pl-8 pr-4 py-2.5 rounded-xl bg-black/30 border border-white/15 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm"
                    />
                  </div>
                </div>

                {/* Password */}
                <div>
                  <label htmlFor="signup-password" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="signup-password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      disabled={isLoading}
                      placeholder="••••••••"
                      className="w-full px-4 py-2.5 pr-12 rounded-xl bg-black/30 border border-white/15 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors p-1"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  {/* Password Requirements Checklist */}
                  {password.length > 0 && (
                    <div className="mt-2 text-xs space-y-1 text-gray-400 pl-1">
                      <div className={`flex items-center gap-1.5 ${hasMinLength ? 'text-emerald-400' : 'text-gray-400'}`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current" />
                        <span>At least 8 characters</span>
                      </div>
                      <div className={`flex items-center gap-1.5 ${hasLetter ? 'text-emerald-400' : 'text-gray-400'}`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current" />
                        <span>Contains at least one letter</span>
                      </div>
                      <div className={`flex items-center gap-1.5 ${hasNumber ? 'text-emerald-400' : 'text-gray-400'}`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current" />
                        <span>Contains at least one number</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-medium text-sm shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed mt-4"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Creating account...</span>
                    </>
                  ) : (
                    <>
                      <span>Create Account</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              {/* Footer */}
              <div className="mt-6 pt-5 border-t border-white/10 text-center">
                <p className="text-sm text-gray-400">
                  Already have an account?{' '}
                  <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors">
                    Sign in here
                  </Link>
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
