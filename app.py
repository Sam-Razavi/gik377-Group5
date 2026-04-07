from flask import Flask

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")

@app.route("/")
def index():
    return "Nordic Digital Solutions - UNESCO World Heritage Service"

if __name__ == "__main__":
    app.run(debug=True)
