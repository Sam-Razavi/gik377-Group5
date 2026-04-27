"""Nordic Digital Solutions – Flask-webbserver.

Ansvarig: Nina Bentmosse

Endpoints:
    GET  /                                   — startsida
    GET  /translate/languages                — lista tillgängliga språk
    POST /translate                          — översätt text
    POST /payment/create                     — skapa prenumeration
    POST /payment/cancel                     — avbryt prenumeration
    GET  /payment/subscription/<id>          — hämta prenumerationsstatus
"""

from dotenv import load_dotenv
load_dotenv()  # Läser .env-filen innan services importeras — måste vara först

from flask import Flask, request, jsonify
from services.translation.service import TranslationService
from services.payment.service import PaymentService

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")

translation_service = TranslationService()
payment_service = PaymentService()


# ---------------------------------------------------------------------------
# Startsida
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return "Nordic Digital Solutions - UNESCO World Heritage Service"


# ---------------------------------------------------------------------------
# Översättning
# ---------------------------------------------------------------------------

@app.route("/translate/languages", methods=["GET"])
def translate_languages():
    """Returnera alla språk användaren kan välja bland."""
    return jsonify(translation_service.supported_languages())


@app.route("/translate", methods=["POST"])
def translate_endpoint():
    """Översätt text till valfritt språk.

    Body (JSON):
        text            : str  — texten som ska översättas
        target_language : str  — ISO-639-1 kod, t.ex. "sv", "ar", "ja" (standard: "en")

    Svar (JSON):
        translated_text   : str
        detected_language : str
    """
    data = request.get_json(force=True)
    text = data.get("text")
    target = data.get("target_language", "en")

    if text is None:
        return jsonify({"error": "Fältet 'text' saknas i förfrågan."}), 400

    try:
        translated = translation_service.translate(text, target_language=target)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    detected = translation_service.detect_language(text)
    return jsonify({"translated_text": translated, "detected_language": detected})


# ---------------------------------------------------------------------------
# Betalning
# ---------------------------------------------------------------------------

@app.route("/payment/create", methods=["POST"])
def payment_create():
    """Skapa en prenumeration.

    Body (JSON):
        user_id : str — användarens ID
        plan_id : str — internt plan-ID i systemet (för Stripe måste det motsvara ett giltigt price_xxx)
        method  : str — "card" (Stripe, standard) eller "invoice"

    Svar (JSON):
        subscription_id : str
        record          : dict
    """
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")
    method = data.get("method", "card")

    if not user_id or not plan_id:
        return jsonify({"error": "Fälten 'user_id' och 'plan_id' krävs."}), 400

    try:
        record = payment_service.create_subscription(user_id, plan_id, method=method)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Betalning kunde inte skapas: {str(e)}"}), 500

    return jsonify({"subscription_id": record["id"], "record": record})


@app.route("/payment/cancel", methods=["POST"])
def payment_cancel():
    """Avbryt en prenumeration.

    Body (JSON):
        subscription_id : str
        method          : str — "card" (standard) eller "invoice"
    """
    data = request.get_json(force=True)
    sub_id = data.get("subscription_id")
    method = data.get("method", "card")

    if not sub_id:
        return jsonify({"error": "Fältet 'subscription_id' saknas."}), 400

    try:
        ok = payment_service.cancel_subscription(sub_id, method=method)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"cancelled": ok})


@app.route("/payment/subscription/<subscription_id>", methods=["GET"])
def payment_get(subscription_id):
    """Hämta status för en prenumeration.

    Query-param:
        method : "card" (standard) eller "invoice"
    """
    method = request.args.get("method", "card")

    try:
        rec = payment_service.get_subscription(subscription_id, method=method)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not rec:
        return jsonify({"error": "Prenumerationen hittades inte."}), 404

    return jsonify(rec)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
