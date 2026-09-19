"""/api/app/* — public app settings."""

from fastapi import APIRouter

import config
from services import providers

router = APIRouter(prefix="/app", tags=["app"])


@router.get("/public-settings")
async def public_settings() -> dict:
    """
    Everything the frontend needs before a user signs in.

    Safe to publish: the provider block names the model and whether a key is
    present, never the key itself.
    """
    return {
        "app_name": config.APP_NAME,
        "google_oauth_enabled": False,
        "email_verification_required": config.EMAIL_VERIFICATION_REQUIRED,
        "demo_mode": config.DEMO_MODE,
        "plans": config.PLANS,
        "llm": providers.status(),
    }
