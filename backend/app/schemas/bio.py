"""
Pydantic schemas for Bio-Link builder and public bio pages.
"""

from datetime import datetime
from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator

ALLOWED_PLATFORMS = {
  "instagram",
  "github",
  "linkedin",
  "twitter",
  "youtube",
  "facebook",
  "website",
}


def validate_web_url(url: str | None) -> str | None:
  """Validate that a URL uses http:// or https:// with a valid host."""
  if not url:
    return None
  clean_url = url.strip()
  parsed = urlparse(clean_url)
  if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
    raise ValueError("URL must be an absolute web address starting with http:// or https://")
  return clean_url


class SocialLinkSchema(BaseModel):
  """Social profile link with controlled platform types."""
  platform: str = Field(description="Social platform identifier (e.g. github, instagram, twitter)")
  url: str = Field(description="Profile URL")

  @field_validator("platform")
  @classmethod
  def validate_platform(cls, v: str) -> str:
    cleaned = v.strip().lower()
    if cleaned not in ALLOWED_PLATFORMS:
      raise ValueError(f"Platform must be one of: {', '.join(sorted(ALLOWED_PLATFORMS))}")
    return cleaned

  @field_validator("url")
  @classmethod
  def validate_url(cls, v: str) -> str:
    res = validate_web_url(v)
    if not res:
      raise ValueError("Invalid social link URL")
    return res


class UpdateBioProfileRequest(BaseModel):
  """Request schema for updating authenticated user's Bio profile."""
  displayName: str = Field(min_length=1, max_length=50, description="Profile heading display name")
  bio: str | None = Field(default=None, max_length=500, description="Short biography text")
  avatarUrl: str | None = Field(default=None, max_length=1000, description="Public avatar image URL")
  backgroundColor: str = Field(
      default="#0F172A",
      pattern=r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$",
      description="Page background hex color",
  )
  buttonColor: str = Field(
      default="#1E293B",
      pattern=r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$",
      description="Link button hex color",
  )
  textColor: str = Field(
      default="#FFFFFF",
      pattern=r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$",
      description="Typography text hex color",
  )
  isPublished: bool = Field(default=True, description="Whether bio page is publicly viewable")
  socialLinks: list[SocialLinkSchema] = Field(default_factory=list, description="List of social channel links")

  @field_validator("avatarUrl")
  @classmethod
  def validate_avatar_url(cls, v: str | None) -> str | None:
    return validate_web_url(v)


class BioProfileResponse(BaseModel):
  """Full BioProfile details returned to authenticated profile owner."""
  id: str
  userId: str
  username: str
  displayName: str
  bio: str | None = None
  avatarUrl: str | None = None
  backgroundColor: str
  buttonColor: str
  textColor: str
  isPublished: bool
  socialLinks: list[SocialLinkSchema]
  createdAt: datetime
  updatedAt: datetime


class CreateBioLinkRequest(BaseModel):
  """Request schema for creating a new bio link."""
  title: str = Field(min_length=1, max_length=100, description="Link label title")
  url: str = Field(min_length=1, max_length=2000, description="Destination target URL")
  isVisible: bool = Field(default=True, description="Whether link is visible to public")

  @field_validator("url")
  @classmethod
  def validate_link_url(cls, v: str) -> str:
    res = validate_web_url(v)
    if not res:
      raise ValueError("Invalid destination URL")
    return res


class UpdateBioLinkRequest(BaseModel):
  """Request schema for updating an existing bio link."""
  title: str | None = Field(default=None, min_length=1, max_length=100)
  url: str | None = Field(default=None, min_length=1, max_length=2000)
  isVisible: bool | None = None

  @field_validator("url")
  @classmethod
  def validate_link_url(cls, v: str | None) -> str | None:
    return validate_web_url(v)


class ReorderBioLinksRequest(BaseModel):
  """Request schema for reordering links."""
  linkIds: list[str] = Field(description="Ordered list of bio link IDs")


class BioLinkResponse(BaseModel):
  """Bio link response returned to authenticated profile owner."""
  id: str
  bioProfileId: str
  title: str
  url: str
  position: int
  isVisible: bool
  createdAt: datetime
  updatedAt: datetime


class PublicBioLinkItem(BaseModel):
  """Visible link representation on public bio page."""
  id: str
  title: str
  url: str
  position: int


class PublicBioResponse(BaseModel):
  """
  Strictly public Bio profile payload.
  Excludes user IDs, email, passwordHash, session information, and hidden links.
  """
  username: str
  displayName: str
  bio: str | None = None
  avatarUrl: str | None = None
  backgroundColor: str
  buttonColor: str
  textColor: str
  socialLinks: list[SocialLinkSchema]
  links: list[PublicBioLinkItem]
