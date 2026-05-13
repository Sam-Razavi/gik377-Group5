# Ansvarig: Sonia Tolouifar
# Modul: UNESCO-data & Karttjänst

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from services.unesco.service import get_sites_near, chat_about_unesco, BORLANGE_LAT, BORLANGE_LON

router = APIRouter(prefix="/unesco", tags=["unesco"])
_bearer = HTTPBearer(auto_error=False)


class ChatRequest(BaseModel):
    message: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius: int = 150
    page_lang: str = "sv"


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


@router.post("/chat")
def chat(req: ChatRequest, credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    """AI-chatt om världsarv nära användarens position. Kräver inloggning.

    Body:
      { "message": "Vilka världsarv finns nära mig?", "lat": 60.4858, "lon": 15.4358, "radius": 150, "page_lang": "sv" }
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Inloggning krävs för att använda AI-chatten.")

    user_lat = req.lat if req.lat is not None else BORLANGE_LAT
    user_lon = req.lon if req.lon is not None else BORLANGE_LON

    sites = get_sites_near(lat=user_lat, lon=user_lon, radius_km=req.radius)
    answer = chat_about_unesco(req.message, sites, page_lang=req.page_lang)

    return {"answer": answer, "sites_used": len(sites)}
