"""Översättningsproviders.

Ansvarig: Nina Bentmosse
Modul: Översättningstjänst – providers

Providers:
- GoogleTranslateProvider : Google Cloud Translate v2 (primär)
- MockProvider            : Fallback för utveckling utan API-nyckel

Google används alltid som primär provider.
Mock används automatiskt som fallback om Google-credentials saknas.
TRANSLATION_PROVIDER i .env läses inte — Google provas alltid först.
"""

import logging
import os
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/cloud-translation"]


def _load_oauth_credentials(client_secret_path: str):
    """Ladda OAuth 2.0-credentials från client secret-fil.

    Kör ett lokalt OAuth-flöde första gången (öppnar webbläsare).
    Sparar token i token.json bredvid client_secret-filen för framtida anrop.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    token_path = os.path.join(os.path.dirname(os.path.abspath(client_secret_path)), "token.json")

    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, _SCOPES)
        except Exception:
            os.remove(token_path)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, _SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as fh:
            fh.write(creds.to_json())
        logger.info("OAuth-token sparad i %s", token_path)

    return creds


# ---------------------------------------------------------------------------
# Google Cloud Translate
# ---------------------------------------------------------------------------

class GoogleTranslateProvider:
    """Google Cloud Translate v2 — primär översättningsprovider.

    Kräver antingen:
        GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json  (service account)
        GOOGLE_CLIENT_SECRET_FILE=path/to/client_secret_*.json        (OAuth 2.0)
    """

    def __init__(self, credentials=None):
        from google.cloud import translate_v2 as google_translate
        self._client = google_translate.Client(credentials=credentials)
        logger.info("GoogleTranslateProvider initierad.")

    def translate(self, text: str, target_language: str) -> str:
        # Skickar text till Google och returnerar den översatta strängen
        result = self._client.translate(text, target_language=target_language)
        return result["translatedText"]

    def detect_language(self, text: str) -> Optional[str]:
        # Detekterar språk via Google och returnerar ISO-kod (t.ex. "sv", "en")
        result = self._client.detect_language(text)
        return result.get("language")

    def get_languages(self) -> List[Dict]:
        # Hämtar alla språk som Google Translate stödjer
        results = self._client.get_languages()
        return [{"code": r["language"], "name": r.get("name", r["language"])} for r in results]


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

class MockProvider:
    """Fallback-provider för utveckling utan API-nyckel.

    Används automatiskt om Google inte är konfigurerat.
    Returnerar originaltext med prefix [mock:språkkod].
    """

    def translate(self, text: str, target_language: str) -> str:
        # Returnerar texten oförändrad med ett tydligt mock-prefix
        return f"[mock:{target_language}] {text}"

    def detect_language(self, _text: str) -> Optional[str]:
        # Kan inte detektera språk — returnerar "und" (undefined)
        return "und"

    def get_languages(self) -> List[Dict]:
        # Returnerar ett fast urval av vanliga språk för testmiljö
        return [
            {"code": "sv", "name": "Swedish"},
            {"code": "en", "name": "English"},
            {"code": "no", "name": "Norwegian"},
            {"code": "da", "name": "Danish"},
            {"code": "fi", "name": "Finnish"},
            {"code": "de", "name": "German"},
            {"code": "fr", "name": "French"},
            {"code": "es", "name": "Spanish"},
            {"code": "ar", "name": "Arabic"},
            {"code": "zh", "name": "Chinese"},
        ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_provider():
    """Bygg rätt provider.

    Prioritet:
        1. OAuth 2.0 via GOOGLE_CLIENT_SECRET_FILE (kör browser-flöde första gången)
        2. Service account via GOOGLE_APPLICATION_CREDENTIALS (ADC)
        3. MockProvider (fallback utan credentials)
    """
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET_FILE")
    if client_secret and os.path.exists(client_secret):
        try:
            creds = _load_oauth_credentials(client_secret)
            provider = GoogleTranslateProvider(credentials=creds)
            logger.info("Translation provider: Google Cloud Translate (OAuth 2.0)")
            return provider
        except Exception as e:
            logger.warning("OAuth-initiering misslyckades, provar ADC: %s", e)

    try:
        provider = GoogleTranslateProvider()
        logger.info("Translation provider: Google Cloud Translate (ADC/service account)")
        return provider
    except Exception as e:
        logger.warning("Google Translate kunde inte initieras, faller tillbaka till mock: %s", e)

    logger.info("Translation provider: Mock (ingen riktig översättning)")
    return MockProvider()


__all__ = ["GoogleTranslateProvider", "MockProvider", "build_provider"]
