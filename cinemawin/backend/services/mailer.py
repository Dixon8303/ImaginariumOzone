"""
CinemaWin mailer — SMTP when configured, console log otherwise.

Never raises to the caller: a delivery failure is logged and the request
continues (the auth flow never leaks whether an address exists).
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

import config

log = logging.getLogger("cinemawin.mailer")


def is_configured() -> bool:
    return config.SMTP_CONFIGURED


def _send_sync(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = config.SMTP_FROM or "cinemawin@localhost"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as smtp:
        smtp.ehlo()
        try:
            smtp.starttls()
            smtp.ehlo()
        except smtplib.SMTPException:
            pass  # server may not offer STARTTLS
        if config.SMTP_USER:
            smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_email(to: str, subject: str, body: str) -> bool:
    if not is_configured():
        log.info("[mail → console] To: %s | %s\n%s", to, subject, body)
        return False
    try:
        await asyncio.to_thread(_send_sync, to, subject, body)
        return True
    except Exception as exc:  # noqa: BLE001 — degrade, never crash the request
        log.error("SMTP send to %s failed: %s", to, exc)
        return False


async def send_otp(to: str, code: str) -> bool:
    return await send_email(
        to,
        f"Your {config.APP_NAME} verification code",
        f"Your {config.APP_NAME} verification code is: {code}\n\n"
        f"It expires in {config.OTP_EXPIRY_MINUTES} minutes.",
    )


async def send_password_reset(to: str, url: str) -> bool:
    return await send_email(
        to,
        f"Reset your {config.APP_NAME} password",
        f"Open this link to choose a new password:\n\n{url}\n\n"
        f"It expires in {config.RESET_TOKEN_EXPIRY_MINUTES} minutes. "
        "If you did not request this, ignore this message.",
    )
