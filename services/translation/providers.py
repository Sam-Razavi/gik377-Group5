"""Översättningsproviders.

Ansvarig: Nina Bentmosse
Modul: Översättningstjänst – providers

Välj provider via TRANSLATION_PROVIDER i .env:
    libretranslate  — gratis, self-hosted eller publik instans (standard)
    google          — Google Cloud Translate
    mock            — returnerar originaltext med prefix (för tester)
"""

import os
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LibreTranslate
# ---------------------------------------------------------------------------

class LibreTranslateProvider:
    """LibreTranslate – gratis och open source via HTTP.

    Kräver:
        pip install requests
        LIBRETRANSLATE_URL=https://libretranslate.com  (eller self-hosted)
        LIBRETRANSLATE_API_KEY=...                     (krävs på publik instans)
    """

    def __init__(self):
        # Läs URL och API-nyckel från miljövariabler
        self.url = os.environ.get("LIBRETRANSLATE_URL", "https://libretranslate.com").rstrip("/")
        self.api_key = os.environ.get("LIBRETRANSLATE_API_KEY", "")
        logger.info("LibreTranslateProvider initierad mot %s.", self.url)

    def translate(self, text: str, target_language: str) -> str:
        # Bygg upp förfrågan med text, källspråk (auto) och målspråk
        payload = {
            "q": text,
            "source": "auto",
            "target": target_language,
            "format": "text",
        }
        # Lägg till API-nyckel om en är konfigurerad
        if self.api_key:
            payload["api_key"] = self.api_key

        # Skicka POST till LibreTranslate och returnera översatt text
        response = requests.post(f"{self.url}/translate", json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("translatedText", text)

    def detect_language(self, text: str) -> Optional[str]:
        # Bygg förfrågan för språkdetektering
        payload = {"q": text}
        if self.api_key:
            payload["api_key"] = self.api_key

        # Skicka POST och returnera ISO-koden för det detekterade språket
        response = requests.post(f"{self.url}/detect", json=payload, timeout=10)
        response.raise_for_status()
        results = response.json()
        if results:
            return results[0].get("language")
        return None


# ---------------------------------------------------------------------------
# Google Cloud Translate
# ---------------------------------------------------------------------------

class GoogleTranslateProvider:
    """Google Cloud Translate v2.

    Kräver:
        pip install google-cloud-translate
        GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json  (eller ADC)
    """

    def __init__(self):
        # Initierar Google Cloud-klienten via ADC eller nyckel-fil
        from google.cloud import translate_v2 as google_translate
        self._client = google_translate.Client()
        logger.info("GoogleTranslateProvider initierad.")

    def translate(self, text: str, target_language: str) -> str:
        # Skickar text till Google och returnerar den översatta strängen
        result = self._client.translate(text, target_language=target_language)
        return result["translatedText"]

    def detect_language(self, text: str) -> Optional[str]:
        # Detekterar språk via Google och returnerar ISO-kod
        result = self._client.detect_language(text)
        return result.get("language")


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

class MockProvider:
    """Enkel mock för tester – returnerar originaltext med prefix."""

    def translate(self, text: str, target_language: str) -> str:
        # Returnerar texten oförändrad med ett tydligt mock-prefix
        return f"[mock:{target_language}] {text}"

    def detect_language(self, text: str) -> Optional[str]:
        # Returnerar alltid "und" (odefinierat) — ingen riktig detektering
        return "und"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_provider():
    """Bygg rätt provider baserat på TRANSLATION_PROVIDER env-variabel."""
    name = os.environ.get("TRANSLATION_PROVIDER", "libretranslate").lower()

    if name == "google":
        try:
            return GoogleTranslateProvider()
        except Exception as e:
            # Om Google inte kan initieras faller vi tillbaka till mock
            logger.warning("Google Translate kunde inte initieras, faller tillbaka till mock: %s", e)

    elif name == "libretranslate":
        try:
            return LibreTranslateProvider()
        except Exception as e:
            # Om LibreTranslate inte kan initieras faller vi tillbaka till mock
            logger.warning("LibreTranslate kunde inte initieras, faller tillbaka till mock: %s", e)

    logger.info("Använder mock-översättningsprovider.")
    return MockProvider()


__all__ = ["LibreTranslateProvider", "GoogleTranslateProvider", "MockProvider", "build_provider"]
