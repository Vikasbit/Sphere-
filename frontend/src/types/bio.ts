/**
 * Bio-Link TypeScript type definitions.
 */

export interface SocialLinkItem {
  platform: string;
  url: string;
}

export interface BioProfile {
  id: string;
  userId: string;
  username: string;
  displayName: string;
  bio: string;
  avatarUrl: string | null;
  backgroundColor: string;
  buttonColor: string;
  textColor: string;
  isPublished: boolean;
  socialLinks: SocialLinkItem[];
  createdAt: string;
  updatedAt: string;
}

export interface UpdateBioProfilePayload {
  displayName: string;
  bio: string;
  avatarUrl?: string | null;
  backgroundColor: string;
  buttonColor: string;
  textColor: string;
  isPublished: boolean;
  socialLinks: SocialLinkItem[];
}

export interface BioLinkItem {
  id: string;
  bioProfileId: string;
  title: string;
  url: string;
  position: number;
  isVisible: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreateBioLinkPayload {
  title: string;
  url: string;
  isVisible?: boolean;
}

export interface UpdateBioLinkPayload {
  title?: string;
  url?: string;
  isVisible?: boolean;
}

export interface PublicBioLinkItem {
  id: string;
  title: string;
  url: string;
  position: number;
}

export interface PublicBioResponse {
  username: string;
  displayName: string;
  bio: string;
  avatarUrl: string | null;
  backgroundColor: string;
  buttonColor: string;
  textColor: string;
  socialLinks: SocialLinkItem[];
  links: PublicBioLinkItem[];
}
