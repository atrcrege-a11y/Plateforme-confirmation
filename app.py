"""app.py — Fabrique Flask de la plateforme de confirmation.

Auth par session (cookie). SECRET_KEY via env (obligatoire en prod).
"""
import os

from flask import Flask, jsonify, redirect, url_for

from routes.confirm import bp as bp_confirm
from routes.dashboard import bp as bp_dashboard
from routes.auth import bp as bp_auth
from routes.import_api import bp as bp_import


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # En prod HTTPS (PythonAnywhere) : cookie envoyé seulement en HTTPS.
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    )

    @app.route("/")
    def accueil():
        return redirect(url_for("dashboard.page_dashboard"))

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "confirmation-lrege"})

    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_confirm)
    app.register_blueprint(bp_dashboard)
    app.register_blueprint(bp_import)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=True)
