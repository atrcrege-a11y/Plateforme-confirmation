"""
routes/dashboard.py — Vue secrétariat (3.1).

Accès réservé à l'admin via token permanent (dashboard.admin_token()). Le
dashboard n'est PAS cloisonné : il agrège toutes les compétitions / clubs.

Endpoints :
  GET /dashboard/<token>                       -> page HTML
  GET /api/dashboard/<token>                   -> agrégat JSON
  GET /api/dashboard/<token>/export/<comp_id>  -> classeur .xlsx (confirmées)
"""
from flask import Blueprint, jsonify, abort, render_template, Response

from db import get_connection
import dashboard as dash

bp = Blueprint("dashboard", __name__)


def _require_admin(token):
    if not dash.is_admin(token):
        abort(404)  # 404 plutôt que 403 : ne pas révéler l'existence du dashboard


@bp.route("/dashboard/<token>", methods=["GET"])
def page_dashboard(token):
    _require_admin(token)
    return render_template("dashboard.html", token=token)


@bp.route("/api/dashboard/<token>", methods=["GET"])
def api_dashboard(token):
    _require_admin(token)
    conn = get_connection()
    try:
        return jsonify({"competitions": dash.agreger(conn)})
    finally:
        conn.close()


@bp.route("/api/dashboard/<token>/export/<int:comp_id>", methods=["GET"])
def export_xlsx(token, comp_id):
    _require_admin(token)
    conn = get_connection()
    try:
        comp = conn.execute(
            "SELECT nom FROM competition WHERE id = ?", (comp_id,)
        ).fetchone()
        if comp is None:
            abort(404, description="Compétition inconnue")
        tireurs, arbitres = dash.participations_export(conn, comp_id)
        contenu = dash.construire_xlsx(comp["nom"], tireurs, arbitres)
    finally:
        conn.close()

    fichier = f"participations_comp{comp_id}.xlsx"
    return Response(
        contenu,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fichier}"'},
    )
