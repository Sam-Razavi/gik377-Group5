"""Nordic Digital Solutions – huvudapplikation.

Ansvarig: Nina Bentmosse
Modul: Flask-app med endpoints för översättning och betalning

Endpoints:
    POST /translate
    POST /payment/create
    POST /payment/cancel
    GET  /payment/subscription/<subscription_id>
"""

from flask import Flask, request, jsonify

# ---Nina---
# Importera översättningstjänsten och betaltjänsten
from services.translation.service import TranslationService
from services.payment.service import PaymentService
# ---Nina---

# Skapa Flask-applikationen med sökvägar till templates och statiska filer
app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")

# Initieras en gång vid start – återanvänds för alla förfrågningar
translation_service = TranslationService()
payment_service = PaymentService()


# Startsida – bekräftar att appen körs
@app.route("/")
def index():
    return "Nordic Digital Solutions - UNESCO World Heritage Service"


# ---------------------------------------------------------------------------
# Översättning
# ---------------------------------------------------------------------------

@app.route("/translate", methods=["POST"])
def translate_endpoint():
    # Läs JSON-data från förfrågan
    data = request.get_json(force=True)
    text = data.get("text")
    target = data.get("target_language", "en")

    # Kontrollera att text skickats med
    if text is None:
        return jsonify({"error": "missing 'text' in request"}), 400

    try:
        # Översätt texten till valt målspråk
        translated = translation_service.translate(text, target_language=target)
    except ValueError as e:
        # Returnera 400 om målspråket inte är ett av de fem nordiska
        return jsonify({"error": str(e)}), 400

    # Detektera vilket språk ursprungstexten är på
    detected = translation_service.detect_language(text)
    return jsonify({"translated_text": translated, "detected_language": detected})


# ---------------------------------------------------------------------------
# Betalning
# ---------------------------------------------------------------------------

@app.route("/payment/create", methods=["POST"])
def payment_create():
    # Läs JSON-data från förfrågan
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")
    method = data.get("method", "card")  # "card" = Stripe, "swish" = Swish mock

    # Båda fälten krävs för att skapa en prenumeration
    if not user_id or not plan_id:
        return jsonify({"error": "user_id and plan_id required"}), 400

    # Skapa prenumerationen via vald betalningsmetod
    record = payment_service.create_subscription(user_id, plan_id, method=method)
    return jsonify({"subscription_id": record["id"], "record": record})


@app.route("/payment/cancel", methods=["POST"])
def payment_cancel():
    # Läs JSON-data från förfrågan
    data = request.get_json(force=True)
    sub_id = data.get("subscription_id")
    method = data.get("method", "card")  # "card" = Stripe, "swish" = Swish mock

    # Prenumerations-ID krävs för att avbryta
    if not sub_id:
        return jsonify({"error": "subscription_id required"}), 400

    # Avbryt prenumerationen via vald betalningsmetod
    ok = payment_service.cancel_subscription(sub_id, method=method)
    return jsonify({"cancelled": ok})


@app.route("/payment/subscription/<subscription_id>", methods=["GET"])
def payment_get(subscription_id):
    # Läs betalningsmetod från query-parameter, t.ex. ?method=swish
    method = request.args.get("method", "card")

    # Hämta prenumerationsdata
    rec = payment_service.get_subscription(subscription_id, method=method)

    # Returnera 404 om prenumerationen inte hittas
    if not rec:
        return jsonify({"error": "subscription not found"}), 404
    return jsonify(rec)


# Starta Flask-servern i debug-läge vid direktkörning
if __name__ == "__main__":

    app.run(debug=True)
