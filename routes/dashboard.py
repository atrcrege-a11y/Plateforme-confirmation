"""routes/dashboard.py — Vue secrétariat (3.1), protégée par session.

Accès humain : connexion (auth.login_requis / api_auth). Rôles admin et
secrétariat voient le dashboard et l'export. Le déclencheur cron garde son
token (appel machine, pas d'humain).
"""
import datetime

from flask import Blueprint, jsonify, abort, render_template, Response, request

from db import get_connection
from champs import champs_tireur
from arbitrage import NIVEAUX_ARBITRE
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


@bp.route("/api/dashboard/corriger/<int:confirmation_id>", methods=["POST"])
@auth.api_auth(*VUE)
def corriger_confirmation(confirmation_id):
    """Correction manuelle d'un club par le secrétariat (outrepasse le lien magique).

    Trace `corrige_par`/`date_correction` SANS toucher `confirme_par_email`
    (distinct d'une confirmation spontanee du club).
    """
    data = request.get_json(silent=True) or {}
    participations = data.get("participations", [])
    arbitres = data.get("arbitres", [])
    user = auth.utilisateur_courant()
    conn = get_connection()
    try:
        conf = conn.execute(
            "SELECT * FROM confirmation WHERE id = ?", (confirmation_id,)
        ).fetchone()
        if conf is None:
            abort(404, description="Confirmation inconnue")
        comp_id, club_id = conf["competition_id"], conf["club_id"]
        comp = conn.execute(
            "SELECT categorie FROM competition WHERE id = ?", (comp_id,)
        ).fetchone()

        ids = [p.get("qualifie_id") for p in participations]
        if ids:
            placeholders = ",".join("?" * len(ids))
            autorises = {
                r["id"] for r in conn.execute(
                    f"SELECT id FROM qualifie WHERE id IN ({placeholders}) "
                    f"AND competition_id = ? AND club_id = ?",
                    (*ids, comp_id, club_id),
                ).fetchall()
            }
            hors = [i for i in ids if i not in autorises]
            if hors:
                abort(403, description=f"Tireur(s) hors de ce club : {hors}")

        for a in arbitres:
            if a.get("niveau") not in NIVEAUX_ARBITRE:
                abort(400, description=f"Niveau d'arbitre invalide : {a.get('niveau')!r}")
        requis = [c["key"] for c in champs_tireur(comp["categorie"]) if c.get("required")]
        for p in participations:
            if p.get("present"):
                for key in requis:
                    if not (p.get(key) or "").strip():
                        abort(400, description=f"Champ '{key}' manquant pour un tireur present")

        conn.execute("DELETE FROM participation_tireur WHERE confirmation_id = ?", (confirmation_id,))
        conn.execute("DELETE FROM arbitre WHERE confirmation_id = ?", (confirmation_id,))
        for p in participations:
            conn.execute(
                "INSERT INTO participation_tireur"
                "(confirmation_id, qualifie_id, present, taille_veste, categorie_age)"
                " VALUES (?,?,?,?,?)",
                (confirmation_id, p.get("qualifie_id"),
                 1 if p.get("present") else 0,
                 p.get("taille_veste"), p.get("categorie_age")),
            )
        for a in arbitres:
            conn.execute(
                "INSERT INTO arbitre(confirmation_id, nom, prenom, club, niveau)"
                " VALUES (?,?,?,?,?)",
                (confirmation_id, a.get("nom"), a.get("prenom"), a.get("club"), a.get("niveau")),
            )
        conn.execute(
            "UPDATE confirmation SET statut='confirmee', corrige_par=?, date_correction=?"
            " WHERE id=?",
            (user["email"], datetime.datetime.now().isoformat(timespec="seconds"),
             confirmation_id),
        )
        conn.commit()
        return jsonify({
            "statut": "confirmee",
            "corrige_par": user["email"],
            "tireurs_enregistres": len(participations),
            "arbitres_enregistres": len(arbitres),
        }), 200
    finally:
        conn.close()


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
