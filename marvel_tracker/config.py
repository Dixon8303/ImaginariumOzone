"""Environment-driven configuration. No secrets are ever written to disk here."""

import os

MARVEL_STUDIOS_COMPANY_ID = 420

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

ICLOUD_APPLE_ID = os.environ.get("ICLOUD_APPLE_ID")
ICLOUD_APP_SPECIFIC_PASSWORD = os.environ.get("ICLOUD_APP_SPECIFIC_PASSWORD")
ICLOUD_CALDAV_URL = os.environ.get("ICLOUD_CALDAV_URL", "https://caldav.icloud.com")
ICLOUD_CALENDAR_NAME = os.environ.get("ICLOUD_CALENDAR_NAME", "Marvel Releases")

NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")

SMS_GATEWAY_ADDRESS = os.environ.get("SMS_GATEWAY_ADDRESS")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(_PACKAGE_DIR, "state.json")
TRACKED_IDS_FILE = os.path.join(_PACKAGE_DIR, "tracked_ids.yaml")

REQUIRED_VARS = [
    "TMDB_API_KEY",
    "ICLOUD_APPLE_ID",
    "ICLOUD_APP_SPECIFIC_PASSWORD",
]


def validate():
    """Raise if a variable required for every run is missing."""
    missing = [name for name in REQUIRED_VARS if not globals().get(name)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
