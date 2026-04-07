# Ansvarig: Sonia Tolouifar
# Modul: UNESCO-data & Karttjänst

from flask import Blueprint, jsonify
from services.unesco.service import get_sites_near

unesco_bp = Blueprint("unesco", __name__)


@unesco_bp.route("/api/sites")
def sites():
    """Returnerar världsarvssajter nära Borlänge som JSON."""
    data = get_sites_near()
    return jsonify(data)
