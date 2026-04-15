# Tester för UNESCO-data & Karttjänst
# Ansvarig: Sonia Tolouifar

from services.unesco.service import get_sites, get_sites_near


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
