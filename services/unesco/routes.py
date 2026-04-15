# Ansvarig: Sonia Tolouifar
# Modul: UNESCO-data & Karttjänst

from flask import Blueprint, jsonify, request
from services.unesco.service import get_sites_near

unesco_bp = Blueprint("unesco", __name__)


@unesco_bp.route("/api/sites")
def sites():
    """Returnerar världsarvssajter nära Borlänge som JSON.

    Query-parametrar:
      ?radius=150   - radie i km (standard 150)
      ?category=Cultural - filtrera på Cultural, Natural eller Mixed
    """
    radius = request.args.get("radius", 150, type=int)
    category = request.args.get("category", None)

    data = get_sites_near(radius_km=radius)

    if category:
        data = [s for s in data if s.get("category", "").lower() == category.lower()]

    return jsonify(data)
