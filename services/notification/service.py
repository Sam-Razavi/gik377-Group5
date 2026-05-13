# Ansvarig: Riyaaq Ali
# Modul: Notification Service (SMS/mail)
# Gemensamt API för meddelandetjänst – ska kunna återanvändas av andra kursgrupper

import logging
import re
from services.notification.providers import (
    EmailProvider,
    MockEmailProvider,
    MockSMSProvider,
    SMSProvider,
)
from services.notification.config import (
    COOLDOWN_SMS_SECONDS,
    COOLDOWN_EMAIL_SECONDS,
    NOTIFICATION_MOCK_MODE,
    SMS_MOCK_MODE,
    EMAIL_MOCK_MODE,
    SITE_PAGE_BASE_URL,
)
from services.notification import db
from services.notification import messages

logger = logging.getLogger("notification")

# Initiera databasen vid import
db.init_db()

# Provider-instanser väljs per kanal baserat på tillgängliga credentials
sms_provider = MockSMSProvider() if (SMS_MOCK_MODE or db.using_mock_storage()) else SMSProvider()
email_provider = MockEmailProvider() if (EMAIL_MOCK_MODE or db.using_mock_storage()) else EmailProvider()

VALID_TYPES = ("sms", "email")
_PHONE_RE = re.compile(r"^\+?[0-9\s\-]{7,15}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


_COOLDOWN_BY_CHANNEL = {
    "sms": COOLDOWN_SMS_SECONDS,
    "email": COOLDOWN_EMAIL_SECONDS,
}


def _is_on_cooldown(user_id, site_id, channel):
    import time
    last = db.get_last_sent(user_id, site_id, channel)
    window = _COOLDOWN_BY_CHANNEL.get(channel, 0)
    return (time.time() - last) < window


def validate_recipient(notification_type, to):
    """Validerar mottagare beroende på typ. Returnerar felmeddelande eller None."""
    if notification_type == "sms":
        if not _PHONE_RE.match(to):
            return "Ogiltigt telefonnummer. Förväntat format: +46701234567"
    elif notification_type == "email":
        if not _EMAIL_RE.match(to):
            return "Ogiltig e-postadress."
    return None


def send_notification(notification_type, to, message, **kwargs):
    """
    Gemensamt API - skickar SMS eller e-post.

    Parametrar:
        notification_type: "sms" eller "email"
        to: mottagare (telefonnummer eller e-postadress)
        message: meddelandetext
        subject: (valfritt, för e-post)
        user_id: (valfritt, för anti-spam)
        site_id: (valfritt, för anti-spam)
    """
    if notification_type not in VALID_TYPES:
        return {"success": False, "error": "invalid_channel",
                "message": "Ogiltig kanal. Använd 'sms' eller 'email'."}

    validation_error = validate_recipient(notification_type, to)
    if validation_error:
        return {"success": False, "error": "invalid_recipient",
                "message": validation_error}

    user_id = kwargs.get("user_id")
    site_id = kwargs.get("site_id")

    if user_id and site_id and _is_on_cooldown(user_id, site_id, notification_type):
        logger.info("Cooldown aktiv för user=%s site=%s kanal=%s", user_id, site_id, notification_type)
        return {
            "success": False,
            "error": "cooldown",
            "message": "Notifiering redan skickad för denna plats och kanal nyligen.",
        }

    if notification_type == "sms":
        result = sms_provider.send(to=to, message=message)
    else:
        subject = kwargs.get("subject", "UNESCO World Heritage – Notifiering")
        result = email_provider.send(to=to, subject=subject, message=message)

    if result["success"]:
        logger.info("Skickade %s till %s", notification_type, to)
        if user_id and site_id:
            db.mark_sent(user_id, site_id, notification_type)
    else:
        logger.warning("Misslyckades skicka %s till %s: %s", notification_type, to, result.get("error"))

    return result


def subscribe(user_id, phone=None, email=None, sites=None):
    if not user_id or not str(user_id).strip():
        return {"success": False, "error": "user_id krävs."}

    if phone and not _PHONE_RE.match(phone):
        return {"success": False, "error": "Ogiltigt telefonnummer."}
    if email and not _EMAIL_RE.match(email):
        return {"success": False, "error": "Ogiltig e-postadress."}
    if sites is not None and not isinstance(sites, list):
        return {"success": False, "error": "sites måste vara en lista."}

    is_new = not db.subscriber_exists(user_id)
    sub = db.add_subscriber(user_id, phone, email, sites)

    logger.info("Prenumeration uppdaterad för user=%s", user_id)

    # Skicka välkomstmeddelande vid ny prenumeration
    if is_new:
        _send_welcome(sub, sites)

    return {"success": True, "subscriber": sub}


def _send_welcome(sub, sites):
    """Skickar välkomstmeddelande via SMS och/eller e-post — bara om riktiga credentials finns."""
    if sub.get("phone") and not SMS_MOCK_MODE:
        sms_provider.send(to=sub["phone"], message=messages.welcome_sms())
        logger.info("Välkomst-SMS skickat till %s", sub["phone"])

    if sub.get("email") and not EMAIL_MOCK_MODE:
        email_provider.send(
            to=sub["email"],
            subject=messages.welcome_email_subject(),
            message=messages.welcome_email_body(sites),
        )
        logger.info("Välkomstmejl skickat till %s", sub["email"])


def unsubscribe(user_id, sites=None):
    if not db.subscriber_exists(user_id):
        return {"success": False, "error": "Prenumerant finns inte."}

    sub = db.get_subscriber(user_id)

    # Skicka bekräftelse innan vi tar bort
    _send_unsubscribe_confirmation(sub, sites)

    db.remove_subscriber(user_id, sites)
    logger.info("Avprenumeration för user=%s sites=%s", user_id, sites)
    return {"success": True}


def _send_unsubscribe_confirmation(sub, sites):
    """Skickar bekräftelse på avprenumeration."""
    if sub.get("phone"):
        sms_provider.send(to=sub["phone"], message=messages.unsubscribe_sms(sites))
        logger.info("Avregistrerings-SMS skickat till %s", sub["phone"])

    if sub.get("email"):
        email_provider.send(
            to=sub["email"],
            subject=messages.unsubscribe_email_subject(),
            message=messages.unsubscribe_email_body(sites),
        )
        logger.info("Avregistreringsmejl skickat till %s", sub["email"])


def get_subscribers():
    return db.get_all_subscribers()


def mark_visited(user_id, site_id):
    """Bockar av att användaren har besökt världsarvet. Stoppar framtida notiser."""
    if not user_id or not site_id:
        return {"success": False, "error": "user_id och site_id krävs."}

    if not db.subscriber_exists(user_id):
        return {"success": False, "error": "Prenumerant finns inte."}

    sub = db.get_subscriber(user_id)
    if site_id not in sub.get("sites", []):
        return {"success": False, "error": "Användaren prenumererar inte på denna plats."}

    db.mark_visited(user_id, site_id)
    logger.info("Markerade site=%s som besökt för user=%s", site_id, user_id)
    return {"success": True, "user_id": user_id, "site_id": site_id, "visited": True}


def trigger_for_location(user_id, site_id, site_name, link=None):
    """
    Triggas när en användare är nära ett världsarv.
    Skickar SMS och/eller e-post beroende på prenumeration.
    Cooldown är per kanal (sms/email) så att båda kan skickas vid samma tillfälle.
    """
    sub = db.get_subscriber(user_id)
    if not sub:
        return [{"success": False, "error": "Användaren har ingen prenumeration."}]

    if site_id not in sub.get("sites", []):
        return [{"success": False, "error": "Användaren prenumererar inte på denna plats."}]

    # Permanent block om användaren redan har bockat av världsarvet
    if db.is_visited(user_id, site_id):
        logger.info("Hoppar över notis: user=%s har redan besökt site=%s", user_id, site_id)
        return [{"success": False, "error": "already_visited",
                 "message": "Användaren har redan markerat detta världsarv som besökt."}]

    # Bygg länk till världsarvssidan om ingen länk skickats med
    if not link:
        link = f"{SITE_PAGE_BASE_URL}?id={site_id}"

    results = []
    if sub.get("phone"):
        sms_text = messages.location_sms(site_name, link)
        results.append(
            send_notification("sms", sub["phone"], sms_text, user_id=user_id, site_id=site_id)
        )
    if sub.get("email"):
        email_text = messages.location_email_body(site_name, link)
        email_subject = messages.location_email_subject(site_name)
        results.append(
            send_notification(
                "email",
                sub["email"],
                email_text,
                subject=email_subject,
                user_id=user_id,
                site_id=site_id,
            )
        )
    if not results:
        results.append({"success": False, "error": "Ingen kontaktinfo registrerad."})

    return results
