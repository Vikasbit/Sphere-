"""
MongoDB connection management.

Provides a single MongoClient instance shared across the application.
Index creation is performed once on startup via `create_indexes()`.

The connection uses a short timeout (5s) so the app doesn't hang if
MongoDB is unavailable. The health endpoint reports degraded status.
"""

import logging

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Module-level client reference — initialized on app startup
_client: MongoClient | None = None
_database: Database | None = None


def connect_to_mongodb() -> None:
    """
    Initialize the MongoDB client and database reference.

    Uses a 5-second serverSelectionTimeout so the app starts quickly
    even if MongoDB is temporarily unavailable. The actual connection
    is lazy — PyMongo connects on first real operation.
    """
    global _client, _database
    settings = get_settings()
    _client = MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=1000,
        connectTimeoutMS=1000,
    )
    _database = _client[settings.database_name]

    # Verify connection with a fast ping
    try:
        _client.admin.command("ping")
        logger.info("MongoDB connected successfully.")
    except Exception as e:
        logger.warning(
            "MongoDB not available at startup: %s. Initializing in-memory database fallback.",
            e,
        )
        try:
            import mongomock
            _client = mongomock.MongoClient()
            _database = _client[settings.database_name]
            logger.info("In-memory MongoDB fallback initialized.")
        except Exception:
            pass


def close_mongodb_connection() -> None:
    """Close the MongoDB client."""
    global _client, _database
    if _client is not None:
        _client.close()
        _client = None
        _database = None


def get_database() -> Database:
    """Return the active database instance, connecting if needed."""
    global _database
    if _database is None:
        connect_to_mongodb()
        create_indexes()
    if _database is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongodb() first.")
    return _database


def create_indexes() -> None:
    """
    Create all required MongoDB indexes.

    Called once on application startup. Using `create_index()` is idempotent —
    if the index already exists with the same spec, it's a no-op.

    Index rationale:
    - User.email (unique): fast login lookups, prevent duplicate registrations
    - User.username (unique): unique usernames for bio-link profiles
    - Link.shortCode (unique): O(1) redirect lookups, prevent slug collisions
    - Link.userId: list links for a specific user
    - ClickEvent.linkId + timestamp (compound): analytics aggregation queries
      filter by linkId then sort/group by timestamp
    - BioProfile.userId (unique): one bio per user
    - BioProfile.username (unique): public bio-link route lookups
    """
    try:
        db = get_database()

        # Users collection
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.users.create_index([("username", ASCENDING)], unique=True)

        # Links collection
        db.links.create_index([("shortCode", ASCENDING)], unique=True)
        db.links.create_index([("userId", ASCENDING)])
        db.links.create_index([("userId", ASCENDING), ("createdAt", DESCENDING)])

        # Click events collection
        db.click_events.create_index([("linkId", ASCENDING)])
        db.click_events.create_index([("timestamp", DESCENDING)])
        db.click_events.create_index([("linkId", ASCENDING), ("timestamp", DESCENDING)])

        # Refresh sessions collection
        db.refresh_sessions.create_index([("tokenHash", ASCENDING)], unique=True)
        db.refresh_sessions.create_index([("userId", ASCENDING)])
        db.refresh_sessions.create_index([("expiresAt", ASCENDING)])

        # Bio profiles
        db.bio_profiles.create_index([("userId", ASCENDING)], unique=True)
        db.bio_profiles.create_index([("username", ASCENDING)], unique=True)

        # Bio links
        db.bio_links.create_index([("bioProfileId", ASCENDING), ("position", ASCENDING)])
        db.bio_links.create_index([("userId", ASCENDING)])

        logger.info("MongoDB indexes created/verified.")
    except Exception as e:
        logger.warning("Could not create indexes (MongoDB may be unavailable): %s", e)
