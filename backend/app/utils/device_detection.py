"""
User-Agent device categorization utility.

Normalizes User-Agent strings into one of three standard categories:
- "Mobile"
- "Tablet"
- "Desktop"
"""


def detect_device_type(user_agent: str | None) -> str:
    """
    Classify a User-Agent string into 'Mobile', 'Tablet', or 'Desktop'.
    Falls back gracefully to 'Desktop' when undetermined or header is absent.
    """
    if not user_agent:
        return "Desktop"

    ua = user_agent.lower()

    # 1. Check for Tablet patterns first (many tablets also mention 'mobile' or 'android')
    # Note: Android tablets typically include 'Android' without 'Mobile'.
    is_android_tablet = "android" in ua and "mobile" not in ua
    tablet_keywords = ("ipad", "tablet", "kindle", "silk", "playbook")
    if is_android_tablet or any(kw in ua for kw in tablet_keywords):
        return "Tablet"

    # 2. Check for Mobile phone patterns
    mobile_keywords = (
        "mobile",
        "iphone",
        "ipod",
        "android",
        "blackberry",
        "opera mini",
        "windows phone",
        "iemobile",
    )
    if any(kw in ua for kw in mobile_keywords):
        return "Mobile"

    # 3. Default fallback
    return "Desktop"
