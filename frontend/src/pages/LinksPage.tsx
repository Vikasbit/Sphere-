import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Link2,
  Copy,
  Check,
  Trash2,
  ExternalLink,
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Loader2,
  Sparkles,
  MousePointerClick,
  Calendar,
  LogOut,
  User,
  Zap,
  BarChart3,
  QrCode,
} from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../context/useAuth';
import toast from 'react-hot-toast';
import { AxiosError } from 'axios';
import type { LinkItem, LinkListResponse } from '../types/link';
import { QrCodeModal } from '../components/QrCodeModal';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';

export const LinksPage: React.FC = () => {
  const { user, logout } = useAuth();

  // Create form state
  const [destinationUrl, setDestinationUrl] = useState('');
  const [customSlug, setCustomSlug] = useState('');
  const [title, setTitle] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [recentlyCreated, setRecentlyCreated] = useState<LinkItem | null>(null);

  // Listing state
  const [links, setLinks] = useState<LinkItem[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Modal states
  const [qrModalLink, setQrModalLink] = useState<LinkItem | null>(null);
  const [deleteModalLink, setDeleteModalLink] = useState<LinkItem | null>(null);

  // Debounce search input (300ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchInput]);

  // Fetch links from backend
  const fetchLinks = useCallback(async (currentPage: number, currentSearch: string) => {
    setIsLoadingList(true);
    try {
      const params = new URLSearchParams({
        page: String(currentPage),
        page_size: String(pageSize),
      });
      if (currentSearch.trim()) {
        params.append('search', currentSearch.trim());
      }
      const response = await api.get<LinkListResponse>(`/links?${params.toString()}`);
      setLinks(response.data.items);
      setTotal(response.data.total);
      setTotalPages(response.data.totalPages);
      setPage(response.data.page);
    } catch {
      toast.error('Failed to load links');
    } finally {
      setIsLoadingList(false);
    }
  }, [pageSize]);

  useEffect(() => {
    let isMounted = true;
    const timer = setTimeout(() => {
      if (isMounted) {
        fetchLinks(page, debouncedSearch);
      }
    }, 0);
    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [fetchLinks, page, debouncedSearch]);

  // Handle Search Input Change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchInput(e.target.value);
  };

  // Create Link Submit Handler
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);

    const cleanUrl = destinationUrl.trim();
    if (!cleanUrl) {
      setCreateError('Please enter a destination URL.');
      return;
    }

    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      setCreateError('Destination URL must start with http:// or https://');
      return;
    }

    setIsCreating(true);
    try {
      const payload: { destinationUrl: string; customSlug?: string; title?: string } = {
        destinationUrl: cleanUrl,
      };
      if (customSlug.trim()) {
        payload.customSlug = customSlug.trim().toLowerCase();
      }
      if (title.trim()) {
        payload.title = title.trim();
      }

      const res = await api.post<LinkItem>('/links', payload);
      toast.success('Short link created successfully!');
      setRecentlyCreated(res.data);

      // Reset form
      setDestinationUrl('');
      setCustomSlug('');
      setTitle('');

      // Refresh list
      fetchLinks(1, debouncedSearch);
    } catch (err) {
      if (err instanceof AxiosError && err.response?.data?.detail) {
        setCreateError(err.response.data.detail);
      } else {
        setCreateError('Failed to create short link. Please check your inputs.');
      }
    } finally {
      setIsCreating(false);
    }
  };

  // Copy to clipboard helper
  const handleCopy = async (url: string, id: string) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = url;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopiedId(id);
      toast.success('Short link copied to clipboard!');
      setTimeout(() => setCopiedId(null), 2500);
    } catch {
      toast.error('Could not copy link to clipboard');
    }
  };

  // Delete link execution handler (invoked by DeleteConfirmModal)
  const confirmDelete = async () => {
    if (!deleteModalLink) return;

    setDeletingId(deleteModalLink.id);
    try {
      await api.delete(`/links/${deleteModalLink.id}`);
      toast.success('Link deleted successfully');
      if (recentlyCreated?.id === deleteModalLink.id) {
        setRecentlyCreated(null);
      }
      setDeleteModalLink(null);
      fetchLinks(page, debouncedSearch);
    } catch {
      toast.error('Failed to delete link');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-gray-100 flex flex-col">
      {/* Header */}
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
                className="px-3 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
              >
                Dashboard
              </Link>
              <Link
                to="/links"
                className="px-3 py-1.5 rounded-lg bg-white/10 text-white font-medium flex items-center gap-1.5"
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
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs">
              <User className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-gray-300 font-medium">@{user?.username}</span>
            </div>

            <button
              onClick={() => logout()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-red-500/20 text-gray-300 hover:text-red-300 border border-white/10 transition-colors text-xs font-semibold cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Page Title */}
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Short Links
          </h1>
          <p className="mt-1 text-sm text-gray-400">
            Create, manage, and share short URLs with custom vanity slugs
          </p>
        </div>

        {/* Create Link Card */}
        <div className="rounded-2xl bg-gradient-to-b from-white/[0.08] to-white/[0.03] border border-white/10 p-6 sm:p-8 backdrop-blur-sm shadow-xl">
          <div className="flex items-center gap-2 text-sm font-semibold text-indigo-400 uppercase tracking-wider mb-4">
            <Plus className="w-4 h-4" />
            <span>Create New Short Link</span>
          </div>

          {createError && (
            <div className="mb-5 flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/30 p-4 text-red-300 text-sm animate-in fade-in duration-200">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <span>{createError}</span>
            </div>
          )}

          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
              {/* Destination URL */}
              <div className="md:col-span-6">
                <label htmlFor="destination-url" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                  Destination URL <span className="text-indigo-400">*</span>
                </label>
                <input
                  id="destination-url"
                  type="url"
                  value={destinationUrl}
                  onChange={(e) => setDestinationUrl(e.target.value)}
                  placeholder="https://example.com/very/long/destination/url"
                  required
                  disabled={isCreating}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/15 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm"
                />
              </div>

              {/* Custom Slug */}
              <div className="md:col-span-3">
                <label htmlFor="custom-slug" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                  Custom Slug <span className="text-gray-500 font-normal">(Optional)</span>
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs font-mono">/r/</span>
                  <input
                    id="custom-slug"
                    type="text"
                    value={customSlug}
                    onChange={(e) => setCustomSlug(e.target.value.toLowerCase())}
                    placeholder="my-sale"
                    disabled={isCreating}
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-black/40 border border-white/15 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm font-mono"
                  />
                </div>
              </div>

              {/* Title / Label */}
              <div className="md:col-span-3">
                <label htmlFor="link-title" className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                  Title / Label <span className="text-gray-500 font-normal">(Optional)</span>
                </label>
                <input
                  id="link-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Summer Promotion"
                  disabled={isCreating}
                  className="w-full px-4 py-2.5 rounded-xl bg-black/40 border border-white/15 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={isCreating}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-medium text-sm shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Shortening...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Create Short Link</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Recently Created Highlight Banner */}
          {recentlyCreated && (
            <div className="mt-6 pt-6 border-t border-white/10 animate-in fade-in zoom-in-95 duration-300">
              <div className="rounded-xl bg-indigo-600/10 border border-indigo-500/30 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Ready to Share</span>
                  </div>
                  <p className="text-sm font-mono font-bold text-white tracking-wide">
                    {recentlyCreated.shortUrl}
                  </p>
                  <p className="text-xs text-gray-400 truncate max-w-md">
                    Target: {recentlyCreated.destinationUrl}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => setQrModalLink(recentlyCreated)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-all cursor-pointer"
                    title="Generate QR code"
                  >
                    <QrCode className="w-4 h-4 text-indigo-400" />
                    <span>QR</span>
                  </button>

                  <Link
                    to={`/analytics/${recentlyCreated.id}`}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-all cursor-pointer"
                  >
                    <BarChart3 className="w-4 h-4 text-indigo-400" />
                    <span>Analytics</span>
                  </Link>

                  <button
                    onClick={() => handleCopy(recentlyCreated.shortUrl, recentlyCreated.id)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow transition-all cursor-pointer"
                  >
                    {copiedId === recentlyCreated.id ? (
                      <>
                        <Check className="w-4 h-4 text-emerald-300" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        <span>Copy Short URL</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Links Table & List View */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Your Links</span>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-white/10 text-indigo-300 border border-white/10 font-normal">
                {total} total
              </span>
            </h2>

            {/* Search Bar */}
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchInput}
                onChange={handleSearchChange}
                placeholder="Search links..."
                className="w-full pl-9 pr-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              />
            </div>
          </div>

          {/* Links List Cards / Table */}
          {isLoadingList ? (
            <div className="rounded-2xl bg-white/5 border border-white/10 p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mx-auto mb-2" />
              <p className="text-xs text-gray-400">Loading your links...</p>
            </div>
          ) : links.length === 0 ? (
            <div className="rounded-2xl bg-white/5 border border-white/10 p-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto border border-indigo-500/20">
                <Link2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-semibold text-white">No short links found</h3>
              <p className="text-xs text-gray-400 max-w-sm mx-auto">
                {debouncedSearch
                  ? `No links matching "${debouncedSearch}". Try clearing your search.`
                  : "You haven't created any short links yet. Use the form above to shorten your first link."}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {links.map((link) => (
                <div
                  key={link.id}
                  className="rounded-2xl bg-white/5 border border-white/10 p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-indigo-500/40 transition-colors"
                >
                  {/* Link Details */}
                  <div className="space-y-1.5 min-w-0 flex-1">
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-sm text-indigo-300">
                        /r/{link.shortCode}
                      </span>
                      {link.title && (
                        <span className="text-xs font-semibold text-gray-200 truncate">
                          {link.title}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-gray-400 truncate max-w-xl">
                      <ExternalLink className="w-3 h-3 flex-shrink-0 text-gray-500" />
                      <span className="truncate">{link.destinationUrl}</span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-gray-500 pt-1">
                      <span className="flex items-center gap-1">
                        <MousePointerClick className="w-3.5 h-3.5 text-indigo-400" />
                        <span className="text-gray-300 font-medium">{link.clickCount} clicks</span>
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        <span>{new Date(link.createdAt).toLocaleDateString()}</span>
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 self-end md:self-center flex-shrink-0 flex-wrap">
                    {/* Analytics */}
                    <Link
                      to={`/analytics/${link.id}`}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 hover:text-white border border-indigo-500/30 text-xs font-semibold transition-colors cursor-pointer"
                      title="View link analytics"
                    >
                      <BarChart3 className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Analytics</span>
                    </Link>

                    {/* QR Code */}
                    <button
                      type="button"
                      onClick={() => setQrModalLink(link)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white border border-white/10 text-xs font-semibold transition-colors cursor-pointer"
                      title="Generate and customize QR code"
                    >
                      <QrCode className="w-3.5 h-3.5 text-indigo-400" />
                      <span className="hidden sm:inline">QR</span>
                    </button>

                    {/* Copy URL */}
                    <button
                      type="button"
                      onClick={() => handleCopy(link.shortUrl, link.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-colors cursor-pointer"
                      title="Copy short link"
                    >
                      {copiedId === link.id ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy URL</span>
                        </>
                      )}
                    </button>

                    {/* Delete */}
                    <button
                      type="button"
                      onClick={() => setDeleteModalLink(link)}
                      disabled={deletingId === link.id}
                      className="p-1.5 rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer disabled:opacity-50"
                      title="Delete short link"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-white/10 text-xs text-gray-400">
              <span>
                Page {page} of {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1 || isLoadingList}
                  className="p-2 rounded-xl bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-white cursor-pointer"
                  title="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages || isLoadingList}
                  className="p-2 rounded-xl bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-white cursor-pointer"
                  title="Next page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* QR Code Customization & Export Dialog */}
      {qrModalLink && (
        <QrCodeModal
          isOpen={Boolean(qrModalLink)}
          onClose={() => setQrModalLink(null)}
          shortCode={qrModalLink.shortCode}
          destinationUrl={qrModalLink.destinationUrl}
          title={qrModalLink.title}
        />
      )}

      {/* Accessible Delete Confirmation Dialog */}
      {deleteModalLink && (
        <DeleteConfirmModal
          isOpen={Boolean(deleteModalLink)}
          onClose={() => setDeleteModalLink(null)}
          onConfirm={confirmDelete}
          shortCode={deleteModalLink.shortCode}
          isDeleting={deletingId === deleteModalLink.id}
        />
      )}
    </div>
  );
};
