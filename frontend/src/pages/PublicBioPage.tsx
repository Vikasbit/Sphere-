import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import {
  ExternalLink,
  AlertCircle,
  Loader2,
  Sparkles,
} from 'lucide-react';
import type { PublicBioResponse } from '../types/bio';
import { renderSocialIcon } from '../components/SocialIcons';

export const PublicBioPage: React.FC = () => {
  const { username } = useParams<{ username: string }>();
  const [profile, setProfile] = useState<PublicBioResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [imgError, setImgError] = useState<boolean>(false);

  useEffect(() => {
    if (!username) return;

    let isMounted = true;
    const timer = setTimeout(() => {
      if (!isMounted) return;
      setIsLoading(true);
      setErrorStatus(null);
      setImgError(false);

      axios
        .get<PublicBioResponse>(`/api/bio/public/${encodeURIComponent(username)}`)
        .then((res) => {
          if (isMounted) {
            setProfile(res.data);
            document.title = `${res.data.displayName} (@${res.data.username}) | SphereSphere`;
          }
        })
        .catch((err) => {
          if (isMounted) {
            setErrorStatus(err.response?.status || 500);
            document.title = 'Profile Not Found | SphereSphere';
          }
        })
        .finally(() => {
          if (isMounted) {
            setIsLoading(false);
          }
        });
    }, 0);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [username]);

  // Loading State
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mb-4" />
        <p className="text-slate-400 font-medium text-sm">Loading bio page...</p>
      </div>
    );
  }

  // Not Found / Unpublished / Error State
  if (errorStatus || !profile) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-center">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-sm">
          <div className="w-16 h-16 bg-slate-800/80 rounded-full flex items-center justify-center mx-auto mb-5 text-amber-400">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Profile Not Available</h1>
          <p className="text-slate-400 text-sm mb-6 leading-relaxed">
            The bio page for <span className="font-semibold text-slate-300">@{username}</span> either does not exist,
            has been set to private, or is currently unpublished.
          </p>
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-lg shadow-indigo-600/20"
          >
            Create Your Own Bio Page
          </Link>
        </div>
      </div>
    );
  }

  const initials = profile.displayName
    ? profile.displayName
        .split(' ')
        .map((part) => part[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : profile.username.substring(0, 2).toUpperCase();

  return (
    <div
      className="min-h-screen flex flex-col justify-between transition-colors duration-300 relative selection:bg-indigo-500 selection:text-white"
      style={{
        backgroundColor: profile.backgroundColor || '#0F172A',
        color: profile.textColor || '#FFFFFF',
      }}
    >
      {/* Centered Main Profile Container */}
      <main className="w-full max-w-xl mx-auto px-4 pt-16 pb-12 flex flex-col items-center">
        {/* Profile Avatar */}
        <div className="relative mb-5 group">
          {profile.avatarUrl && !imgError ? (
            <img
              src={profile.avatarUrl}
              alt={profile.displayName}
              onError={() => setImgError(true)}
              className="w-24 h-24 sm:w-28 sm:h-28 rounded-full object-cover shadow-xl ring-4 ring-white/10 group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div
              className="w-24 h-24 sm:w-28 sm:h-28 rounded-full flex items-center justify-center text-2xl font-bold shadow-xl ring-4 ring-white/10 group-hover:scale-105 transition-transform duration-300"
              style={{
                backgroundColor: profile.buttonColor || '#1E293B',
                color: profile.textColor || '#FFFFFF',
              }}
            >
              {initials}
            </div>
          )}
        </div>

        {/* Display Name & Username */}
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-center mb-1">
          {profile.displayName}
        </h1>
        <p className="text-sm sm:text-base opacity-75 font-medium mb-4">
          @{profile.username}
        </p>

        {/* Biography (plain text safely wrapped to prevent XSS) */}
        {profile.bio && (
          <p className="text-sm sm:text-base opacity-90 text-center max-w-md whitespace-pre-wrap leading-relaxed mb-6 font-normal">
            {profile.bio}
          </p>
        )}

        {/* Social Icons Row */}
        {profile.socialLinks && profile.socialLinks.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-3 mb-8">
            {profile.socialLinks.map((item, idx) => (
              <a
                key={`${item.platform}-${idx}`}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                title={item.platform}
                aria-label={item.platform}
                className="p-3 rounded-full transition-all duration-200 hover:scale-115 hover:opacity-100 opacity-80 backdrop-blur-md shadow-md"
                style={{
                  backgroundColor: profile.buttonColor || '#1E293B',
                  color: profile.textColor || '#FFFFFF',
                }}
              >
                {renderSocialIcon(item.platform, 'w-5 h-5')}
              </a>
            ))}
          </div>
        )}

        {/* Custom Links Stack */}
        <div className="w-full space-y-3.5 mt-2">
          {profile.links && profile.links.length > 0 ? (
            profile.links.map((link) => (
              <a
                key={link.id}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full flex items-center justify-between p-4 rounded-xl font-semibold text-sm sm:text-base shadow-md transition-all duration-200 hover:scale-[1.02] active:scale-[0.99] group border border-white/5"
                style={{
                  backgroundColor: profile.buttonColor || '#1E293B',
                  color: profile.textColor || '#FFFFFF',
                }}
              >
                <div className="w-6" /> {/* spacer */}
                <span className="truncate px-2 text-center flex-1 font-medium">{link.title}</span>
                <ExternalLink className="w-5 h-5 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all flex-shrink-0" />
              </a>
            ))
          ) : (
            <div className="text-center py-8 opacity-60 text-sm">
              No links shared yet.
            </div>
          )}
        </div>
      </main>

      {/* Powered by SphereSphere Footer */}
      <footer className="w-full py-8 text-center">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold backdrop-blur-md opacity-80 hover:opacity-100 transition-opacity border border-white/10 shadow-sm"
          style={{
            backgroundColor: profile.buttonColor || '#1E293B',
            color: profile.textColor || '#FFFFFF',
          }}
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Powered by SphereSphere</span>
        </Link>
      </footer>
    </div>
  );
};
