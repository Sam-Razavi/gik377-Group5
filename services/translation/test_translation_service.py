"""Tester för TranslationService — kör med: python -m pytest services/translation/"""

import pytest
from unittest.mock import patch
from services.translation.service import TranslationService
from services.translation.providers import MockProvider


@pytest.fixture
def service():
    with patch("services.translation.service.build_provider", return_value=MockProvider()):
        yield TranslationService()


# ---------------------------------------------------------------------------
# translate()
# ---------------------------------------------------------------------------

def test_translate_returns_mock_prefix(service):
    result = service.translate("Hej världen", target_language="en")
    assert result == "[mock:en] Hej världen"


def test_translate_to_swedish(service):
    result = service.translate("Hello world", target_language="sv")
    assert result == "[mock:sv] Hello world"


def test_translate_empty_text_returns_empty(service):
    result = service.translate("", target_language="en")
    assert result == ""


def test_translate_invalid_language_raises(service):
    with pytest.raises(ValueError, match="stöds inte"):
        service.translate("Text", target_language="xx")


def test_translate_default_language_is_english(service):
    result = service.translate("Hej")
    assert "[mock:en]" in result


# ---------------------------------------------------------------------------
# detect_language()
# ---------------------------------------------------------------------------

def test_detect_language_returns_und_for_mock(service):
    result = service.detect_language("Hej världen")
    assert result == "und"


def test_detect_language_empty_returns_none(service):
    result = service.detect_language("")
    assert result is None


# ---------------------------------------------------------------------------
# supported_languages()
# ---------------------------------------------------------------------------

def test_supported_languages_returns_list(service):
    langs = service.supported_languages()
    assert isinstance(langs, list)
    assert len(langs) > 0


def test_supported_languages_contains_swedish(service):
    langs = service.supported_languages()
    codes = [lang["code"] for lang in langs]
    assert "sv" in codes


def test_supported_languages_sorted_by_name(service):
    langs = service.supported_languages()
    names = [lang["name"] for lang in langs]
    assert names == sorted(names)


def test_supported_languages_has_code_and_name(service):
    langs = service.supported_languages()
    for lang in langs:
        assert "code" in lang
        assert "name" in lang
