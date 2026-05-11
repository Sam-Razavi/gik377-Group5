"""
Providerabstraktion för SMS och e-post.

Varje provider implementerar send() och kan bytas ut utan kodändringar
i service-/routes-lagret. Det publika svarsformatet är leverantörsneutralt
så att andra grupper kan byta ut hela notifieringsmodulen bakom samma API
utan att deras kod påverkas (kurskrav 1.2 / 1.3).

Returformat (neutralt):
    success: bool
    channel: "sms" | "email"
    error:   str      (endast vid misslyckande)
    detail:  dict     (valfri, intern diagnostikdata)
"""

import logging
import time

import requests

from services.notification.config import (
    HELLOSMS_API_URL,
    HELLOSMS_USERNAME,
    HELLOSMS_PASSWORD,
    SMTP2GO_API_URL,
    SMTP2GO_API_KEY,
    SMTP2GO_SENDER,
)

logger = logging.getLogger("notification")

# Retry-konfiguration för transienta fel (nätverksfel + 5xx från provider).
# 4xx retriar vi inte – det betyder vårt eget anrop är fel och retry hjälper inte.
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0  # 1s, 2s, 4s ...


def _post_with_retry(url, channel, **kwargs):
    """
    Skickar POST till provider-API med retry vid transienta fel.

    Retriar vid:
      - requests.ConnectionError, Timeout (nätverksfel)
      - HTTP 5xx från servern

    Retriar INTE vid:
      - HTTP 4xx (klientfel – vårt anrop är fel, retry hjälper inte)

    Returnerar ett tuple (success, detail_or_error_string).
    """
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, timeout=10, **kwargs)
            if 500 <= resp.status_code < 600:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning(
                    "Provider %s svarade %s (försök %d/%d)",
                    channel, resp.status_code, attempt, MAX_ATTEMPTS,
                )
            else:
                resp.raise_for_status()
                return True, resp.json()
        except requests.HTTPError as e:
            # 4xx – retry hjälper inte, bryt direkt
            return False, str(e)
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = str(e)
            logger.warning(
                "Provider %s nätverksfel (försök %d/%d): %s",
                channel, attempt, MAX_ATTEMPTS, e,
            )
        except requests.RequestException as e:
            # Oväntat fel från requests – retry försiktigt
            last_error = str(e)

        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    return False, last_error or "okänt fel"


class SMSProvider:
    """
    SMS-provider. Nuvarande implementation använder HelloSMS internt,
    men det publika returformatet avslöjar inte leverantören.
    """

    def send(self, to, message, sender="UNESCO"):
        url = f"{HELLOSMS_API_URL}sms/send"
        payload = {
            "from": sender,
            "to": to,
            "message": message,
        }
        success, result = _post_with_retry(
            url,
            channel="sms",
            json=payload,
            auth=(HELLOSMS_USERNAME, HELLOSMS_PASSWORD),
        )
        if success:
            return {"success": True, "channel": "sms", "detail": result}
        return {"success": False, "channel": "sms", "error": result}


class MockSMSProvider:
    """SMS-provider for local demo mode without HelloSMS credentials."""

    def send(self, to, message, sender="UNESCO"):
        logger.info("[MOCK SMS] to=%s message=%s", to, message)
        return {"success": True, "channel": "sms", "detail": {"mock": True}}


class EmailProvider:
    """
    E-post-provider. Nuvarande implementation använder SMTP2GO internt,
    men det publika returformatet avslöjar inte leverantören.
    """

    def send(self, to, subject, message, sender=None):
        url = f"{SMTP2GO_API_URL}email/send"
        payload = {
            "api_key": SMTP2GO_API_KEY,
            "to": [to],
            "sender": sender or SMTP2GO_SENDER,
            "subject": subject,
            "text_body": message,
        }
        success, result = _post_with_retry(url, channel="email", json=payload)
        if success:
            return {"success": True, "channel": "email", "detail": result}
        return {"success": False, "channel": "email", "error": result}


class MockEmailProvider:
    """Email-provider for local demo mode without SMTP2GO credentials."""

    def send(self, to, subject, message, sender=None):
        logger.info("[MOCK EMAIL] to=%s subject=%s", to, subject)
        return {"success": True, "channel": "email", "detail": {"mock": True}}
