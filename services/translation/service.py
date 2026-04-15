"""Översättningstjänst.

Ansvarig: Nina Bentmosse
Modul: Översättningstjänst

Provider väljs via TRANSLATION_PROVIDER i .env:
    libretranslate  — gratis, self-hosted eller publik instans (standard)
    google          — Google Cloud Translate
    mock            — returnerar originaltext med prefix (för tester)

Publika metoder:
- TranslationService.translate(text, target_language) -> str
- TranslationService.detect_language(text) -> str
"""

from typing import Optional
from .providers import build_provider, MockProvider

# De fem nordiska språk som tjänsten stöder (ISO-639-1 koder)
SUPPORTED_LANGUAGES = {"sv", "en", "fi", "no", "da"}


class TranslationService:
    """Översättningstjänst med utbytbara providers (LibreTranslate, Google, Mock).

    Stödda språk: svenska (sv), engelska (en), finska (fi), norska (no), danska (da).
    """

    def __init__(self):
        # Bygg vald provider baserat på TRANSLATION_PROVIDER i .env
        self._provider = build_provider()

    def translate(self, text: str, target_language: str = "en") -> str:
        """Översätt text till ett nordiskt mål-språk (sv, en, fi, no, da)."""
        # Returnera tom sträng direkt om ingen text skickas in
        if not text:
            return ""

        # Kontrollera att målspråket finns bland de stödda nordiska språken
        if target_language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Språket '{target_language}' stöds inte. "
                f"Välj ett av: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
            )

        try:
            # Försök översätta med vald provider (t.ex. LibreTranslate)
            return self._provider.translate(text, target_language)
        except Exception as e:
            import logging
            # Om översättningen misslyckas loggas felet och mock används som fallback
            logging.getLogger(__name__).exception("Translate misslyckades, faller tillbaka till mock: %s", e)
            return MockProvider().translate(text, target_language)

    def detect_language(self, text: str) -> Optional[str]:
        """Detektera språk för given text. Returnerar ISO-kod eller None."""
        # Returnera None direkt om ingen text skickas in
        if not text:
            return None

        try:
            # Försök detektera språk med vald provider
            return self._provider.detect_language(text)
        except Exception as e:
            import logging
            # Vid fel loggas undantaget och "und" (odefinierat) returneras
            logging.getLogger(__name__).exception("Detect language misslyckades: %s", e)
            return "und"


__all__ = ["TranslationService"]
