"""
Providerabstraktion för SMS och e-post.
Varje provider implementerar send() och kan bytas ut utan kodändringar.
"""

import requests
from services.notification.config import (
    HELLOSMS_API_URL,
    HELLOSMS_USERNAME,
    HELLOSMS_PASSWORD,
    SMTP2GO_API_URL,
    SMTP2GO_API_KEY,
    SMTP2GO_SENDER,
)


class SMSProvider:
    """Skickar SMS via HelloSMS API."""

    def send(self, to, message, sender="UNESCO"):
        url = f"{HELLOSMS_API_URL}sms/send"
        payload = {
            "from": sender,
            "to": to,
            "message": message,
        }
        try:
            resp = requests.post(
                url,
                json=payload,
                auth=(HELLOSMS_USERNAME, HELLOSMS_PASSWORD),
                timeout=10,
            )
            resp.raise_for_status()
            return {"success": True, "provider": "hellosms", "detail": resp.json()}
        except requests.RequestException as e:
            return {"success": False, "provider": "hellosms", "error": str(e)}


class EmailProvider:
    """Skickar e-post via SMTP2GO API."""

    def send(self, to, subject, message, sender=None):
        url = f"{SMTP2GO_API_URL}email/send"
        payload = {
            "api_key": SMTP2GO_API_KEY,
            "to": [to],
            "sender": sender or SMTP2GO_SENDER,
            "subject": subject,
            "text_body": message,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return {"success": True, "provider": "smtp2go", "detail": resp.json()}
        except requests.RequestException as e:
            return {"success": False, "provider": "smtp2go", "error": str(e)}
