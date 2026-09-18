"""
Bio-Link management and public profile service.

Handles:
- Automatic initialization and updates of BioProfiles
- Link CRUD with positional ordering
- Safe link reordering with ownership enforcement
- Public profile retrieval with strict privacy filtering and publication checks
"""

from datetime import datetime, timezone
import logging
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import get_database
from app.schemas.bio import (
    BioLinkResponse,
    BioProfileResponse,
    CreateBioLinkRequest,
    PublicBioLinkItem,
    PublicBioResponse,
    ReorderBioLinksRequest,
    SocialLinkSchema,
    UpdateBioLinkRequest,
    UpdateBioProfileRequest,
)

logger = logging.getLogger(__name__)


def sanitize_profile_doc(doc: dict) -> BioProfileResponse:
    """Format MongoDB bio_profile document to BioProfileResponse."""
    socials = [
        SocialLinkSchema(platform=item["platform"], url=item["url"])
        for item in doc.get("socialLinks", [])
    ]
    return BioProfileResponse(
        id=str(doc["_id"]),
        userId=str(doc["userId"]),
        username=doc["username"],
        displayName=doc.get("displayName") or doc["username"],
        bio=doc.get("bio") or "",
        avatarUrl=doc.get("avatarUrl"),
        backgroundColor=doc.get("backgroundColor", "#0F172A"),
        buttonColor=doc.get("buttonColor", "#1E293B"),
        textColor=doc.get("textColor", "#FFFFFF"),
        isPublished=doc.get("isPublished", True),
        socialLinks=socials,
        createdAt=doc["createdAt"],
        updatedAt=doc["updatedAt"],
    )


def sanitize_link_doc(doc: dict) -> BioLinkResponse:
    """Format MongoDB bio_link document to BioLinkResponse."""
    return BioLinkResponse(
        id=str(doc["_id"]),
        bioProfileId=str(doc["bioProfileId"]),
        title=doc["title"],
        url=doc["url"],
        position=doc.get("position", 0),
        isVisible=doc.get("isVisible", True),
        createdAt=doc["createdAt"],
        updatedAt=doc["updatedAt"],
    )


class BioService:
    """Provides business logic for personal Bio-Link pages."""

    @classmethod
    def get_or_create_profile(cls, user_id: str, username: str, name: str) -> BioProfileResponse:
        """
        Retrieve the authenticated user's BioProfile.
        If none exists, initializes a default profile using user credentials.
        """
        db = get_database()
        user_id_str = str(user_id)
        profile = db.bio_profiles.find_one({"userId": user_id_str})

        if profile:
            return sanitize_profile_doc(profile)

        now = datetime.now(timezone.utc)
        clean_username = username.lower().strip()
        clean_name = name.strip() or clean_username

        default_doc = {
            "userId": user_id_str,
            "username": clean_username,
            "displayName": clean_name,
            "bio": "",
            "avatarUrl": None,
            "backgroundColor": "#0F172A",
            "buttonColor": "#1E293B",
            "textColor": "#FFFFFF",
            "isPublished": True,
            "socialLinks": [],
            "createdAt": now,
            "updatedAt": now,
        }

        res = db.bio_profiles.insert_one(default_doc)
        default_doc["_id"] = res.inserted_id
        logger.info("Initialized default BioProfile for user %s (@%s)", user_id_str, clean_username)
        return sanitize_profile_doc(default_doc)

    @classmethod
    def update_profile(
        cls,
        user_id: str,
        data: UpdateBioProfileRequest,
        username: str = "",
        name: str = "",
    ) -> BioProfileResponse:
        """
        Update the authenticated user's BioProfile settings and theme.
        Auto-initializes the profile if it has not been retrieved yet.
        """
        db = get_database()
        user_id_str = str(user_id)
        now = datetime.now(timezone.utc)

        profile = db.bio_profiles.find_one({"userId": user_id_str})
        if not profile:
            if not username:
                try:
                    u_doc = db.users.find_one({"_id": ObjectId(user_id_str)})
                    if u_doc:
                        username = u_doc.get("username", "")
                        name = u_doc.get("name", "")
                except Exception:
                    pass
            cls.get_or_create_profile(user_id=user_id_str, username=username, name=name)

        update_fields = {
            "displayName": data.displayName.strip(),
            "bio": (data.bio or "").strip(),
            "avatarUrl": data.avatarUrl,
            "backgroundColor": data.backgroundColor.upper(),
            "buttonColor": data.buttonColor.upper(),
            "textColor": data.textColor.upper(),
            "isPublished": data.isPublished,
            "socialLinks": [item.model_dump() for item in data.socialLinks],
            "updatedAt": now,
        }

        result = db.bio_profiles.find_one_and_update(
            {"userId": user_id_str},
            {"$set": update_fields},
            return_document=True,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bio profile not found",
            )

        logger.info("Updated BioProfile for user %s", user_id_str)
        return sanitize_profile_doc(result)

    @classmethod
    def list_links(cls, user_id: str) -> list[BioLinkResponse]:
        """
        List all bio links owned by the user, ordered by position ascending.
        """
        db = get_database()
        cursor = db.bio_links.find({"userId": str(user_id)}).sort("position", 1)
        return [sanitize_link_doc(doc) for doc in cursor]

    @classmethod
    def create_link(
        cls,
        user_id: str,
        data: CreateBioLinkRequest,
        username: str = "",
        name: str = "",
    ) -> BioLinkResponse:
        """
        Add a new link to the user's bio profile.
        Computes the next position index automatically.
        """
        db = get_database()
        user_id_str = str(user_id)

        profile = db.bio_profiles.find_one({"userId": user_id_str})
        if not profile:
            if not username:
                try:
                    u_doc = db.users.find_one({"_id": ObjectId(user_id_str)})
                    if u_doc:
                        username = u_doc.get("username", "")
                        name = u_doc.get("name", "")
                except Exception:
                    pass
            cls.get_or_create_profile(user_id=user_id_str, username=username, name=name)
            profile = db.bio_profiles.find_one({"userId": user_id_str})

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bio profile not found",
            )

        bio_profile_id = str(profile["_id"])

        # Determine next position
        highest = db.bio_links.find_one(
            {"bioProfileId": bio_profile_id},
            sort=[("position", -1)],
        )
        next_pos = (highest["position"] + 1) if highest else 0

        now = datetime.now(timezone.utc)
        link_doc = {
            "bioProfileId": bio_profile_id,
            "userId": user_id_str,
            "title": data.title.strip(),
            "url": data.url.strip(),
            "position": next_pos,
            "isVisible": data.isVisible,
            "createdAt": now,
            "updatedAt": now,
        }

        res = db.bio_links.insert_one(link_doc)
        link_doc["_id"] = res.inserted_id
        logger.info("Created bio link '%s' at position %d for user %s", data.title, next_pos, user_id_str)
        return sanitize_link_doc(link_doc)

    @classmethod
    def update_link(cls, user_id: str, link_id: str, data: UpdateBioLinkRequest) -> BioLinkResponse:
        """
        Update an existing bio link's title, URL, or visibility.
        Enforces user ownership.
        """
        db = get_database()
        try:
            oid = ObjectId(link_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bio link not found",
            )

        user_id_str = str(user_id)
        now = datetime.now(timezone.utc)

        update_data: dict = {"updatedAt": now}
        if data.title is not None:
            update_data["title"] = data.title.strip()
        if data.url is not None:
            update_data["url"] = data.url.strip()
        if data.isVisible is not None:
            update_data["isVisible"] = data.isVisible

        result = db.bio_links.find_one_and_update(
            {"_id": oid, "userId": user_id_str},
            {"$set": update_data},
            return_document=True,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bio link not found",
            )

        logger.info("Updated bio link %s for user %s", link_id, user_id_str)
        return sanitize_link_doc(result)

    @classmethod
    def delete_link(cls, user_id: str, link_id: str) -> None:
        """
        Delete a bio link. Enforces user ownership.
        """
        db = get_database()
        try:
            oid = ObjectId(link_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bio link not found",
            )

        del_res = db.bio_links.delete_one({"_id": oid, "userId": str(user_id)})
        if del_res.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bio link not found",
            )

        logger.info("Deleted bio link %s for user %s", link_id, user_id)

    @classmethod
    def reorder_links(cls, user_id: str, data: ReorderBioLinksRequest) -> list[BioLinkResponse]:
        """
        Persist a new order for the user's bio links.
        Verifies that every provided link ID belongs to the authenticated user.
        """
        db = get_database()
        user_id_str = str(user_id)
        now = datetime.now(timezone.utc)

        # Validate that all submitted IDs belong to the current user
        valid_oids = []
        for lid in data.linkIds:
            try:
                valid_oids.append(ObjectId(lid))
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid link ID format: {lid}",
                )

        count = db.bio_links.count_documents({
            "_id": {"$in": valid_oids},
            "userId": user_id_str,
        })

        if count != len(valid_oids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more links do not belong to the current user's profile.",
            )

        # Update positions sequentially
        for new_pos, oid in enumerate(valid_oids):
            db.bio_links.update_one(
                {"_id": oid, "userId": user_id_str},
                {"$set": {"position": new_pos, "updatedAt": now}},
            )

        cursor = db.bio_links.find({"userId": user_id_str}).sort("position", 1)
        return [sanitize_link_doc(doc) for doc in cursor]

    @classmethod
    def get_public_profile(cls, username: str) -> PublicBioResponse:
        """
        Retrieve a public Bio profile by username.
        - If profile does not exist OR isPublished is False, strictly returns 404.
        - Never returns private user metadata, session info, or hidden links.
        - Returns only visible links sorted by position ascending.
        """
        clean_username = username.lower().strip()
        db = get_database()

        profile = db.bio_profiles.find_one({"username": clean_username})
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bio profile not found",
            )

        # Unpublished profiles must return 404 to avoid leaking existence
        if not profile.get("isPublished", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bio profile not found",
            )

        # Query only visible links, sorted by position
        cursor = db.bio_links.find(
            {"bioProfileId": str(profile["_id"]), "isVisible": True}
        ).sort("position", 1)

        public_links = [
            PublicBioLinkItem(
                id=str(doc["_id"]),
                title=doc["title"],
                url=doc["url"],
                position=doc.get("position", 0),
            )
            for doc in cursor
        ]

        socials = [
            SocialLinkSchema(platform=item["platform"], url=item["url"])
            for item in profile.get("socialLinks", [])
        ]

        return PublicBioResponse(
            username=profile["username"],
            displayName=profile.get("displayName") or profile["username"],
            bio=profile.get("bio") or "",
            avatarUrl=profile.get("avatarUrl"),
            backgroundColor=profile.get("backgroundColor", "#0F172A"),
            buttonColor=profile.get("buttonColor", "#1E293B"),
            textColor=profile.get("textColor", "#FFFFFF"),
            socialLinks=socials,
            links=public_links,
        )
