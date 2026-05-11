import os
from dotenv import load_dotenv

# Ladda .env från projektets rot
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def _require_env(key):
    """Kraschar tydligt om en miljövariabel saknas."""
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Miljövariabel '{key}' saknas. "
            f"Lägg till den i .env eller som systemvariabel."
        )
    return value


# HelloSMS (SMS-provider)
HELLOSMS_API_URL = os.getenv("HELLOSMS_API_URL", "https://api.hellosms.se/v1/")
HELLOSMS_USERNAME = _require_env("HELLOSMS_USERNAME")
HELLOSMS_PASSWORD = _require_env("HELLOSMS_PASSWORD")

# SMTP2GO (E-post-provider)
SMTP2GO_API_URL = os.getenv("SMTP2GO_API_URL", "https://api.smtp2go.com/v3/")
SMTP2GO_API_KEY = _require_env("SMTP2GO_API_KEY")
SMTP2GO_SENDER = os.getenv("SMTP2GO_SENDER", "noreply@nordicdigitalsolutions.se")

# Debug-token för skyddade endpoints (t.ex. /subscribers)
ADMIN_TOKEN = os.getenv("NOTIFICATION_ADMIN_TOKEN", "")

# Bas-URL till sidan som visar världsarvsinformation.
# Backend bygger länken som "{SITE_PAGE_BASE_URL}?id={site_id}".
SITE_PAGE_BASE_URL = os.getenv(
    "SITE_PAGE_BASE_URL",
    "https://nordicdigitalsolutions.se/site.html",
)

# Anti-spam: cooldown per kanal och världsarv (anges i TIMMAR).
# SMS kostar mer än e-post, därför längre fönster för SMS.
# Default: 720 timmar (30 dagar) för SMS, 168 timmar (7 dagar) för e-post.
COOLDOWN_SMS_HOURS = int(os.getenv("NOTIFICATION_COOLDOWN_SMS_HOURS", "720"))
COOLDOWN_EMAIL_HOURS = int(os.getenv("NOTIFICATION_COOLDOWN_EMAIL_HOURS", "168"))

# Räknas om till sekunder internt (timestamps i DB är i sekunder).
COOLDOWN_SMS_SECONDS = COOLDOWN_SMS_HOURS * 3600
COOLDOWN_EMAIL_SECONDS = COOLDOWN_EMAIL_HOURS * 3600

# PostgreSQL-anslutning
PG_HOST = os.getenv("NOTIFICATION_PG_HOST", "localhost")
PG_PORT = int(os.getenv("NOTIFICATION_PG_PORT", "5432"))
PG_DATABASE = os.getenv("NOTIFICATION_PG_DATABASE", "notification")
PG_USER = _require_env("NOTIFICATION_PG_USER")
PG_PASSWORD = _require_env("NOTIFICATION_PG_PASSWORD")
