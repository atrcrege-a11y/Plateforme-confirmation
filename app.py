"""
app.py — Squelette Flask de la plateforme de confirmation (2.1).

Fabrique d'application + enregistrement des blueprints. Les routes métier
(/c/<token>, /api/confirm, /api/dashboard) sont posées en squelette ici et
seront étoffées en 2.2.

Lancer en dev :
    python migrate.py        # crée la base
    python app.py            # http://127.0.0.1:5002
"""
from flask import Flask, jsonify

from routes.confirm import bp as bp_confirm
from routes.dashboard import bp as bp_dashboard


def create_app():
    app = Flask(__name__)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "confirmation-lrege"})

    app.register_blueprint(bp_confirm)
    app.register_blueprint(bp_dashboard)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=True)
