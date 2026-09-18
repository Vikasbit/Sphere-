"""
Analytics service for short links.

Executes database-driven MongoDB aggregation pipelines to calculate:
- Clicks over time (grouped by UTC calendar day)
- Top referrers (sorted descending)
- Device distribution (Mobile, Desktop, Tablet)
- KPIs (total clicks all time, period clicks)

Enforces link ownership, zero-fills missing calendar dates for smooth charts,
and avoids in-memory data processing over raw click events.
"""

from datetime import datetime, timedelta, timezone
import logging
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.schemas.analytics import (
    AnalyticsOverview,
    ClickOverTimeItem,
    DeviceItem,
    LinkAnalyticsResponse,
    ReferrerItem,
)

logger = logging.getLogger(__name__)

VALID_RANGES = {"7d", "30d", "90d", "all"}
STANDARD_DEVICES = ["Mobile", "Desktop", "Tablet"]


class AnalyticsService:
    """Provides aggregation and analysis for link click events."""

    @classmethod
    def verify_link_ownership(cls, user_id: str, link_id: str) -> dict:
        """
        Verify that the link exists and is owned by the given user.
        Raises 404 Not Found if missing or unauthorized (prevents resource enumeration).
        """
        db = get_database()
        try:
            oid = ObjectId(link_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        link = db.links.find_one({"_id": oid})
        if not link or str(link.get("userId")) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        return link

    @classmethod
    def _compute_date_range(cls, range_str: str, now: datetime) -> tuple[datetime | None, int]:
        """
        Calculate the start date (UTC, start of day) and total number of days for the range.
        Returns (start_date, day_count). start_date is None for 'all'.
        """
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if range_str == "7d":
            return today_start - timedelta(days=6), 7
        elif range_str == "30d":
            return today_start - timedelta(days=29), 30
        elif range_str == "90d":
            return today_start - timedelta(days=89), 90
        elif range_str == "all":
            return None, 0
        else:
            # Default fallback to 7d
            return today_start - timedelta(days=6), 7

    @classmethod
    def get_clicks_over_time(
        cls,
        link_id: str,
        start_date: datetime | None,
        now: datetime,
        range_str: str,
        link_created_at: datetime | None = None,
    ) -> list[ClickOverTimeItem]:
        """
        Aggregate clicks by calendar day (UTC) using MongoDB aggregation.
        Fills missing calendar dates with 0 clicks so frontend charts do not
        misleadingly connect missing dates.
        """
        db = get_database()
        match_filter: dict = {"linkId": link_id}
        if start_date:
            match_filter["timestamp"] = {"$gte": start_date, "$lte": now}

        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "clicks": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        cursor = db.click_events.aggregate(pipeline)
        db_counts = {item["_id"]: item["clicks"] for item in cursor}

        # Determine start date for zero-filling
        today_date = now.date()
        if start_date:
            fill_start_date = start_date.date()
        else:
            # For 'all', determine the earliest date: from db_counts or link_created_at
            if db_counts:
                earliest_db_str = min(db_counts.keys())
                earliest_db_date = datetime.strptime(earliest_db_str, "%Y-%m-%d").date()
                fill_start_date = earliest_db_date
            elif link_created_at:
                fill_start_date = link_created_at.date()
            else:
                fill_start_date = today_date - timedelta(days=6)

            # Cap 'all' zero-fill to a reasonable maximum (e.g. 90 days) if earliest date is ancient
            if (today_date - fill_start_date).days > 90 and not db_counts:
                fill_start_date = today_date - timedelta(days=89)

        # Generate every day from fill_start_date to today_date
        items: list[ClickOverTimeItem] = []
        current_date = fill_start_date
        while current_date <= today_date:
            d_str = current_date.strftime("%Y-%m-%d")
            items.append(
                ClickOverTimeItem(
                    date=d_str,
                    clicks=db_counts.get(d_str, 0),
                )
            )
            current_date += timedelta(days=1)

        return items

    @classmethod
    def get_top_referrers(
        cls,
        link_id: str,
        start_date: datetime | None,
        now: datetime,
        period_clicks: int,
        limit: int = 5,
    ) -> list[ReferrerItem]:
        """
        Aggregate top referrers using MongoDB aggregation.
        Sorted descending by click count, top N limit.
        """
        db = get_database()
        match_filter: dict = {"linkId": link_id}
        if start_date:
            match_filter["timestamp"] = {"$gte": start_date, "$lte": now}

        pipeline = [
            {"$match": match_filter},
            {"$group": {"_id": "$referrer", "clicks": {"$sum": 1}}},
            {"$sort": {"clicks": -1}},
            {"$limit": limit},
        ]

        cursor = db.click_events.aggregate(pipeline)
        items: list[ReferrerItem] = []

        for row in cursor:
            ref = row["_id"] or "Direct"
            clicks = row["clicks"]
            pct = round((clicks / period_clicks * 100.0), 1) if period_clicks > 0 else 0.0
            items.append(
                ReferrerItem(
                    referrer=ref,
                    clicks=clicks,
                    percentage=pct,
                )
            )

        return items

    @classmethod
    def get_device_distribution(
        cls,
        link_id: str,
        start_date: datetime | None,
        now: datetime,
        period_clicks: int,
    ) -> list[DeviceItem]:
        """
        Aggregate clicks by device category (Mobile, Desktop, Tablet) using MongoDB aggregation.
        Ensures standard device types are always represented in response even with zero clicks.
        """
        db = get_database()
        match_filter: dict = {"linkId": link_id}
        if start_date:
            match_filter["timestamp"] = {"$gte": start_date, "$lte": now}

        pipeline = [
            {"$match": match_filter},
            {"$group": {"_id": "$deviceType", "clicks": {"$sum": 1}}},
        ]

        cursor = db.click_events.aggregate(pipeline)
        device_counts = {item["_id"]: item["clicks"] for item in cursor}

        items: list[DeviceItem] = []
        for dev in STANDARD_DEVICES:
            clicks = device_counts.get(dev, 0)
            pct = round((clicks / period_clicks * 100.0), 1) if period_clicks > 0 else 0.0
            items.append(
                DeviceItem(
                    deviceType=dev,
                    clicks=clicks,
                    percentage=pct,
                )
            )

        return items

    @classmethod
    def get_link_analytics(
        cls,
        user_id: str,
        link_id: str,
        range_str: str = "7d",
    ) -> LinkAnalyticsResponse:
        """
        Complete analytics coordinator for a short link.
        1. Enforces user ownership.
        2. Resolves time boundaries.
        3. Aggregates KPIs, clicks-over-time, top referrers, and device breakdown.
        """
        clean_range = range_str.lower().strip()
        if clean_range not in VALID_RANGES:
            clean_range = "7d"

        # 1. Enforce ownership
        link = cls.verify_link_ownership(user_id=user_id, link_id=link_id)

        now = datetime.now(timezone.utc)
        start_date, _ = cls._compute_date_range(clean_range, now)

        db = get_database()

        # 2. Total clicks (all time) & Period clicks
        # Use link's clickCount or actual documents count
        db_total_events = db.click_events.count_documents({"linkId": link_id})
        link_click_count = link.get("clickCount", 0)
        total_clicks = max(db_total_events, link_click_count)

        if start_date is None:
            period_clicks = total_clicks
        else:
            period_clicks = db.click_events.count_documents(
                {"linkId": link_id, "timestamp": {"$gte": start_date, "$lte": now}}
            )

        overview = AnalyticsOverview(
            totalClicks=total_clicks,
            periodClicks=period_clicks,
        )

        # 3. Clicks over time (daily aggregation with zero-fill)
        clicks_over_time = cls.get_clicks_over_time(
            link_id=link_id,
            start_date=start_date,
            now=now,
            range_str=clean_range,
            link_created_at=link.get("createdAt"),
        )

        # 4. Top Referrers
        top_referrers = cls.get_top_referrers(
            link_id=link_id,
            start_date=start_date,
            now=now,
            period_clicks=period_clicks,
            limit=5,
        )

        # 5. Devices
        devices = cls.get_device_distribution(
            link_id=link_id,
            start_date=start_date,
            now=now,
            period_clicks=period_clicks,
        )

        return LinkAnalyticsResponse(
            linkId=str(link["_id"]),
            shortCode=link.get("shortCode", ""),
            destinationUrl=link.get("destinationUrl", ""),
            title=link.get("title"),
            range=clean_range,
            overview=overview,
            clicksOverTime=clicks_over_time,
            topReferrers=top_referrers,
            devices=devices,
        )
