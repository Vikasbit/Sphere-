"""
Telemetry service for tracking click events.

Records anonymous, privacy-safe analytics asynchronously without slowing down
the public redirect path or leaking personal data.
"""

from datetime import datetime, timezone
import logging
from app.core.database import get_database

logger = logging.getLogger(__name__)

MAX_REFERRER_LENGTH = 500


def normalize_referrer(raw_referrer: str | None) -> str:
    """
    Sanitize and normalize the HTTP Referer header.
    Returns 'Direct' when missing or empty. Caps length to avoid oversized database documents.
    """
    if not raw_referrer or not raw_referrer.strip():
        return "Direct"
    cleaned = raw_referrer.strip()
    return cleaned[:MAX_REFERRER_LENGTH]


class TelemetryService:
    """Handles asynchronous recording of short link click events."""

    @staticmethod
    def record_click_event(
        link_id: str,
        referrer: str,
        device_type: str,
        ip_hash: str,
        timestamp: datetime | None = None,
    ) -> None:
        """
        Persist a click event to the click_events collection.
        This method is designed to be executed via FastAPI BackgroundTasks.
        Catches and logs all database errors to guarantee telemetry failures never
        compromise client redirects.
        """
        try:
            db = get_database()
            event_doc = {
                "linkId": str(link_id),
                "timestamp": timestamp or datetime.now(timezone.utc),
                "referrer": referrer,
                "deviceType": device_type,
                "ipHash": ip_hash,
            }
            db.click_events.insert_one(event_doc)
            logger.debug("Telemetry recorded for linkId=%s, device=%s", link_id, device_type)
        except Exception as e:
            logger.error(
                "Telemetry recording failure for linkId=%s: %s. Redirect succeeded unaffected.",
                link_id,
                e,
            )
