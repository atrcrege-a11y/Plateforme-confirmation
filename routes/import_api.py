"""routes/import_api.py — Réception machine d'une palette SelecGE (POST /api/import).

Appel machine (SelecGE), pas d'humain : protégé par le token admin, comme
/cron/rappels/<token>. Réutilise dashboard.is_admin (env ADMIN_TOKEN).
"""
from flask import Blueprint, jsonify, request, abort

from db import get_connection
import dashboard as dash
from import_selecge import importer

bp = Blueprint("import_api", __name__)


@bp.route("/api/import/<token>", methods=["POST"])
def api_import(token):
    if not dash.is_admin(token):
        abort(404)
    payload = request.get_json(silent=True)
    if payload is None:
        abort(400, description="Corps JSON manquant ou invalide")
    conn = get_connection()
    try:
        try:
            resume = importer(conn, payload)
        except ValueError as e:
            conn.rollback()
            abort(400, description=str(e))
        conn.commit()
        return jsonify(resume), 201
    finally:
        conn.close()


@bp.route("/api/suivi/<token>", methods=["GET"])
def api_suivi(token):
    """Lecture machine du suivi (pour SuiviGE). Même token que /api/import."""
    if not dash.is_admin(token):
        abort(404)
    conn = get_connection()
    try:
        return jsonify({"competitions": dash.agreger(conn)})
    finally:
        conn.close()
