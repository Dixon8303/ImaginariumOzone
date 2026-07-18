"""Push (ntfy) and text-message (carrier email-to-SMS gateway) notifications."""

import smtplib
from email.mime.text import MIMEText

import requests

from . import config


def send_push(title, message):
    if not config.NTFY_TOPIC:
        return
    requests.post(
        f"{config.NTFY_SERVER}/{config.NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title},
        timeout=15,
    )


def send_sms(message):
    if not (
        config.SMS_GATEWAY_ADDRESS
        and config.GMAIL_ADDRESS
        and config.GMAIL_APP_PASSWORD
    ):
        return

    # Carrier email-to-SMS gateways typically truncate long messages.
    mime = MIMEText(message[:300])
    mime["From"] = config.GMAIL_ADDRESS
    mime["To"] = config.SMS_GATEWAY_ADDRESS
    mime["Subject"] = ""

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        smtp.send_message(mime)


def notify(title, message):
    send_push(title, message)
    send_sms(message)
