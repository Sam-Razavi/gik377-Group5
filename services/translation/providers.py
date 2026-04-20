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
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Google Cloud Translate
# ---------------------------------------------------------------------------

class GoogleTranslateProvider:
    """Google Cloud Translate v2 — primär översättningsprovider.

    Kräver:
        pip install google-cloud-translate
        GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json  (eller ADC)
    """

    def __init__(self):
        # Importerar Google-klienten och initierar via credentials-fil eller ADC
        from google.cloud import translate_v2 as google_translate
        self._client = google_translate.Client()
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
    """Bygg rätt provider — försöker alltid Google först.

    Faller tillbaka till MockProvider om Google inte är konfigurerat.
    """
    # Försöker alltid starta Google oavsett vad TRANSLATION_PROVIDER är satt till
    try:
        provider = GoogleTranslateProvider()
        logger.info("Translation provider: Google Cloud Translate")
        return provider
    except Exception as e:
        # Google saknar credentials eller bibliotek — kör mock istället
        logger.warning("Google Translate kunde inte initieras, faller tillbaka till mock: %s", e)

    logger.info("Translation provider: Mock (ingen riktig översättning)")
    return MockProvider()


__all__ = ["GoogleTranslateProvider", "MockProvider", "build_provider"]
