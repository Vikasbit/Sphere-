import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Link2,
  Copy,
  Check,
  ExternalLink,
  Plus,
  Trash2,
  Edit2,
  ChevronUp,
  ChevronDown,
  Eye,
  EyeOff,
  User,
  LogOut,
  Zap,
  Palette,
  Sparkles,
  Share2,
  Loader2,
  Save,
  CheckCircle2,
} from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../context/useAuth';
import toast from 'react-hot-toast';
import type {
  BioProfile,
  BioLinkItem,
  SocialLinkItem,
  UpdateBioProfilePayload,
} from '../types/bio';
import { renderSocialIcon } from '../components/SocialIcons';

// Theme presets
const THEME_PRESETS = [
  {
    name: 'Midnight',
    bg: '#0F172A',
    btn: '#1E293B',
    text: '#F8FAFC',
    border: 'border-slate-700',
  },
  {
    name: 'Minimal Light',
    bg: '#FFFFFF',
    btn: '#F1F5F9',
    text: '#0F172A',
    border: 'border-slate-300',
  },
  {
    name: 'Cyber Indigo',
    bg: '#1E1B4B',
    btn: '#4338CA',
    text: '#EEF2FF',
    border: 'border-indigo-600',
  },
  {
    name: 'Warm Sunset',
    bg: '#78350F',
    btn: '#B45309',
    text: '#FEF3C7',
    border: 'border-amber-700',
  },
  {
    name: 'Emerald Forest',
    bg: '#064E3B',
    btn: '#047857',
    text: '#ECFDF5',
    border: 'border-emerald-600',
  },
  {
    name: 'Rose Velvet',
    bg: '#4C0519',
    btn: '#9F1239',
    text: '#FFE4E6',
    border: 'border-rose-700',
  },
];

const SOCIAL_PLATFORMS = [
  { id: 'instagram', label: 'Instagram' },
  { id: 'twitter', label: 'Twitter / X' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'facebook', label: 'Facebook' },
  { id: 'github', label: 'GitHub' },
  { id: 'website', label: 'Website / Blog' },
];

export const BioBuilderPage: React.FC = () => {
  const { user, logout } = useAuth();

  // Active editor tab
  const [activeTab, setActiveTab] = useState<'profile' | 'links' | 'socials' | 'appearance'>('profile');

  // Profile data
  const [profile, setProfile] = useState<BioProfile | null>(null);
  const [links, setLinks] = useState<BioLinkItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Profile form state
  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [backgroundColor, setBackgroundColor] = useState('#0F172A');
  const [buttonColor, setButtonColor] = useState('#1E293B');
  const [textColor, setTextColor] = useState('#F8FAFC');
  const [isPublished, setIsPublished] = useState(true);
  const [socialLinks, setSocialLinks] = useState<SocialLinkItem[]>([]);

  // New social input state
  const [newPlatform, setNewPlatform] = useState('github');
  const [newSocialUrl, setNewSocialUrl] = useState('');

  // Link management state
  const [showAddLinkForm, setShowAddLinkForm] = useState(false);
  const [newLinkTitle, setNewLinkTitle] = useState('');
  const [newLinkUrl, setNewLinkUrl] = useState('');
  const [isAddingLink, setIsAddingLink] = useState(false);

  // Edit link modal/state
  const [editingLink, setEditingLink] = useState<BioLinkItem | null>(null);
  const [editLinkTitle, setEditLinkTitle] = useState('');
  const [editLinkUrl, setEditLinkUrl] = useState('');
  const [isUpdatingLink, setIsUpdatingLink] = useState(false);

  // UI helpers
  const [copiedLink, setCopiedLink] = useState(false);

  // Fetch initial profile and links
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [profileRes, linksRes] = await Promise.all([
        api.get<BioProfile>('/bio'),
        api.get<BioLinkItem[]>('/bio/links'),
      ]);

      const prof = profileRes.data;
      setProfile(prof);
      setDisplayName(prof.displayName || '');
      setBio(prof.bio || '');
      setAvatarUrl(prof.avatarUrl || '');
      setBackgroundColor(prof.backgroundColor || '#0F172A');
      setButtonColor(prof.buttonColor || '#1E293B');
      setTextColor(prof.textColor || '#F8FAFC');
      setIsPublished(prof.isPublished);
      setSocialLinks(prof.socialLinks || []);

      setLinks(linksRes.data || []);
      setHasUnsavedChanges(false);
    } catch {
      toast.error('Failed to load bio profile');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const timer = setTimeout(() => {
      if (isMounted) {
        fetchData();
      }
    }, 0);
    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [fetchData]);

  // Track unsaved changes for profile fields
  const handleProfileFieldChange = () => {
    setHasUnsavedChanges(true);
  };

  // Save profile changes to backend
  const handleSaveProfile = async (publishOverride?: boolean) => {
    setIsSaving(true);
    const publishedVal = publishOverride !== undefined ? publishOverride : isPublished;

    const payload: UpdateBioProfilePayload = {
      displayName: displayName.trim() || (user?.username || 'Creator'),
      bio: bio.trim(),
      avatarUrl: avatarUrl.trim() || null,
      backgroundColor: backgroundColor.toUpperCase(),
      buttonColor: buttonColor.toUpperCase(),
      textColor: textColor.toUpperCase(),
      isPublished: publishedVal,
      socialLinks,
    };

    try {
      const res = await api.put<BioProfile>('/bio', payload);
      setProfile(res.data);
      setIsPublished(res.data.isPublished);
      setHasUnsavedChanges(false);
      toast.success(
        publishOverride !== undefined
          ? publishOverride
            ? 'Bio page published!'
            : 'Bio page saved as draft'
          : 'Profile saved successfully!'
      );
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr.response?.data?.detail || 'Failed to update bio profile');
    } finally {
      setIsSaving(false);
    }
  };

  // Toggle publish status immediately
  const handleTogglePublish = async () => {
    const nextState = !isPublished;
    setIsPublished(nextState);
    await handleSaveProfile(nextState);
  };

  // Copy public link to clipboard
  const handleCopyPublicUrl = () => {
    if (!profile) return;
    const url = `${window.location.origin}/bio/${profile.username}`;
    navigator.clipboard.writeText(url);
    setCopiedLink(true);
    toast.success('Public bio link copied!');
    setTimeout(() => setCopiedLink(false), 2000);
  };

  // Social Links management
  const handleAddSocial = () => {
    if (!newSocialUrl.trim()) {
      toast.error('Please enter a valid URL');
      return;
    }
    const cleanUrl = newSocialUrl.trim();
    if (!/^https?:\/\//i.test(cleanUrl)) {
      toast.error('URL must start with http:// or https://');
      return;
    }

    // Check if platform already added
    const exists = socialLinks.some((item) => item.platform.toLowerCase() === newPlatform.toLowerCase());
    if (exists) {
      setSocialLinks(
        socialLinks.map((item) =>
          item.platform.toLowerCase() === newPlatform.toLowerCase() ? { ...item, url: cleanUrl } : item
        )
      );
      toast.success(`Updated ${newPlatform} link`);
    } else {
      setSocialLinks([...socialLinks, { platform: newPlatform, url: cleanUrl }]);
      toast.success(`Added ${newPlatform} link`);
    }
    setNewSocialUrl('');
    setHasUnsavedChanges(true);
  };

  const handleRemoveSocial = (platform: string) => {
    setSocialLinks(socialLinks.filter((item) => item.platform !== platform));
    setHasUnsavedChanges(true);
    toast.success(`Removed ${platform}`);
  };

  // Bio Links CRUD
  const handleAddLink = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLinkTitle.trim() || !newLinkUrl.trim()) {
      toast.error('Title and destination URL are required');
      return;
    }

    setIsAddingLink(true);
    try {
      const res = await api.post<BioLinkItem>('/bio/links', {
        title: newLinkTitle.trim(),
        url: newLinkUrl.trim(),
        isVisible: true,
      });
      setLinks([...links, res.data]);
      setNewLinkTitle('');
      setNewLinkUrl('');
      setShowAddLinkForm(false);
      toast.success('Bio link added!');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr.response?.data?.detail || 'Failed to add link');
    } finally {
      setIsAddingLink(false);
    }
  };

  const handleToggleLinkVisibility = async (link: BioLinkItem) => {
    const updatedVisible = !link.isVisible;
    try {
      const res = await api.put<BioLinkItem>(`/bio/links/${link.id}`, {
        isVisible: updatedVisible,
      });
      setLinks(links.map((l) => (l.id === link.id ? res.data : l)));
      toast.success(updatedVisible ? 'Link is now visible' : 'Link is now hidden');
    } catch {
      toast.error('Failed to toggle visibility');
    }
  };

  const handleDeleteLink = async (id: string) => {
    try {
      await api.delete(`/bio/links/${id}`);
      setLinks(links.filter((l) => l.id !== id));
      toast.success('Link deleted');
    } catch {
      toast.error('Failed to delete link');
    }
  };

  const handleEditLinkSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLink) return;
    if (!editLinkTitle.trim() || !editLinkUrl.trim()) {
      toast.error('Title and destination URL are required');
      return;
    }

    setIsUpdatingLink(true);
    try {
      const res = await api.put<BioLinkItem>(`/bio/links/${editingLink.id}`, {
        title: editLinkTitle.trim(),
        url: editLinkUrl.trim(),
      });
      setLinks(links.map((l) => (l.id === editingLink.id ? res.data : l)));
      setEditingLink(null);
      toast.success('Link updated successfully');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr.response?.data?.detail || 'Failed to update link');
    } finally {
      setIsUpdatingLink(false);
    }
  };

  // Reordering Links (Up / Down)
  const handleMoveLink = async (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === links.length - 1) return;

    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    const newLinks = [...links];
    const temp = newLinks[index];
    newLinks[index] = newLinks[targetIndex];
    newLinks[targetIndex] = temp;

    // Optimistically update UI
    setLinks(newLinks);

    try {
      const linkIds = newLinks.map((l) => l.id);
      await api.patch<BioLinkItem[]>('/bio/links/reorder', { linkIds });
    } catch {
      toast.error('Failed to save link order');
      // Revert on error
      fetchData();
    }
  };

  const applyPresetTheme = (preset: typeof THEME_PRESETS[number]) => {
    setBackgroundColor(preset.bg);
    setButtonColor(preset.btn);
    setTextColor(preset.text);
    setHasUnsavedChanges(true);
    toast.success(`Applied ${preset.name} theme`);
  };

  const publicBioUrl = profile ? `${window.location.origin}/bio/${profile.username}` : '';

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mb-4" />
        <p className="text-slate-400 font-medium text-sm">Loading bio editor...</p>
      </div>
    );
  }

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
                className="px-3 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
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
                className="px-3 py-1.5 rounded-lg bg-white/10 text-white font-medium flex items-center gap-1.5"
              >
                <Share2 className="w-3.5 h-3.5 text-indigo-400" />
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

      {/* Builder Top Bar / Controls */}
      <section className="border-b border-white/10 bg-slate-900/40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
                <span>Bio-Link Builder</span>
                {isPublished ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Live
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    Draft
                  </span>
                )}
              </h1>
              <p className="text-xs text-gray-400 mt-0.5 flex flex-wrap items-center gap-1.5">
                <span>Public link:</span>
                <span className="font-mono text-indigo-400 font-medium">{publicBioUrl}</span>
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Publish Toggle Button */}
            <button
              onClick={handleTogglePublish}
              disabled={isSaving}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 cursor-pointer ${
                isPublished
                  ? 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border-amber-500/30'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white border-transparent shadow-lg shadow-emerald-600/20'
              }`}
            >
              {isPublished ? 'Unpublish' : 'Publish Page'}
            </button>

            {/* Copy Public Link */}
            <button
              onClick={handleCopyPublicUrl}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white/5 hover:bg-white/10 text-gray-200 border border-white/10 transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedLink ? 'Copied URL' : 'Copy Bio Link'}</span>
            </button>

            {/* Open Live Bio */}
            <a
              href={`/bio/${profile?.username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-lg shadow-indigo-600/20 cursor-pointer"
            >
              <span>View Live</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>

            {/* Save Button */}
            <button
              onClick={() => handleSaveProfile()}
              disabled={isSaving || !hasUnsavedChanges}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
                hasUnsavedChanges
                  ? 'bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white shadow-lg shadow-indigo-500/25 ring-2 ring-indigo-400/50'
                  : 'bg-white/5 text-gray-500 border border-white/5 cursor-not-allowed'
              }`}
            >
              {isSaving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : hasUnsavedChanges ? (
                <Save className="w-3.5 h-3.5" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              )}
              <span>{isSaving ? 'Saving...' : hasUnsavedChanges ? 'Save Changes' : 'Saved'}</span>
            </button>
          </div>
        </div>
      </section>

      {/* Main Workspace (Split Grid) */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* ========================================================
              LEFT COLUMN: Editor Controls & Tabs
             ======================================================== */}
          <div className="lg:col-span-7 space-y-6">
            {/* Navigation Tabs */}
            <div className="flex border-b border-white/10 bg-slate-900/60 p-1.5 rounded-2xl gap-1">
              <button
                onClick={() => setActiveTab('profile')}
                className={`flex-1 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                  activeTab === 'profile'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <User className="w-4 h-4" />
                <span>Profile</span>
              </button>

              <button
                onClick={() => setActiveTab('links')}
                className={`flex-1 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                  activeTab === 'links'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Link2 className="w-4 h-4" />
                <span>Links ({links.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('socials')}
                className={`flex-1 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                  activeTab === 'socials'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Share2 className="w-4 h-4" />
                <span>Socials ({socialLinks.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('appearance')}
                className={`flex-1 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                  activeTab === 'appearance'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Palette className="w-4 h-4" />
                <span>Theme</span>
              </button>
            </div>

            {/* TAB 1: PROFILE INFO */}
            {activeTab === 'profile' && (
              <div className="rounded-2xl bg-white/[0.04] border border-white/10 p-6 sm:p-8 space-y-6 backdrop-blur-sm">
                <div>
                  <h2 className="text-lg font-bold text-white">Profile Details</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Basic information visible to everyone visiting your public page.
                  </p>
                </div>

                <div className="space-y-4">
                  {/* Display Name */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                      Display Name
                    </label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => {
                        setDisplayName(e.target.value);
                        handleProfileFieldChange();
                      }}
                      maxLength={60}
                      placeholder="e.g. Sarah Connor"
                      className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-gray-600"
                    />
                  </div>

                  {/* Avatar URL */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                      Avatar Image URL
                    </label>
                    <input
                      type="url"
                      value={avatarUrl}
                      onChange={(e) => {
                        setAvatarUrl(e.target.value);
                        handleProfileFieldChange();
                      }}
                      placeholder="https://example.com/avatar.jpg"
                      className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-gray-600"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Direct link to an image (JPG, PNG, WebP). Leave blank to display your initials.
                    </p>
                  </div>

                  {/* Bio */}
                  <div>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300">
                        Biography
                      </label>
                      <span className="text-xs text-gray-500">{bio.length}/300</span>
                    </div>
                    <textarea
                      value={bio}
                      onChange={(e) => {
                        setBio(e.target.value);
                        handleProfileFieldChange();
                      }}
                      maxLength={300}
                      rows={4}
                      placeholder="Write a short summary about who you are, what you create, or why people should connect with you..."
                      className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-gray-600 resize-none"
                    />
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => handleSaveProfile()}
                    disabled={isSaving || !hasUnsavedChanges}
                    className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-all shadow-md shadow-indigo-600/25 cursor-pointer"
                  >
                    {isSaving ? 'Saving...' : 'Save Profile'}
                  </button>
                </div>
              </div>
            )}

            {/* TAB 2: BIO LINKS */}
            {activeTab === 'links' && (
              <div className="space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-white">Custom Bio Links</h2>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Add and reorder buttons displayed on your public bio.
                    </p>
                  </div>

                  {!showAddLinkForm && (
                    <button
                      onClick={() => setShowAddLinkForm(true)}
                      className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 shadow-md shadow-indigo-600/20 cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Link</span>
                    </button>
                  )}
                </div>

                {/* Add Link Form Card */}
                {showAddLinkForm && (
                  <div className="rounded-2xl bg-slate-900/90 border border-indigo-500/40 p-5 space-y-4 shadow-xl animate-in fade-in duration-200">
                    <div className="flex items-center justify-between border-b border-white/10 pb-3">
                      <h3 className="text-sm font-bold text-indigo-400 flex items-center gap-1.5">
                        <Plus className="w-4 h-4" />
                        <span>Add New Bio Link</span>
                      </h3>
                      <button
                        onClick={() => setShowAddLinkForm(false)}
                        className="text-gray-400 hover:text-white text-xs cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>

                    <form onSubmit={handleAddLink} className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1">
                          Link Title <span className="text-indigo-400">*</span>
                        </label>
                        <input
                          type="text"
                          value={newLinkTitle}
                          onChange={(e) => setNewLinkTitle(e.target.value)}
                          maxLength={80}
                          placeholder="e.g. Read My Latest Blog Post"
                          required
                          className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1">
                          Destination URL <span className="text-indigo-400">*</span>
                        </label>
                        <input
                          type="url"
                          value={newLinkUrl}
                          onChange={(e) => setNewLinkUrl(e.target.value)}
                          placeholder="https://example.com/article"
                          required
                          className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                        />
                      </div>

                      <div className="flex justify-end gap-2 pt-2">
                        <button
                          type="button"
                          onClick={() => setShowAddLinkForm(false)}
                          className="px-4 py-2 rounded-xl text-xs font-semibold text-gray-400 hover:text-white bg-white/5 cursor-pointer"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          disabled={isAddingLink}
                          className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white flex items-center gap-1.5 shadow-md shadow-indigo-600/25 cursor-pointer"
                        >
                          {isAddingLink && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                          <span>Add Link</span>
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* Edit Link Modal/Card */}
                {editingLink && (
                  <div className="rounded-2xl bg-slate-900/90 border border-amber-500/40 p-5 space-y-4 shadow-xl">
                    <div className="flex items-center justify-between border-b border-white/10 pb-3">
                      <h3 className="text-sm font-bold text-amber-400 flex items-center gap-1.5">
                        <Edit2 className="w-4 h-4" />
                        <span>Edit Bio Link</span>
                      </h3>
                      <button
                        onClick={() => setEditingLink(null)}
                        className="text-gray-400 hover:text-white text-xs cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>

                    <form onSubmit={handleEditLinkSubmit} className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1">
                          Link Title
                        </label>
                        <input
                          type="text"
                          value={editLinkTitle}
                          onChange={(e) => setEditLinkTitle(e.target.value)}
                          maxLength={80}
                          required
                          className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1">
                          Destination URL
                        </label>
                        <input
                          type="url"
                          value={editLinkUrl}
                          onChange={(e) => setEditLinkUrl(e.target.value)}
                          required
                          className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                        />
                      </div>

                      <div className="flex justify-end gap-2 pt-2">
                        <button
                          type="button"
                          onClick={() => setEditingLink(null)}
                          className="px-4 py-2 rounded-xl text-xs font-semibold text-gray-400 hover:text-white bg-white/5 cursor-pointer"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          disabled={isUpdatingLink}
                          className="px-5 py-2 rounded-xl text-xs font-semibold bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white flex items-center gap-1.5 shadow-md shadow-amber-600/25 cursor-pointer"
                        >
                          {isUpdatingLink && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                          <span>Update Link</span>
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* List of Links */}
                <div className="space-y-3">
                  {links.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-gray-400 bg-white/[0.02]">
                      <Link2 className="w-8 h-8 text-gray-600 mx-auto mb-3" />
                      <p className="text-sm font-medium text-gray-300">No links added yet</p>
                      <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                        Add destination links to showcase your projects, articles, videos, or stores.
                      </p>
                      <button
                        onClick={() => setShowAddLinkForm(true)}
                        className="mt-4 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white inline-flex items-center gap-1.5 shadow-md cursor-pointer"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add Your First Link</span>
                      </button>
                    </div>
                  ) : (
                    links.map((link, index) => (
                      <div
                        key={link.id}
                        className={`rounded-xl border transition-all p-4 flex items-center justify-between gap-4 ${
                          link.isVisible
                            ? 'bg-slate-900/80 border-white/10 hover:border-white/20'
                            : 'bg-slate-900/30 border-white/5 opacity-60'
                        }`}
                      >
                        {/* Position Controls & Info */}
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex flex-col gap-1">
                            <button
                              onClick={() => handleMoveLink(index, 'up')}
                              disabled={index === 0}
                              title="Move link up"
                              className="p-1 rounded bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white disabled:opacity-20 disabled:cursor-not-allowed cursor-pointer"
                            >
                              <ChevronUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleMoveLink(index, 'down')}
                              disabled={index === links.length - 1}
                              title="Move link down"
                              className="p-1 rounded bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white disabled:opacity-20 disabled:cursor-not-allowed cursor-pointer"
                            >
                              <ChevronDown className="w-3.5 h-3.5" />
                            </button>
                          </div>

                          <div className="min-w-0">
                            <h4 className="text-sm font-semibold text-white truncate flex items-center gap-2">
                              <span>{link.title}</span>
                              {!link.isVisible && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 font-normal">
                                  Hidden
                                </span>
                              )}
                            </h4>
                            <p className="text-xs text-gray-500 truncate mt-0.5">{link.url}</p>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <button
                            onClick={() => handleToggleLinkVisibility(link)}
                            title={link.isVisible ? 'Hide link' : 'Show link'}
                            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white transition-colors cursor-pointer"
                          >
                            {link.isVisible ? <Eye className="w-4 h-4 text-emerald-400" /> : <EyeOff className="w-4 h-4 text-gray-500" />}
                          </button>

                          <button
                            onClick={() => {
                              setEditingLink(link);
                              setEditLinkTitle(link.title);
                              setEditLinkUrl(link.url);
                            }}
                            title="Edit link"
                            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white transition-colors cursor-pointer"
                          >
                            <Edit2 className="w-4 h-4 text-indigo-400" />
                          </button>

                          <button
                            onClick={() => handleDeleteLink(link.id)}
                            title="Delete link"
                            className="p-2 rounded-lg bg-white/5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* TAB 3: SOCIAL ICONS */}
            {activeTab === 'socials' && (
              <div className="rounded-2xl bg-white/[0.04] border border-white/10 p-6 sm:p-8 space-y-6 backdrop-blur-sm">
                <div>
                  <h2 className="text-lg font-bold text-white">Social Channel Links</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Showcase clickable social icons directly below your avatar and bio.
                  </p>
                </div>

                {/* Add Social Bar */}
                <div className="p-4 rounded-xl bg-slate-900 border border-white/10 space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                    <div className="sm:col-span-4">
                      <label className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1">
                        Platform
                      </label>
                      <select
                        value={newPlatform}
                        onChange={(e) => setNewPlatform(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        {SOCIAL_PLATFORMS.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="sm:col-span-8">
                      <label className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1">
                        Profile URL
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="url"
                          value={newSocialUrl}
                          onChange={(e) => setNewSocialUrl(e.target.value)}
                          placeholder="https://..."
                          className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        <button
                          type="button"
                          onClick={handleAddSocial}
                          className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1 cursor-pointer flex-shrink-0"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          <span>Add</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* List of Active Socials */}
                <div className="space-y-2.5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                    Active Social Profiles ({socialLinks.length})
                  </h3>

                  {socialLinks.length === 0 ? (
                    <p className="text-xs text-gray-500 italic py-2">
                      No social links added yet. Add Instagram, GitHub, LinkedIn, or X above!
                    </p>
                  ) : (
                    socialLinks.map((item, idx) => (
                      <div
                        key={`${item.platform}-${idx}`}
                        className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-white/10"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="p-2 rounded-lg bg-white/5 text-indigo-400">
                            {renderSocialIcon(item.platform, 'w-4 h-4')}
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-semibold text-white capitalize">{item.platform}</p>
                            <p className="text-[11px] text-gray-500 truncate">{item.url}</p>
                          </div>
                        </div>

                        <button
                          onClick={() => handleRemoveSocial(item.platform)}
                          title="Remove social link"
                          className="p-1.5 rounded-lg bg-white/5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => handleSaveProfile()}
                    disabled={isSaving || !hasUnsavedChanges}
                    className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition-all cursor-pointer"
                  >
                    {isSaving ? 'Saving...' : 'Save Socials'}
                  </button>
                </div>
              </div>
            )}

            {/* TAB 4: THEME & APPEARANCE */}
            {activeTab === 'appearance' && (
              <div className="rounded-2xl bg-white/[0.04] border border-white/10 p-6 sm:p-8 space-y-6 backdrop-blur-sm">
                <div>
                  <h2 className="text-lg font-bold text-white">Theme & Styling</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Customize background, button cards, and text styling for your page.
                  </p>
                </div>

                {/* Presets */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-3">
                    Curated Color Presets
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {THEME_PRESETS.map((preset) => {
                      const isActive =
                        backgroundColor.toUpperCase() === preset.bg.toUpperCase() &&
                        buttonColor.toUpperCase() === preset.btn.toUpperCase();
                      return (
                        <button
                          key={preset.name}
                          type="button"
                          onClick={() => applyPresetTheme(preset)}
                          className={`p-3 rounded-xl text-left border transition-all cursor-pointer ${
                            isActive
                              ? 'border-indigo-500 ring-2 ring-indigo-500/30 bg-white/10'
                              : 'border-white/10 bg-slate-900/60 hover:bg-white/5'
                          }`}
                        >
                          <div className="flex items-center gap-1.5 mb-2">
                            <div
                              className="w-4 h-4 rounded-full border border-white/20 shadow-sm"
                              style={{ backgroundColor: preset.bg }}
                            />
                            <div
                              className="w-4 h-4 rounded-full border border-white/20 shadow-sm"
                              style={{ backgroundColor: preset.btn }}
                            />
                            <div
                              className="w-4 h-4 rounded-full border border-white/20 shadow-sm"
                              style={{ backgroundColor: preset.text }}
                            />
                          </div>
                          <span className="text-xs font-semibold text-white block truncate">
                            {preset.name}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Custom Color Pickers */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                  {/* Background Color */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                      Background Color
                    </label>
                    <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900 border border-white/10">
                      <input
                        type="color"
                        value={backgroundColor}
                        onChange={(e) => {
                          setBackgroundColor(e.target.value);
                          handleProfileFieldChange();
                        }}
                        className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0"
                      />
                      <input
                        type="text"
                        value={backgroundColor}
                        onChange={(e) => {
                          setBackgroundColor(e.target.value);
                          handleProfileFieldChange();
                        }}
                        maxLength={7}
                        className="w-full text-xs font-mono text-white bg-transparent border-0 focus:outline-none uppercase"
                      />
                    </div>
                  </div>

                  {/* Button Color */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                      Button Card Color
                    </label>
                    <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900 border border-white/10">
                      <input
                        type="color"
                        value={buttonColor}
                        onChange={(e) => {
                          setButtonColor(e.target.value);
                          handleProfileFieldChange();
                        }}
                        className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0"
                      />
                      <input
                        type="text"
                        value={buttonColor}
                        onChange={(e) => {
                          setButtonColor(e.target.value);
                          handleProfileFieldChange();
                        }}
                        maxLength={7}
                        className="w-full text-xs font-mono text-white bg-transparent border-0 focus:outline-none uppercase"
                      />
                    </div>
                  </div>

                  {/* Text Color */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1.5">
                      Text & Icon Color
                    </label>
                    <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900 border border-white/10">
                      <input
                        type="color"
                        value={textColor}
                        onChange={(e) => {
                          setTextColor(e.target.value);
                          handleProfileFieldChange();
                        }}
                        className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0"
                      />
                      <input
                        type="text"
                        value={textColor}
                        onChange={(e) => {
                          setTextColor(e.target.value);
                          handleProfileFieldChange();
                        }}
                        maxLength={7}
                        className="w-full text-xs font-mono text-white bg-transparent border-0 focus:outline-none uppercase"
                      />
                    </div>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => handleSaveProfile()}
                    disabled={isSaving || !hasUnsavedChanges}
                    className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition-all cursor-pointer"
                  >
                    {isSaving ? 'Saving...' : 'Save Theme'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* ========================================================
              RIGHT COLUMN: Live Mobile Mockup Preview
             ======================================================== */}
          <div className="lg:col-span-5 flex flex-col items-center">
            <div className="sticky top-24 w-full flex flex-col items-center">
              <div className="flex items-center justify-between w-full max-w-[340px] mb-3 px-2">
                <span className="text-xs font-semibold text-gray-400 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  Live Mobile Preview
                </span>
                <span className="text-[11px] text-gray-500">Updates in real-time</span>
              </div>

              {/* Smartphone Frame */}
              <div className="w-full max-w-[340px] h-[640px] rounded-[44px] p-3 bg-slate-800/80 border-4 border-slate-700 shadow-2xl relative flex flex-col overflow-hidden backdrop-blur-md">
                {/* Dynamic Island / Speaker notch */}
                <div className="absolute top-4 left-1/2 -translate-x-1/2 w-24 h-4 bg-black rounded-full z-20" />

                {/* Inner Screen */}
                <div
                  className="w-full h-full rounded-[34px] overflow-y-auto pt-10 pb-8 px-4 flex flex-col items-center justify-between relative select-none scrollbar-none transition-colors duration-200"
                  style={{
                    backgroundColor,
                    color: textColor,
                  }}
                >
                  <div className="w-full flex flex-col items-center">
                    {/* Mockup Avatar */}
                    <div className="w-18 h-18 rounded-full mb-3 flex items-center justify-center shadow-lg ring-2 ring-white/10 overflow-hidden">
                      {avatarUrl ? (
                        <img
                          src={avatarUrl}
                          alt="preview avatar"
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      ) : (
                        <div
                          className="w-full h-full flex items-center justify-center font-bold text-lg"
                          style={{ backgroundColor: buttonColor, color: textColor }}
                        >
                          {(displayName || user?.username || 'U').substring(0, 2).toUpperCase()}
                        </div>
                      )}
                    </div>

                    {/* Mockup Name & Handle */}
                    <h3 className="font-extrabold text-base tracking-tight text-center leading-snug">
                      {displayName || user?.username || 'Your Name'}
                    </h3>
                    <p className="text-[11px] opacity-70 font-medium mb-3">
                      @{profile?.username || user?.username}
                    </p>

                    {/* Mockup Bio */}
                    {bio && (
                      <p className="text-xs text-center opacity-85 leading-relaxed max-w-[260px] mb-4 line-clamp-4 whitespace-pre-wrap">
                        {bio}
                      </p>
                    )}

                    {/* Mockup Social Icons */}
                    {socialLinks.length > 0 && (
                      <div className="flex flex-wrap items-center justify-center gap-2 mb-5">
                        {socialLinks.map((item, idx) => (
                          <div
                            key={`preview-${item.platform}-${idx}`}
                            className="p-2 rounded-full shadow-sm text-xs"
                            style={{
                              backgroundColor: buttonColor,
                              color: textColor,
                            }}
                          >
                            {renderSocialIcon(item.platform, 'w-4 h-4')}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Mockup Bio Links */}
                    <div className="w-full space-y-2.5">
                      {links.filter((l) => l.isVisible).length === 0 ? (
                        <div className="text-center py-6 text-xs opacity-50 border border-dashed border-white/10 rounded-xl">
                          Visible links will appear here
                        </div>
                      ) : (
                        links
                          .filter((l) => l.isVisible)
                          .map((link) => (
                            <div
                              key={`preview-${link.id}`}
                              className="w-full py-2.5 px-3 rounded-xl text-center text-xs font-medium shadow-sm truncate border border-white/5"
                              style={{
                                backgroundColor: buttonColor,
                                color: textColor,
                              }}
                            >
                              {link.title}
                            </div>
                          ))
                      )}
                    </div>
                  </div>

                  {/* Powered by SphereSphere footer inside preview */}
                  <div className="pt-6 text-center">
                    <span
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[9px] font-semibold opacity-70 border border-white/10"
                      style={{
                        backgroundColor: buttonColor,
                        color: textColor,
                      }}
                    >
                      <Sparkles className="w-2.5 h-2.5 text-indigo-400" />
                      Powered by SphereSphere
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
