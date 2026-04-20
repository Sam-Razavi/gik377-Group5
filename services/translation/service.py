"""Översättningstjänst – legobit.

Ansvarig: Nina Bentmosse
Modul: services/translation/service.py

Google Cloud Translate används alltid som primär provider.
Faller automatiskt tillbaka till Mock om credentials saknas.

Providers:
    google — Google Cloud Translate (primär)
    mock   — returnerar originaltext med prefix (automatisk fallback)

Publika metoder:
    TranslationService.translate(text, target_language) -> str
    TranslationService.detect_language(text)            -> str | None
    TranslationService.supported_languages()            -> list[dict]
"""

from __future__ import annotations
import logging
from typing import Optional
from .providers import build_provider, MockProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Alla språk som Google Translate stöder (ISO-639-1 koder).
# Används för validering och för att exponera listan via API.
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES: dict[str, str] = {
    "af": "Afrikaans",
    "sq": "Albanska",
    "am": "Amhariska",
    "ar": "Arabiska",
    "hy": "Armeniska",
    "az": "Azerbajdzjanska",
    "eu": "Baskiska",
    "be": "Vitryska",
    "bn": "Bengaliska",
    "bs": "Bosniska",
    "bg": "Bulgariska",
    "ca": "Katalanska",
    "ceb": "Cebuano",
    "zh": "Kinesiska (förenklad)",
    "zh-TW": "Kinesiska (traditionell)",
    "co": "Korsikanska",
    "hr": "Kroatiska",
    "cs": "Tjeckiska",
    "da": "Danska",
    "nl": "Nederländska",
    "en": "Engelska",
    "eo": "Esperanto",
    "et": "Estniska",
    "fi": "Finska",
    "fr": "Franska",
    "fy": "Frisiska",
    "gl": "Galiciska",
    "ka": "Georgiska",
    "de": "Tyska",
    "el": "Grekiska",
    "gu": "Gujarati",
    "ht": "Haitisk kreol",
    "ha": "Hausa",
    "haw": "Hawaiianska",
    "he": "Hebreiska",
    "hi": "Hindi",
    "hmn": "Hmong",
    "hu": "Ungerska",
    "is": "Isländska",
    "ig": "Igbo",
    "id": "Indonesiska",
    "ga": "Iriska",
    "it": "Italienska",
    "ja": "Japanska",
    "jv": "Javanesiska",
    "kn": "Kannada",
    "kk": "Kazakiska",
    "km": "Khmer",
    "rw": "Kinyarwanda",
    "ko": "Koreanska",
    "ku": "Kurdiska",
    "ky": "Kirgisiska",
    "lo": "Laotiska",
    "la": "Latin",
    "lv": "Lettiska",
    "lt": "Litauiska",
    "lb": "Luxemburgiska",
    "mk": "Makedonska",
    "mg": "Malagassiska",
    "ms": "Malajiska",
    "ml": "Malayalam",
    "mt": "Maltesiska",
    "mi": "Maori",
    "mr": "Marathi",
    "mn": "Mongoliska",
    "my": "Burmesiska",
    "ne": "Nepalesiska",
    "no": "Norska",
    "ny": "Nyanja",
    "or": "Odia",
    "ps": "Pashto",
    "fa": "Persiska",
    "pl": "Polska",
    "pt": "Portugisiska",
    "pa": "Punjabi",
    "ro": "Rumänska",
    "ru": "Ryska",
    "sm": "Samoanska",
    "gd": "Skotsk gaeliska",
    "sr": "Serbiska",
    "st": "Sesotho",
    "sn": "Shona",
    "sd": "Sindhi",
    "si": "Singalesiska",
    "sk": "Slovakiska",
    "sl": "Slovenska",
    "so": "Somaliska",
    "es": "Spanska",
    "su": "Sundanesiska",
    "sw": "Swahili",
    "sv": "Svenska",
    "tl": "Tagalog",
    "tg": "Tadzjikiska",
    "ta": "Tamilska",
    "tt": "Tatariska",
    "te": "Telugu",
    "th": "Thailändska",
    "tr": "Turkiska",
    "tk": "Turkmeniska",
    "uk": "Ukrainska",
    "ur": "Urdu",
    "ug": "Uiguriska",
    "uz": "Uzbekiska",
    "vi": "Vietnamesiska",
    "cy": "Walesiska",
    "xh": "Xhosa",
    "yi": "Jiddisch",
    "yo": "Yoruba",
    "zu": "Zulu",
}


class TranslationService:
    """Översättningstjänst med utbytbara providers (Google, Mock).

    Stöder alla världsspråk som den valda providern hanterar.
    Validering sker mot SUPPORTED_LANGUAGES-ordboken ovan.
    """

    def __init__(self) -> None:
        self._provider = build_provider()
        logger.info("TranslationService initierad med provider: %s", type(self._provider).__name__)

    # ------------------------------------------------------------------
    # Publikt API
    # ------------------------------------------------------------------

    def translate(self, text: str, target_language: str = "en") -> str:
        """Översätt text till valfritt mål-språk.

        Args:
            text:            Texten som ska översättas.
            target_language: ISO-639-1 kod, t.ex. "sv", "ja", "ar".

        Returns:
            Översatt text, eller mock-sträng om providern misslyckas.

        Raises:
            ValueError: Om target_language inte finns i SUPPORTED_LANGUAGES.
        """
        if not text:
            return ""

        if target_language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Språkkoden '{target_language}' stöds inte. "
                f"Använd en giltig ISO-639-1 kod, t.ex. 'sv', 'en', 'ja'. "
                f"Se /languages för fullständig lista."
            )

        try:
            result = self._provider.translate(text, target_language)
            logger.debug("Översatte %d tecken till '%s'.", len(text), target_language)
            return result
        except Exception:
            logger.exception("Provider misslyckades – använder mock-fallback.")
            return MockProvider().translate(text, target_language)

    def detect_language(self, text: str) -> Optional[str]:
        """Detektera vilket språk texten är skriven på.

        Returns:
            ISO-639-1 kod (t.ex. "sv"), "und" vid fel, eller None om tom text.
        """
        if not text:
            return None

        try:
            lang = self._provider.detect_language(text)
            logger.debug("Detekterat språk: '%s'.", lang)
            return lang
        except Exception:
            logger.exception("Språkdetektering misslyckades – returnerar 'und'.")
            return "und"

    def supported_languages(self) -> list[dict]:
        """Returnera lista med alla stödda språk.

        Returns:
            Lista med dicts: [{"code": "sv", "name": "Svenska"}, ...]
        """
        return [
            {"code": code, "name": name}
            for code, name in sorted(SUPPORTED_LANGUAGES.items(), key=lambda x: x[1])
        ]


__all__ = ["TranslationService", "SUPPORTED_LANGUAGES"]
