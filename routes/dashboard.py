"""routes/dashboard.py — Vue secrétariat (3.1), protégée par session.

Accès humain : connexion (auth.login_requis / api_auth). Rôles admin et
secrétariat voient le dashboard et l'export. Le déclencheur cron garde son
token (appel machine, pas d'humain).
"""
from flask import Blueprint, jsonify, abort, render_template, Response

from db import get_connection
import dashboard as dash
import auth

bp = Blueprint("dashboard", __name__)

VUE = ("admin", "secretariat")  # rôles autorisés à consulter le dashboard


@bp.route("/dashboard", methods=["GET"])
@auth.login_requis
def page_dashboard():
    return render_template("dashboard.html", user=auth.utilisateur_courant())


@bp.route("/api/dashboard", methods=["GET"])
@auth.api_auth(*VUE)
def api_dashboard():
    conn = get_connection()
    try:
        return jsonify({"competitions": dash.agreger(conn)})
    finally:
        conn.close()


@bp.route("/api/dashboard/export/<int:comp_id>", methods=["GET"])
@auth.api_auth(*VUE)
def export_xlsx(comp_id):
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


@bp.route("/cron/rappels/<token>", methods=["GET"])
def cron_rappels(token):
    """Déclencheur HTTP des rappels (cron externe). Protégé par le token admin."""
    if not dash.is_admin(token):
        abort(404)
    from rappels import envoyer_rappels
    conn = get_connection()
    try:
        res = envoyer_rappels(conn)
    finally:
        conn.close()
    return jsonify({
        "envois": len(res),
        "details": [
            {"club": r["club_nom"], "competition": r["competition_nom"],
             "jours_restants": r["jours_restants"], "sent": r["sent"],
             "dry_run": r["dry_run"], "error": r["error"]}
            for r in res
        ],
    })
