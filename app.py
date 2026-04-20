from flask import Flask, jsonify

from services.notification import notification_bp


app = Flask(__name__)

# Registrera service-Blueprints
app.register_blueprint(notification_bp)


@app.route("/")
def root():
    return jsonify({
        "service": "Nordic Digital Solutions",
        "status": "running",
        "modules": ["notification"],
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
