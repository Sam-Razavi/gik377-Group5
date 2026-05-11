# Tester för UNESCO-data & Karttjänst
# Ansvarig: Sonia Tolouifar

from unittest.mock import MagicMock, patch

from services.unesco.service import chat_about_unesco, get_sites, get_sites_near


def test_get_sites_returns_list():
    sites = get_sites(limit=5)
    assert isinstance(sites, list)
    assert len(sites) > 0


def test_get_sites_has_required_fields():
    sites = get_sites(limit=1)
    site = sites[0]
    assert "name_en" in site
    assert "coordinates" in site


def test_get_sites_near_returns_list():
    sites = get_sites_near()
    assert isinstance(sites, list)


def test_get_sites_near_sorted_by_distance():
    sites = get_sites_near()
    distances = [s["distance_km"] for s in sites]
    assert distances == sorted(distances)


def test_chat_returns_string(mocker):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Gammelstaden är ett medeltida stadscentrum.")]
    mocker.patch("services.unesco.service.anthropic.Anthropic").return_value.messages.create.return_value = mock_response

    result = chat_about_unesco("Berätta om Gammelstaden", [])
    assert isinstance(result, str)
    assert len(result) > 0


def test_chat_system_prompt_restricts_off_topic(mocker):
    captured = {}

    def fake_create(**kwargs):
        captured["system"] = kwargs.get("system", [])
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Jag kan bara hjälpa till med frågor om UNESCO:s världsarv.")]
        return mock_response

    mocker.patch("services.unesco.service.anthropic.Anthropic").return_value.messages.create.side_effect = fake_create

    chat_about_unesco("En fråga utanför UNESCO", [])

    system_text = " ".join(block["text"] for block in captured["system"])
    assert "endast" in system_text.lower() or "bara" in system_text.lower()
