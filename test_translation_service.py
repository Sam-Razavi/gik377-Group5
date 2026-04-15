"""Tester för TranslationService.

Kör med: python -m pytest test_translation_service.py -v
Alla tester använder mock-läge via TRANSLATION_PROVIDER=mock,
ingen extern tjänst krävs.
"""

import os

os.environ.setdefault("TRANSLATION_PROVIDER", "mock")

from services.translation.service import TranslationService
from services.translation.providers import MockProvider


class TestMockProvider:
    def setup_method(self):
        self.provider = MockProvider()

    def test_translate_returnerar_prefix(self):
        result = self.provider.translate("Hello", "sv")
        assert result == "[mock:sv] Hello"

    def test_translate_annan_kod(self):
        result = self.provider.translate("Bonjour", "en")
        assert result == "[mock:en] Bonjour"

    def test_detect_language_returnerar_und(self):
        result = self.provider.detect_language("test")
        assert result == "und"


class TestTranslationService:
    def setup_method(self):
        os.environ["TRANSLATION_PROVIDER"] = "mock"
        self.service = TranslationService()

    def test_translate_tom_text_returnerar_tom_strang(self):
        assert self.service.translate("") == ""

    def test_translate_returnerar_mockformat(self):
        result = self.service.translate("Hej världen", "en")
        assert result == "[mock:en] Hej världen"

    def test_translate_standard_sprak_ar_en(self):
        result = self.service.translate("text")
        assert "[mock:en]" in result

    def test_detect_language_tom_text_returnerar_none(self):
        assert self.service.detect_language("") is None

    def test_detect_language_returnerar_strang(self):
        result = self.service.detect_language("Hej")
        assert isinstance(result, str)

    def test_fallback_om_provider_kastar(self, monkeypatch):
        """Om primär provider kastar ska MockProvider användas som fallback."""
        def kastar(*_):
            raise RuntimeError("simulerat fel")

        monkeypatch.setattr(self.service._provider, "translate", kastar)
        result = self.service.translate("Test", "sv")
        assert result == "[mock:sv] Test"
