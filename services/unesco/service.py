# Ansvarig: Sonia Tolouifar
# Modul: UNESCO-data & Karttjänst
# Hämtar världsarvsdata från UNESCO API och hanterar kartfunktionalitet

import os
import time

import anthropic
import requests
from math import radians, sin, cos, sqrt, atan2

BASE_URL = "https://data.unesco.org/api/explore/v2.1/catalog/datasets/whc001/records"

BORLANGE_LAT = 60.4858
BORLANGE_LON = 15.4358
DEFAULT_RADIUS_KM = 150
CACHE_TTL_SECONDS = 3600

_sites_cache = {"data": [], "fetched_at": 0}


def get_sites(limit=100, offset=0):
    """Hämtar världsarvssajter från UNESCO API."""
    params = {
        "limit": limit,
        "offset": offset,
        "select": "name_en,short_description_en,category,states_names,region,coordinates,date_inscribed,main_image_url,id_no"
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json().get("results", [])


def _haversine_km(lat1, lon1, lat2, lon2):
    """Beräknar avstånd i km mellan två koordinater."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _get_all_sites_cached():
    if time.time() - _sites_cache["fetched_at"] < CACHE_TTL_SECONDS:
        return _sites_cache["data"]

    sites = []
    offset = 0
    while True:
        batch = get_sites(limit=100, offset=offset)
        if not batch:
            break
        sites.extend(batch)
        offset += 100
        if len(batch) < 100:
            break

    _sites_cache["data"] = sites
    _sites_cache["fetched_at"] = time.time()
    return sites


def get_sites_near(lat=BORLANGE_LAT, lon=BORLANGE_LON, radius_km=DEFAULT_RADIUS_KM):
    """Returnerar världsarvssajter inom en given radie (km) från en koordinat."""
    all_sites = _get_all_sites_cached()

    nearby = []
    for site in all_sites:
        coords = site.get("coordinates")
        if not coords:
            continue
        dist = _haversine_km(lat, lon, coords["lat"], coords["lon"])
        if dist <= radius_km:
            site["distance_km"] = round(dist, 1)
            nearby.append(site)

    nearby.sort(key=lambda s: s["distance_km"])
    return nearby


def chat_about_unesco(message: str, sites: list) -> str:
    """Svarar på frågor om världsarv med hjälp av Claude AI.

    Använder prompt caching för att slippa skicka platsdata varje gång.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "AI-tjansten ar inte tillganglig. "
            "Kontakta administratoren for att konfigurera ANTHROPIC_API_KEY."
        )

    client = anthropic.Anthropic(api_key=api_key)

    sites_text = "\n".join(
        f"- {s.get('name_en', 'Okänt namn')} ({s.get('category', '?')}), "
        f"{s.get('states_names', '')}, "
        f"{round(s.get('distance_km', 0), 1)} km bort. "
        f"{s.get('short_description_en', '')}"
        for s in sites[:20]
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": (
                    "Du är en hjälpsam guide om UNESCO:s världsarv. "
                    "Du svarar ENDAST på frågor som handlar om UNESCO, världsarv, kulturarv, naturarv eller specifika världsarvssajter. "
                    "Om användaren frågar om något annat ämne svarar du: "
                    "'Jag kan bara hjälpa till med frågor om UNESCO:s världsarv.' "
                    "Svara alltid på samma språk som användaren skriver på. "
                    "Håll svaren kortfattade och informativa."
                ),
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": f"Här är de närmaste världsarven:\n{sites_text}",
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": message}],
    )

    return response.content[0].text
