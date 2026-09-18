"""
Public short link redirection endpoint.

Routes:
- GET /r/{short_code}: Fast indexed lookup, atomic $inc click count,
  asynchronous click telemetry, and HTTP 302 Found redirect to the destination URL.
"""

from datetime import datetime, timezone
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.core.database import get_database
from app.core.limiter import limiter
from app.services.telemetry_service import TelemetryService, normalize_referrer
from app.utils.device_detection import detect_device_type
from app.utils.ip_hashing import extract_client_ip, hash_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Redirect"])


@router.get(
    "/r/{short_code}",
    summary="Redirect short code to target destination",
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
)
@limiter.limit("120/minute")
def redirect_to_destination(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
) -> RedirectResponse:
    """
    Public 302 redirect engine.
    1. Validates short code format.
    2. Performs O(1) indexed lookup in MongoDB.
    3. Atomically increments click count using $inc.
    4. Gathers privacy-safe telemetry (timestamp, device type, normalized referrer, hashed IP).
    5. Dispatches telemetry persistence asynchronously via BackgroundTasks.
    6. Returns HTTP 302 Found with Location header pointing to destination URL.
    """
    clean_code = short_code.strip()
    if not clean_code or len(clean_code) > 100:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )

    db = get_database()
    link = db.links.find_one({"shortCode": clean_code})
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )

    destination_url = link.get("destinationUrl")
    if not destination_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid link destination",
        )

    now = datetime.now(timezone.utc)
    link_id_str = str(link["_id"])

    # 1. Atomic click count increment in MongoDB
    try:
        db.links.update_one(
            {"_id": link["_id"]},
            {
                "$inc": {"clickCount": 1},
                "$set": {"updatedAt": now},
            },
        )
    except Exception as e:
        logger.error("Failed to increment clickCount for link %s: %s", link_id_str, e)

    # 2. Extract telemetry metadata
    raw_referrer = request.headers.get("referer") or request.headers.get("referrer")
    referrer = normalize_referrer(raw_referrer)
    device_type = detect_device_type(request.headers.get("user-agent"))
    client_ip = extract_client_ip(request)
    ip_hash = hash_client_ip(client_ip)

    # 3. Dispatch asynchronous telemetry write (does not block redirect response)
    background_tasks.add_task(
        TelemetryService.record_click_event,
        link_id=link_id_str,
        referrer=referrer,
        device_type=device_type,
        ip_hash=ip_hash,
        timestamp=now,
    )

    # 4. Explicitly return HTTP 302 Found
    return RedirectResponse(
        url=destination_url,
        status_code=status.HTTP_302_FOUND,
    )
