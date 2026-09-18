import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ChevronLeft,
  Copy,
  Check,
  ExternalLink,
  BarChart3,
  Calendar,
  MousePointerClick,
  Smartphone,
  Monitor,
  Tablet,
  Globe,
  Loader2,
  AlertCircle,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import toast from 'react-hot-toast';
import { useLinkAnalytics } from '../hooks/useLinkAnalytics';

const RANGE_OPTIONS = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'all', label: 'All time' },
];

export const AnalyticsPage: React.FC = () => {
  const { linkId } = useParams<{ linkId: string }>();
  const [range, setRange] = useState<string>('7d');
  const [copied, setCopied] = useState(false);

  const { data, isLoading, isError, error, refetch, isFetching } = useLinkAnalytics(
    linkId,
    range
  );

  const handleCopy = (shortCode: string) => {
    const fullUrl = `${window.location.origin}/r/${shortCode}`;
    navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    toast.success('Short link copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType.toLowerCase()) {
      case 'mobile':
        return <Smartphone className="w-4 h-4 text-indigo-400" />;
      case 'tablet':
        return <Tablet className="w-4 h-4 text-amber-400" />;
      case 'desktop':
      default:
        return <Monitor className="w-4 h-4 text-emerald-400" />;
    }
  };

  // Format date for chart X-axis
  const formatXAxisDate = (dateStr: string) => {
    try {
      const parts = dateStr.split('-');
      if (parts.length === 3) {
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const month = monthNames[parseInt(parts[1], 10) - 1];
        const day = parseInt(parts[2], 10);
        return `${month} ${day}`;
      }
      return dateStr;
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-gray-100 px-4 py-8 sm:py-12">
      <div className="max-w-6xl w-full mx-auto space-y-6">
        {/* Navigation Breadcrumb & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Link
              to="/links"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white text-xs font-semibold border border-white/10 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Back to Links</span>
            </Link>
            <div className="h-4 w-[1px] bg-white/20" />
            <h1 className="text-xl sm:text-2xl font-extrabold text-white flex items-center gap-2">
              <BarChart3 className="w-6 h-6 text-indigo-400" />
              <span>Link Analytics</span>
            </h1>
          </div>

          {/* Time Range Selector & Refresh */}
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-xl bg-white/5 border border-white/10 p-1">
              {RANGE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setRange(opt.value)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    range === opt.value
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 hover:text-white transition-colors cursor-pointer disabled:opacity-50"
              title="Refresh Analytics"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="rounded-2xl bg-white/5 border border-white/10 p-16 text-center space-y-4">
            <Loader2 className="w-10 h-10 animate-spin text-indigo-400 mx-auto" />
            <p className="text-sm text-gray-300 font-medium">Aggregating link metrics...</p>
            <p className="text-xs text-gray-500">Querying database-level time series pipelines.</p>
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div className="rounded-2xl bg-red-500/10 border border-red-500/20 p-8 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-red-500/20 text-red-400 flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-bold text-white">Failed to Load Analytics</h2>
              <p className="text-xs text-gray-400">
                {error?.message || 'Link was not found or you do not have permission to view its metrics.'}
              </p>
            </div>
            <div className="pt-2">
              <Link
                to="/links"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-colors"
              >
                <span>Return to Links Library</span>
              </Link>
            </div>
          </div>
        )}

        {/* Loaded Data Dashboard */}
        {data && (
          <div className="space-y-6">
            {/* Link Info Bar */}
            <div className="rounded-2xl bg-white/5 border border-white/10 p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-base sm:text-lg font-bold text-indigo-300">
                    /r/{data.shortCode}
                  </span>
                  {data.title && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-white/10 text-gray-300">
                      {data.title}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-400 truncate max-w-2xl">
                  <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 text-gray-500" />
                  <a
                    href={data.destinationUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-indigo-300 hover:underline truncate"
                  >
                    {data.destinationUrl}
                  </a>
                </div>
              </div>

              <div className="flex items-center gap-2 self-start md:self-center flex-shrink-0">
                <button
                  onClick={() => handleCopy(data.shortCode)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-300" />
                      <span>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Short Link</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* KPI Overview Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="rounded-2xl bg-white/5 border border-white/10 p-5 space-y-2">
                <div className="flex items-center justify-between text-gray-400 text-xs">
                  <span>Total Clicks (All Time)</span>
                  <MousePointerClick className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="text-3xl font-extrabold text-white">
                  {data.overview.totalClicks.toLocaleString()}
                </div>
                <p className="text-[11px] text-gray-500">Recorded across the link lifetime</p>
              </div>

              <div className="rounded-2xl bg-white/5 border border-white/10 p-5 space-y-2">
                <div className="flex items-center justify-between text-gray-400 text-xs">
                  <span>Period Clicks ({data.range})</span>
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-3xl font-extrabold text-white">
                  {data.overview.periodClicks.toLocaleString()}
                </div>
                <p className="text-[11px] text-gray-500">Within selected date range</p>
              </div>

              <div className="rounded-2xl bg-white/5 border border-white/10 p-5 space-y-2">
                <div className="flex items-center justify-between text-gray-400 text-xs">
                  <span>Top Referrer</span>
                  <Globe className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-xl font-bold text-white truncate">
                  {data.topReferrers.length > 0 ? data.topReferrers[0].referrer : 'None'}
                </div>
                <p className="text-[11px] text-gray-500">
                  {data.topReferrers.length > 0
                    ? `${data.topReferrers[0].clicks} clicks (${data.topReferrers[0].percentage}%)`
                    : 'Awaiting first referral'}
                </p>
              </div>

              <div className="rounded-2xl bg-white/5 border border-white/10 p-5 space-y-2">
                <div className="flex items-center justify-between text-gray-400 text-xs">
                  <span>Primary Device</span>
                  <Smartphone className="w-4 h-4 text-violet-400" />
                </div>
                <div className="text-xl font-bold text-white truncate">
                  {data.devices.find((d) => d.clicks > 0)?.deviceType || 'None'}
                </div>
                <p className="text-[11px] text-gray-500">
                  {data.overview.periodClicks > 0 ? 'Highest volume visitor type' : 'Awaiting visits'}
                </p>
              </div>
            </div>

            {/* Empty State vs Full Chart View */}
            {data.overview.totalClicks === 0 ? (
              <div className="rounded-2xl bg-white/5 border border-white/10 p-12 text-center space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto border border-indigo-500/20">
                  <BarChart3 className="w-7 h-7" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-lg font-bold text-white">No Clicks Recorded Yet</h3>
                  <p className="text-xs text-gray-400 max-w-md mx-auto">
                    This short link has not received any visitors yet. Share your short link to start tracking real-time analytics, referrers, and device distribution.
                  </p>
                </div>
                <button
                  onClick={() => handleCopy(data.shortCode)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all cursor-pointer"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Short Link & Share</span>
                </button>
              </div>
            ) : (
              <>
                {/* Clicks Over Time Chart */}
                <div className="rounded-2xl bg-white/5 border border-white/10 p-5 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-base font-bold text-white">Clicks Over Time</h2>
                      <p className="text-xs text-gray-400">Daily visit volume grouped in UTC</p>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-indigo-300 bg-indigo-600/10 px-2.5 py-1 rounded-lg border border-indigo-500/20">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{data.range.toUpperCase()}</span>
                    </div>
                  </div>

                  <div className="h-72 w-full pt-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={data.clicksOverTime}
                        margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                      >
                        <defs>
                          <linearGradient id="clickGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                        <XAxis
                          dataKey="date"
                          tickFormatter={formatXAxisDate}
                          stroke="#64748b"
                          fontSize={11}
                          tickLine={false}
                          axisLine={{ stroke: '#ffffff15' }}
                        />
                        <YAxis
                          stroke="#64748b"
                          fontSize={11}
                          tickLine={false}
                          axisLine={{ stroke: '#ffffff15' }}
                          allowDecimals={false}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            borderColor: '#334155',
                            borderRadius: '0.75rem',
                            fontSize: '12px',
                            color: '#f8fafc',
                          }}
                          labelFormatter={(label) => `Date: ${label} (UTC)`}
                          formatter={(value: unknown) => {
                            const val = typeof value === 'number' ? value : Number(value || 0);
                            return [`${val} clicks`, 'Visits'];
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="clicks"
                          stroke="#818cf8"
                          strokeWidth={2.5}
                          fillOpacity={1}
                          fill="url(#clickGradient)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Sub-Aggregations Grid: Referrers & Devices */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Top Referrers */}
                  <div className="rounded-2xl bg-white/5 border border-white/10 p-5 sm:p-6 space-y-4">
                    <div>
                      <h2 className="text-base font-bold text-white flex items-center gap-2">
                        <Globe className="w-4 h-4 text-blue-400" />
                        <span>Top Referrers</span>
                      </h2>
                      <p className="text-xs text-gray-400">Sources bringing visits to this link</p>
                    </div>

                    {data.topReferrers.length === 0 ? (
                      <p className="text-xs text-gray-500 py-6 text-center">
                        No referrer data captured for this period.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {data.topReferrers.map((item, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-gray-200 font-medium truncate max-w-xs">
                                {item.referrer}
                              </span>
                              <span className="text-gray-400 font-mono">
                                {item.clicks} ({item.percentage}%)
                              </span>
                            </div>
                            <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
                                style={{ width: `${Math.min(item.percentage, 100)}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Device Distribution */}
                  <div className="rounded-2xl bg-white/5 border border-white/10 p-5 sm:p-6 space-y-4">
                    <div>
                      <h2 className="text-base font-bold text-white flex items-center gap-2">
                        <Smartphone className="w-4 h-4 text-violet-400" />
                        <span>Device Distribution</span>
                      </h2>
                      <p className="text-xs text-gray-400">Visitors categorized by client platform</p>
                    </div>

                    <div className="space-y-3">
                      {data.devices.map((device) => (
                        <div
                          key={device.deviceType}
                          className="bg-white/5 border border-white/5 rounded-xl p-3 space-y-2"
                        >
                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              {getDeviceIcon(device.deviceType)}
                              <span className="text-gray-200 font-semibold">{device.deviceType}</span>
                            </div>
                            <span className="text-gray-400 font-mono">
                              {device.clicks} clicks ({device.percentage}%)
                            </span>
                          </div>
                          <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-1.5 rounded-full transition-all duration-500 ${
                                device.deviceType.toLowerCase() === 'mobile'
                                  ? 'bg-indigo-500'
                                  : device.deviceType.toLowerCase() === 'tablet'
                                  ? 'bg-amber-500'
                                  : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.min(device.percentage, 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
