"""
Pydantic schemas for short link analytics.

Defines the structure for:
- Overall KPIs (total clicks all time, period clicks)
- Time-series clicks grouped by calendar day (UTC)
- Top referrers with counts and percentages
- Device distribution (Mobile, Desktop, Tablet)
- Complete LinkAnalyticsResponse
"""

from pydantic import BaseModel, Field


class AnalyticsOverview(BaseModel):
    totalClicks: int = Field(description="Total clicks all time")
    periodClicks: int = Field(description="Clicks within the selected date range")


class ClickOverTimeItem(BaseModel):
    date: str = Field(description="Calendar date in YYYY-MM-DD UTC format")
    clicks: int = Field(description="Number of clicks on this date")


class ReferrerItem(BaseModel):
    referrer: str = Field(description="Referrer source or 'Direct'")
    clicks: int = Field(description="Number of clicks from this referrer")
    percentage: float = Field(description="Percentage of period clicks (0.0 to 100.0)")


class DeviceItem(BaseModel):
    deviceType: str = Field(description="Device category: Mobile, Desktop, or Tablet")
    clicks: int = Field(description="Number of clicks from this device category")
    percentage: float = Field(description="Percentage of period clicks (0.0 to 100.0)")


class LinkAnalyticsResponse(BaseModel):
    linkId: str
    shortCode: str
    destinationUrl: str
    title: str | None = None
    range: str = Field(description="Selected period: 7d, 30d, 90d, or all")
    overview: AnalyticsOverview
    clicksOverTime: list[ClickOverTimeItem]
    topReferrers: list[ReferrerItem]
    devices: list[DeviceItem]
