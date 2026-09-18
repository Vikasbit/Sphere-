"""
Privacy-preserving IP address hashing utility.

Raw IP addresses are classified as personal data under privacy regulations (such as GDPR).
To respect user privacy while preventing bot fraud and calculating unique click metrics,
client IP addresses are salted with a server-side pepper and permanently hashed via SHA-256.
Raw IP addresses are NEVER persisted in MongoDB or exposed via APIs.
"""

import hashlib
from fastapi import Request
from app.core.config import get_settings


def extract_client_ip(request: Request) -> str:
    """
    Extract client IP address from the request.
    Inspects X-Forwarded-For (taking the first client IP) or falls back to request.client.host.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # First IP in comma-separated list is the original client IP
        parts = [ip.strip() for ip in forwarded_for.split(",")]
        if parts and parts[0]:
            return parts[0]

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def hash_client_ip(ip: str | None) -> str:
    """
    Produce a deterministic, irreversible SHA-256 hash of a client IP address
    incorporating a server-side pepper/salt.
    """
    settings = get_settings()
    normalized_ip = (ip or "unknown").strip().lower()
    salted_value = f"{normalized_ip}:{settings.ip_hash_salt}"
    return hashlib.sha256(salted_value.encode("utf-8")).hexdigest()
