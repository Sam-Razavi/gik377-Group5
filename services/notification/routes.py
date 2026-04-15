"""
Flask Blueprint med alla endpoints för Notification Service.
Gemensamt API-format så att andra grupper kan använda modulen direkt.
"""

import logging
from flask import Blueprint, request, jsonify
from services.notification.config import ADMIN_TOKEN
from services.notification.service import (
    send_notification,
    subscribe,
    unsubscribe,
    get_subscribers,
    trigger_for_location,
    VALID_TYPES,
)

logger = logging.getLogger("notification")

notification_bp = Blueprint("notification", __name__, url_prefix="/notification")


# ---------- Gemensamt API (krav 1.3) ----------

@notification_bp.route("/send-notification", methods=["POST"])
def send():
    """
    POST /notification/send-notification
    Body:
    {
        "type": "sms" | "email",
        "to": "+4670..." | "user@example.com",
        "message": "...",
        "subject": "...",          (valfritt, för e-post)
        "user_id": "...",          (valfritt, för anti-spam)
        "site_id": "..."           (valfritt, för anti-spam)
    }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "JSON body krävs."}), 400

    notification_type = data.get("type")
    to = data.get("to")
    message = data.get("message")

    if not all([notification_type, to, message]):
        return jsonify({"success": False, "error": "Fälten 'type', 'to' och 'message' krävs."}), 400

    if notification_type not in VALID_TYPES:
        return jsonify({"success": False, "error": "Ogiltig typ. Använd 'sms' eller 'email'."}), 400

    result = send_notification(
        notification_type=notification_type,
        to=to,
        message=message,
        subject=data.get("subject"),
        user_id=data.get("user_id"),
        site_id=data.get("site_id"),
    )

    if result.get("success"):
        status = 200
    elif result.get("error") == "cooldown":
        status = 429
    elif result.get("error") in ("invalid_type", "invalid_recipient"):
        status = 400
    else:
        status = 500

    return jsonify(result), status


# ---------- Trigger via URL (krav 2.1 / 5.2) ----------

@notification_bp.route("/trigger-notification", methods=["GET"])
def trigger():
    """
    GET /notification/trigger-notification?user_id=...&site_id=...&site_name=...&link=...
    """
    user_id = request.args.get("user_id")
    site_id = request.args.get("site_id")
    site_name = request.args.get("site_name", "Okänt världsarv")
    link = request.args.get("link")

    if not user_id or not site_id:
        return jsonify({"success": False, "error": "user_id och site_id krävs."}), 400

    results = trigger_for_location(user_id, site_id, site_name, link)

    # Bestäm statuskod baserat på resultat
    if results and all(r.get("error") == "cooldown" for r in results):
        status = 429
    elif results and results[0].get("error") in (
        "Användaren har ingen prenumeration.",
        "Användaren prenumererar inte på denna plats.",
        "Ingen kontaktinfo registrerad.",
    ):
        status = 404
    else:
        status = 200

    return jsonify({"results": results}), status


# ---------- Prenumeration (krav 2.3) ----------

@notification_bp.route("/subscribe", methods=["POST"])
def subscribe_route():
    """
    POST /notification/subscribe
    Body:
    {
        "user_id": "abc123",
        "phone": "+46701234567",
        "email": "user@example.com",
        "sites": ["site_1", "site_2"]
    }
    """
    data = request.get_json(silent=True)
    if not data or not data.get("user_id"):
        return jsonify({"success": False, "error": "user_id krävs."}), 400

    result = subscribe(
        user_id=data["user_id"],
        phone=data.get("phone"),
        email=data.get("email"),
        sites=data.get("sites"),
    )
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@notification_bp.route("/unsubscribe", methods=["POST"])
def unsubscribe_route():
    """
    POST /notification/unsubscribe
    Body: { "user_id": "abc123", "sites": ["site_1"] }
    """
    data = request.get_json(silent=True)
    if not data or not data.get("user_id"):
        return jsonify({"success": False, "error": "user_id krävs."}), 400

    result = unsubscribe(data["user_id"], data.get("sites"))
    status = 200 if result.get("success") else 404
    return jsonify(result), status


# ---------- Intern/skyddad endpoint ----------

@notification_bp.route("/subscribers", methods=["GET"])
def list_subscribers():
    """Intern endpoint. Kräver Authorization-header med admin-token."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        return jsonify({"success": False, "error": "Otillåten. Ange giltig admin-token."}), 403

    logger.info("Endpoint /subscribers anropad (autentiserad)")
    return jsonify(get_subscribers()), 200


# ---------- Healthcheck ----------

@notification_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "notification"}), 200
