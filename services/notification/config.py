import os
from dotenv import load_dotenv

# Ladda .env från notification-mappen
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


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

# Anti-spam: max 1 SMS per världsarv per "tillfälle".
# Vi definierar "tillfälle" som en tidsperiod i sekunder (default 3600 = 1 timme).
# Motivering: när en användare befinner sig nära ett världsarv räknas det som
# ett tillfälle så länge de är kvar inom tidsfönstret. Först efter att cooldown
# löpt ut kan ett nytt SMS skickas för samma plats.
COOLDOWN_SECONDS = int(os.getenv("NOTIFICATION_COOLDOWN", "3600"))

# Sökväg till SQLite-databasen
DB_PATH = os.getenv("NOTIFICATION_DB_PATH", os.path.join(
    os.path.dirname(__file__), "notification.db"
))
