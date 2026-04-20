"""Nordic Digital Solutions - huvudapp.

Startar Flask-servern och registrerar alla service-moduler (Blueprints).
Varje grupp registrerar sin egen Blueprint här.
"""

from flask import Flask, jsonify

# --- Notification (Riyaaq Ali) ---
from services.notification import notification_bp


app = Flask(__name__)

# Registrera service-Blueprints
app.register_blueprint(notification_bp)

# Övriga grupper registrerar sina Blueprints här, t.ex:
# from services.auth import auth_bp
# app.register_blueprint(auth_bp)
# from services.payment import payment_bp
# app.register_blueprint(payment_bp)


@app.route("/")
def root():
    return jsonify({
        "service": "Nordic Digital Solutions",
        "status": "running",
        "modules": ["notification"],
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
