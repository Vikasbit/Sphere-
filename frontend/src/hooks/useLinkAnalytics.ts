/**
 * TanStack Query hook for link analytics.
 * Fetches aggregated metrics: clicks over time, top referrers, and device distribution.
 */

import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

export interface AnalyticsOverview {
  totalClicks: number;
  periodClicks: number;
}

export interface ClickOverTimeItem {
  date: string;
  clicks: number;
}

export interface ReferrerItem {
  referrer: string;
  clicks: number;
  percentage: number;
}

export interface DeviceItem {
  deviceType: 'Mobile' | 'Desktop' | 'Tablet' | string;
  clicks: number;
  percentage: number;
}

export interface LinkAnalytics {
  linkId: string;
  shortCode: string;
  destinationUrl: string;
  title?: string | null;
  range: '7d' | '30d' | '90d' | 'all';
  overview: AnalyticsOverview;
  clicksOverTime: ClickOverTimeItem[];
  topReferrers: ReferrerItem[];
  devices: DeviceItem[];
}

export function useLinkAnalytics(linkId: string | undefined, range: string = '7d') {
  return useQuery<LinkAnalytics, Error>({
    queryKey: ['linkAnalytics', linkId, range],
    queryFn: async () => {
      if (!linkId) {
        throw new Error('Link ID is required');
      }
      const response = await api.get<LinkAnalytics>(`/links/${linkId}/analytics`, {
        params: { range },
      });
      return response.data;
    },
    enabled: Boolean(linkId),
    staleTime: 30 * 1000, // 30 seconds fresh cache
  });
}
