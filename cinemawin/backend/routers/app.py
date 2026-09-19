"""/api/app/* — public app settings."""

from fastapi import APIRouter

import config

router = APIRouter(prefix="/app", tags=["app"])


@router.get("/public-settings")
async def public_settings() -> dict:
    return {
        "app_name": config.APP_NAME,
        "google_oauth_enabled": False,
        "email_verification_required": config.EMAIL_VERIFICATION_REQUIRED,
        "demo_mode": config.DEMO_MODE,
        "plans": config.PLANS,
    }
