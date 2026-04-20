# Ansvarig: Sonia Tolouifar
# Modul: UNESCO-data & Karttjänst

from typing import Optional
from fastapi import APIRouter
from services.unesco.service import get_sites_near, BORLANGE_LAT, BORLANGE_LON

router = APIRouter(prefix="/unesco", tags=["unesco"])


@router.get("/sites")
def sites(
    radius: int = 150,
    category: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
):
    """Returnerar världsarvssajter nära en given position som JSON.

    Query-parametrar:
      ?radius=150         - radie i km (standard 150)
      ?category=Cultural  - filtrera på Cultural, Natural eller Mixed
      ?lat=60.4858        - latitud (standard: Borlänge)
      ?lon=15.4358        - longitud (standard: Borlänge)
    """
    user_lat = lat if lat is not None else BORLANGE_LAT
    user_lon = lon if lon is not None else BORLANGE_LON

    data = get_sites_near(lat=user_lat, lon=user_lon, radius_km=radius)

    if category:
        data = [s for s in data if s.get("category", "").lower() == category.lower()]

    return data
