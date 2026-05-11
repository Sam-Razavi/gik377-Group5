"""
=============================================================
  ÖVERSÄTTNINGSSERVER  —  services/translation/app.py
  Ansvarig: Nina Bentmosse
=============================================================

Vad gör den här filen?
-----------------------
Flask-server för översättning. Körs på port 5001.
Tar emot text från frontend, skickar den till Google Cloud
Translate och returnerar översatt text samt identifierat källspråk.

Flöde:
-------
1. Frontend anropar  GET  /translate/languages
   → Får lista på alla tillgängliga språk (används i dropdown)

2. Användaren skriver text och väljer målspråk

3. Frontend anropar  POST /translate  med text och target_language
   → Backend översätter via Google Cloud Translate
   → Returnerar översatt text och identifierat källspråk

Endpoints:
-----------
  GET  /                      → Visar index.html (översättningsgränssnitt)
  GET  /nyheter               → Visar nyheter.html (nyhetssidan)
  GET  /translate/languages   → Lista på alla stödda språk
  POST /translate             → Översätt text, returnerar översättning + källspråk
  GET  /betalning/lyckades    → Bekräftelsesida efter lyckad betalning
  GET  /betalning/avbruten    → Sida om användaren avbröt

Krav:
------
  pip install flask flask-cors python-dotenv google-cloud-translate
  credentials/client_secret.json för Google Translate

Starta servern:
----------------
  cd services/translation
  python3 app.py
=============================================================
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import os, sys

# Sökväg till den här filen och mappen ovanför (services/)
HERE   = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)

# Lägg till services/ i Python-sökvägen så vi kan importera translation och payment
sys.path.insert(0, PARENT)

# Läs in miljövariabler från .env-filen i samma mapp som app.py
load_dotenv(os.path.join(HERE, ".env"))

# Om Google-credentials finns, sätt miljövariabeln automatiskt
_creds = os.path.join(HERE, "credentials", "client_secret.json")
if os.path.exists(_creds):
    os.environ["GOOGLE_CLIENT_SECRET_FILE"] = _creds

# Importera tjänsterna — translation hanterar översättning, payment hanterar Stripe
from translation.service import TranslationService
from payment.service import PaymentService

# Skapa Flask-appen och tillåt anrop från andra portar (CORS)
app = Flask(__name__)
CORS(app)

# Starta tjänsterna en gång vid uppstart
translation_service = TranslationService()
payment_service     = PaymentService()


# ── Sidor ──────────────────────────────────────────────────────────────────

# Startsidan — visar index.html från samma mapp
@app.route("/")
def index():
    return send_file(os.path.join(HERE, "index.html"))


# Nyhetssidan — visar nyheter.html från samma mapp
@app.route("/nyheter")
def nyheter():
    return send_file(os.path.join(HERE, "nyheter.html"))


# ── Översättning ────────────────────────────────────────────────────────────

# Returnerar lista på alla språk som stöds (används av frontend-dropdown)
@app.route("/translate/languages", methods=["GET"])
def languages():
    return jsonify(translation_service.supported_languages())


# Tar emot text och målspråk, returnerar översatt text och identifierat källspråk
@app.route("/translate", methods=["POST"])
def translate():
    data   = request.get_json(force=True)
    text   = data.get("text", "")
    target = data.get("target_language", "en")

    # Kontrollera att text skickades med
    if not text:
        return jsonify({"error": "text saknas"}), 400

    try:
        translated = translation_service.translate(text, target_language=target)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Identifiera vilket språk originaltexten är på
    detected = translation_service.detect_language(text)
    return jsonify({"translated_text": translated, "detected_language": detected})


# ── Betalning ───────────────────────────────────────────────────────────────

# Returnerar Stripe publishable key till frontend — frontend behöver den för att visa kortformulär
@app.route("/payment/config", methods=["GET"])
def payment_config():
    pub_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    if not pub_key:
        return jsonify({"error": "STRIPE_PUBLISHABLE_KEY saknas i .env"}), 500
    return jsonify({"publishable_key": pub_key})


# Skapar en Stripe PaymentIntent — returnerar client_secret som frontend använder för kortbetalning
@app.route("/payment/intent", methods=["POST"])
def payment_intent():
    data     = request.get_json(force=True)
    price_id = data.get("price_id", "price_1TRqWVHYkj0fomnSAd10SVLn")
    email    = data.get("email", "")
    try:
        result = payment_service.create_payment_intent(price_id, email)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(result)


# Skapar en Stripe Checkout Session — returnerar en URL dit användaren skickas för att betala
@app.route("/payment/checkout", methods=["POST"])
def payment_checkout():
    data     = request.get_json(force=True)
    price_id = data.get("price_id", "price_1TRqWVHYkj0fomnSAd10SVLn")
    success  = data.get("success_url", "http://localhost:5001/betalning/lyckades")
    cancel   = data.get("cancel_url",  "http://localhost:5001/betalning/avbruten")
    try:
        session = payment_service.create_checkout_session(price_id, success, cancel)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(session)


# ── Betalningssidor ─────────────────────────────────────────────────────────

# Visas när betalningen gick igenom — Stripe skickar hit efter lyckad betalning
@app.route("/betalning/lyckades")
def betalning_klar():
    return """<!DOCTYPE html>
<html lang="sv"><head><meta charset="utf-8">
<title>Betalning klar</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#f0f4f8;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:#fff;border-radius:16px;padding:48px 40px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.08);max-width:400px}
  .icon{font-size:52px;margin-bottom:16px}
  h1{color:#276749;font-size:1.5rem;margin-bottom:8px}
  p{color:#718096;font-size:14px;margin-bottom:24px}
  a{display:inline-block;padding:12px 28px;background:#1d3571;color:#fff;border-radius:8px;text-decoration:none;font-weight:600}
</style></head><body>
<div class="box">
  <div class="icon">✅</div>
  <h1>Tack! Betalningen lyckades.</h1>
  <p>Du har nu tillgång till tjänsten.</p>
  <a href="/">Gå tillbaka till startsidan</a>
</div>
</body></html>"""


# Visas när användaren avbröt betalningen — Stripe skickar hit om användaren tryckte "avbryt"
@app.route("/betalning/avbruten")
def betalning_avbruten():
    return """<!DOCTYPE html>
<html lang="sv"><head><meta charset="utf-8">
<title>Betalning avbruten</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#f0f4f8;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:#fff;border-radius:16px;padding:48px 40px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.08);max-width:400px}
  .icon{font-size:52px;margin-bottom:16px}
  h1{color:#744210;font-size:1.5rem;margin-bottom:8px}
  p{color:#718096;font-size:14px;margin-bottom:24px}
  a{display:inline-block;padding:12px 28px;background:#1d3571;color:#fff;border-radius:8px;text-decoration:none;font-weight:600}
</style></head><body>
<div class="box">
  <div class="icon">↩️</div>
  <h1>Betalningen avbröts.</h1>
  <p>Inga pengar har dragits.</p>
  <a href="/">Försök igen</a>
</div>
</body></html>"""


# Starta servern på port 5001 när filen körs direkt
if __name__ == "__main__":
    app.run(debug=True, port=5001)
