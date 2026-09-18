"""
System-wide constants for short links, validation, and route protection.
"""

import string

# Short code generator parameters
SHORT_CODE_ALPHABET = string.ascii_letters + string.digits  # 62 alphanumeric characters
SHORT_CODE_LENGTH = 6
MAX_CODE_GEN_ATTEMPTS = 5

# Centralized reserved routes and system slugs that cannot be claimed as vanity short codes
RESERVED_SLUGS = {
    # System routes
    "api",
    "r",
    "bio",
    "health",
    "docs",
    "redoc",
    "openapi.json",
    # Frontend application routes
    "login",
    "signup",
    "logout",
    "dashboard",
    "links",
    "analytics",
    "settings",
    "profile",
    "forgot-password",
    "reset-password",
    "verify-email",
    # Administrative & standard assets
    "admin",
    "root",
    "static",
    "assets",
    "favicon.ico",
    "robots.txt",
    "sitemap.xml",
}
