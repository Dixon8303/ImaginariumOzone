"""/api/auth/* — email/password auth, OTP verification, password reset."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import config
import database
import security
from services import mailer

log = logging.getLogger("cinemawin.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


def _norm_email(email: str) -> str:
    return email.strip().lower()


def _expiry(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=config.PASSWORD_MIN_LENGTH, max_length=1024)


class LoginBody(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class EmailBody(BaseModel):
    email: str = Field(min_length=1, max_length=320)


class VerifyOtpBody(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    code: str = Field(min_length=1, max_length=16)


class ResetPasswordBody(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=config.PASSWORD_MIN_LENGTH, max_length=1024)


def _issue(user: dict) -> dict:
    return {
        "access_token": security.create_access_token(user["id"], user["email"]),
        "user": user,
    }


async def _send_new_otp(email: str) -> None:
    code = f"{secrets.randbelow(1_000_000):06d}"
    await database.create_otp(email, code, _expiry(config.OTP_EXPIRY_MINUTES))
    if not await mailer.send_otp(email, code):
        # SMTP is configured but the send failed. Without this the account is
        # unrecoverable: registration reports verification_required and the
        # code exists nowhere the operator can reach.
        log.warning("OTP email to %s failed to send. Code for manual delivery: %s", email, code)


@router.post("/register")
async def register(body: Credentials) -> dict:
    email = _norm_email(body.email)
    if "@" not in email:
        raise HTTPException(status_code=422, detail="invalid_email")
    if await database.get_user_by_email(email) is not None:
        raise HTTPException(status_code=409, detail="email_already_registered")

    verification_required = config.EMAIL_VERIFICATION_REQUIRED
    user = await database.create_user(
        email, security.hash_password(body.password), verified=not verification_required
    )
    if verification_required:
        await _send_new_otp(email)
        return {"verification_required": True, "access_token": None, "user": None}
    return {"verification_required": False, **_issue(user)}


@router.post("/verify-otp")
async def verify_otp(body: VerifyOtpBody) -> dict:
    email = _norm_email(body.email)
    if not await database.consume_otp(email, body.code.strip()):
        raise HTTPException(status_code=400, detail="invalid_or_expired_code")
    await database.mark_user_verified(email)
    row = await database.get_user_by_email(email)
    if row is None:
        raise HTTPException(status_code=400, detail="invalid_or_expired_code")
    return _issue(database.row_to_user(row))


@router.post("/resend-otp")
async def resend_otp(body: EmailBody) -> dict:
    email = _norm_email(body.email)
    row = await database.get_user_by_email(email)
    if row is not None and not row["email_verified"]:
        await _send_new_otp(email)
    return {"ok": True}


@router.post("/login")
async def login(body: LoginBody) -> dict:
    email = _norm_email(body.email)
    row = await database.get_user_by_email(email)
    if row is None or not security.verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    if not row["email_verified"]:
        raise HTTPException(status_code=403, detail="email_not_verified")
    return _issue(database.row_to_user(row))


@router.get("/me")
async def me(user: dict = security.CurrentUser) -> dict:
    return user


@router.post("/logout")
async def logout() -> dict:
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(body: EmailBody) -> dict:
    email = _norm_email(body.email)
    row = await database.get_user_by_email(email)
    if row is not None:
        token = secrets.token_urlsafe(32)
        await database.create_reset_token(
            row["id"], token, _expiry(config.RESET_TOKEN_EXPIRY_MINUTES)
        )
        url = f"{config.PUBLIC_URL}/reset-password?token={token}"
        sent = await mailer.send_password_reset(email, url)
        if not sent:
            log.info("Password reset URL for %s: %s", email, url)
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordBody) -> dict:
    user_id: Optional[str] = await database.consume_reset_token(body.token.strip())
    if user_id is None:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    await database.set_user_password(user_id, security.hash_password(body.new_password))
    return {"ok": True}
