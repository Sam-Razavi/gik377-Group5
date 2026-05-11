# Standalone Flask server - use FastAPI routes.py for the main app.
"""
=============================================================
  BETALNINGSSERVER  —  services/payment/app.py
  Ansvarig: Nina Bentmosse
=============================================================

Vad gör den här filen?
-----------------------
Flask-server för betalningar. Körs på port 5002.
Hanterar all kommunikation med Stripe — kortbetalningar,
prenumerationer och checkout.

Flöde:
-------
1. Frontend anropar  GET  /payment/config
   → Får publishable key och initierar Stripe.js

2. Frontend anropar  POST /payment/intent  med price_id och email
   → Backend skapar en Stripe-prenumeration och returnerar client_secret

3. Frontend anropar  stripe.confirmCardPayment(client_secret, { card })
   → Stripe hanterar kortverifiering direkt i webbläsaren

4. Stripe skickar användaren till /betalning/lyckades eller /betalning/avbruten

Endpoints:
-----------
  GET  /                          → Visar index.html (betalningsgränssnitt)
  GET  /betalning/lyckades        → Bekräftelsesida efter lyckad betalning
  GET  /betalning/avbruten        → Sida om användaren avbröt
  GET  /payment/config            → Returnerar Stripe publishable key
  POST /payment/intent            → Skapar PaymentIntent, returnerar client_secret
  POST /payment/checkout          → Skapar Stripe Checkout Session med betalningslänk
  POST /payment/create            → Skapar prenumeration (card eller invoice)
  GET  /payment/subscription/<id> → Hämtar status för en prenumeration
  POST /payment/cancel            → Avbryter en prenumeration

Krav:
------
  pip install flask flask-cors stripe python-dotenv
  .env med: STRIPE_PUBLISHABLE_KEY och STRIPE_SECRET_KEY

Starta servern:
----------------
  cd services/payment
  python3 app.py
=============================================================
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os, sys
from dotenv import load_dotenv

# Sökväg till den här filen och mappen ovanför (services/)
HERE   = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)

# Lägg till services/ i Python-sökvägen så vi kan importera payment
sys.path.insert(0, PARENT)

# Läs in miljövariabler från .env-filen i samma mapp som app.py
load_dotenv(os.path.join(HERE, ".env"))

# Importera betaltjänsten — hanterar all logik mot Stripe
from payment.service import PaymentService

# Skapa Flask-appen och tillåt anrop från andra portar (CORS)
app = Flask(__name__)
CORS(app)

# Starta betaltjänsten en gång vid uppstart
payment_service = PaymentService()


# ── Sidor ──────────────────────────────────────────────────────────────────

# Startsidan — visar betalningsgränssnittet (index.html)
@app.route("/")
def index():
    return send_file(os.path.join(HERE, "index.html"))


# Visas när betalningen gick igenom — Stripe skickar hit efter lyckad betalning
@app.route("/betalning/lyckades")
def betalning_lyckades():
    return """<!DOCTYPE html>
<html lang="sv"><head><meta charset="utf-8"><title>Betalning klar</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#f0f4f8;display:flex;
       align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:#fff;border-radius:16px;padding:48px 40px;text-align:center;
       box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:400px}
  h1{color:#276749;font-size:1.4rem;margin:16px 0 8px}
  p{color:#718096;font-size:14px;margin-bottom:24px}
  a{display:inline-block;padding:12px 28px;background:#1d3571;color:#fff;
    border-radius:8px;text-decoration:none;font-weight:600}
</style></head><body>
<div class="box">
  <div style="font-size:52px"></div>
  <h1>Tack! Betalningen lyckades.</h1>
  <p>Du har nu tillgång till tjänsten.</p>
  <a href="/">Gå tillbaka</a>
</div></body></html>"""


# Visas när användaren avbröt betalningen — Stripe skickar hit om användaren tryckte "avbryt"
@app.route("/betalning/avbruten")
def betalning_avbruten():
    return """<!DOCTYPE html>
<html lang="sv"><head><meta charset="utf-8"><title>Avbruten</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#f0f4f8;display:flex;
       align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:#fff;border-radius:16px;padding:48px 40px;text-align:center;
       box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:400px}
  h1{color:#744210;font-size:1.4rem;margin:16px 0 8px}
  p{color:#718096;font-size:14px;margin-bottom:24px}
  a{display:inline-block;padding:12px 28px;background:#1d3571;color:#fff;
    border-radius:8px;text-decoration:none;font-weight:600}
</style></head><body>
<div class="box">
  <div style="font-size:52px">↩</div>
  <h1>Betalningen avbröts.</h1>
  <p>Inga pengar har dragits.</p>
  <a href="/">Försök igen</a>
</div></body></html>"""


# ── API ────────────────────────────────────────────────────────────────────

# Returnerar Stripe publishable key till frontend — frontend behöver den för att visa kortformulär
@app.route("/payment/config")
def payment_config():
    pub = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    if not pub:
        return jsonify({"error": "STRIPE_PUBLISHABLE_KEY saknas i .env"}), 500
    return jsonify({"publishable_key": pub})


# Skapar en Stripe PaymentIntent — returnerar client_secret som frontend använder för kortbetalning
@app.route("/payment/intent", methods=["POST"])
def payment_intent():
    data     = request.get_json(force=True)
    price_id = data.get("price_id", "")
    email    = data.get("email", "")
    if not price_id:
        return jsonify({"error": "price_id saknas"}), 400
    try:
        result = payment_service.create_payment_intent(price_id, email)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(result)


# Skapar en Stripe Checkout Session — returnerar en URL dit användaren skickas för att betala
@app.route("/payment/checkout", methods=["POST"])
def payment_checkout():
    data     = request.get_json(force=True)
    price_id = data.get("price_id", "")
    success  = data.get("success_url", "http://localhost:5002/betalning/lyckades")
    cancel   = data.get("cancel_url",  "http://localhost:5002/betalning/avbruten")
    if not price_id:
        return jsonify({"error": "price_id saknas"}), 400
    try:
        session = payment_service.create_checkout_session(price_id, success, cancel)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(session)


# Skapar en prenumeration direkt — stöder betalmetod "card" (Stripe) eller "invoice" (faktura)
@app.route("/payment/create", methods=["POST"])
def payment_create():
    data    = request.get_json(force=True)
    user_id = data.get("user_id", "")
    plan_id = data.get("plan_id", "")
    method  = data.get("method", "card")
    if not user_id or not plan_id:
        return jsonify({"error": "user_id och plan_id krävs"}), 400
    try:
        record = payment_service.create_subscription(user_id, plan_id, method=method)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"subscription_id": record["id"], "record": record})


# Hämtar aktuell status för en prenumeration med hjälp av dess ID
@app.route("/payment/subscription/<sub_id>")
def payment_get(sub_id):
    method = request.args.get("method", "card")
    try:
        rec = payment_service.get_subscription(sub_id, method=method)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if not rec:
        return jsonify({"error": "Hittades inte"}), 404
    return jsonify(rec)


# Avbryter en prenumeration — sätter status till "cancelled" i Stripe
@app.route("/payment/cancel", methods=["POST"])
def payment_cancel():
    data   = request.get_json(force=True)
    sub_id = data.get("subscription_id", "")
    method = data.get("method", "card")
    if not sub_id:
        return jsonify({"error": "subscription_id saknas"}), 400
    try:
        ok = payment_service.cancel_subscription(sub_id, method=method)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"cancelled": ok})


# Starta servern på port 5002 när filen körs direkt
if __name__ == "__main__":
    app.run(debug=True, port=5002)
