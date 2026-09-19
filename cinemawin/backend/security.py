"""
CinemaWin security — PBKDF2 password hashing, HS256 JWTs, auth dependency.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request

import config
import database

_HASH_SCHEME = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, config.PBKDF2_ITERATIONS
    )
    return f"{_HASH_SCHEME}${config.PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, hash_hex = stored.split("$", 3)
        if scheme != _HASH_SCHEME:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=config.JWT_EXPIRY_DAYS)).timestamp()),
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def _bearer_token(request: Request) -> Optional[str]:
    header = request.headers.get("authorization", "")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: resolves the bearer JWT to a User dict, or 401."""
    token = _bearer_token(request)
    if token is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="invalid_token")
    row = await database.get_user_by_id(payload["sub"])
    if row is None:
        raise HTTPException(status_code=401, detail="invalid_token")
    return database.row_to_user(row)


CurrentUser = Depends(get_current_user)
