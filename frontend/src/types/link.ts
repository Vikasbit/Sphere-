/**
 * Short Link TypeScript type definitions.
 */

export interface LinkItem {
  id: string;
  destinationUrl: string;
  shortCode: string;
  shortUrl: string;
  clickCount: number;
  title?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateLinkPayload {
  destinationUrl: string;
  customSlug?: string | null;
  title?: string | null;
}

export interface LinkListResponse {
  items: LinkItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}
