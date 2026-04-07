from flask import Flask
from services.unesco.routes import unesco_bp

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")
app.register_blueprint(unesco_bp)

@app.route("/")
def index():
    return "Nordic Digital Solutions - UNESCO World Heritage Service"

if __name__ == "__main__":
    app.run(debug=True)
