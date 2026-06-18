"""
routes/confirm.py — Lecture + enregistrement des confirmations (2.2).

Accès par lien magique : /c/<token> identifie le club + la compétition via
confirmation.token. CLOISONNEMENT (règle métier) : un club ne peut écrire que
sur SES propres tireurs (qualifie.club_id == club du token) ; toute tentative
sur un tireur d'un autre club est rejetée (403), côté serveur, sans se fier au
front.
"""
import datetime

from flask import Blueprint, jsonify, request, abort, render_template

from db import get_connection
from arbitrage import calculer_arbitres_requis, NIVEAUX_ARBITRE
from champs import champs_tireur
from mailer import notifier_confirmation

bp = Blueprint("confirm", __name__)


def _row(conn, sql, args=()):
    return conn.execute(sql, args).fetchone()


def _confirmation(conn, token):
    return _row(conn, "SELECT * FROM confirmation WHERE token = ?", (token,))


@bp.route("/c/<token>", methods=["GET"])
def page_confirmation(token):
    """Page web de confirmation (le JS appelle /api/c/<token>)."""
    return render_template("confirmation.html", token=token)


@bp.route("/api/c/<token>", methods=["GET"])
def lire_confirmation(token):
    """Renvoie le périmètre du club : compétition, qualifiés (mine/lecture seule),
    bloc arbitrage, et la saisie déjà enregistrée."""
    conn = get_connection()
    try:
        conf = _confirmation(conn, token)
        if conf is None:
            abort(404, description="Lien invalide ou expiré")

        comp = _row(conn, "SELECT * FROM competition WHERE id = ?", (conf["competition_id"],))
        club = _row(conn, "SELECT * FROM club WHERE id = ?", (conf["club_id"],))

        qualifies = conn.execute(
            "SELECT id, club_id, nom, prenom, section, equipe, rang "
            "FROM qualifie WHERE competition_id = ? ORDER BY equipe, rang",
            (conf["competition_id"],),
        ).fetchall()

        # saisie déjà enregistrée (préremplissage)
        partic = {
            r["qualifie_id"]: dict(r)
            for r in conn.execute(
                "SELECT qualifie_id, present, taille_veste, categorie_age "
                "FROM participation_tireur WHERE confirmation_id = ?",
                (conf["id"],),
            ).fetchall()
        }
        arbitres = [dict(r) for r in conn.execute(
            "SELECT nom, prenom, club, niveau FROM arbitre WHERE confirmation_id = ?",
            (conf["id"],),
        ).fetchall()]

        mine_count = sum(1 for q in qualifies if q["club_id"] == conf["club_id"])
        return jsonify({
            "competition": {
                "id": comp["id"], "nom": comp["nom"], "categorie": comp["categorie"],
                "format": comp["format"], "arme": comp["arme"], "genre": comp["genre"],
                "date": comp["date"], "lieu": comp["lieu"], "date_limite": comp["date_limite"],
                "champs": champs_tireur(comp["categorie"]),
            },
            "club": {"id": club["id"], "nom": club["nom"]},
            "statut": conf["statut"],
            "arbitrage": {
                "arbitres_requis": bool(comp["arbitres_requis"]),
                "type_arbitrage": comp["type_arbitrage"],
                "source": comp["source_arbitres"],
                "arbitres_requis_nombre": calculer_arbitres_requis(
                    mine_count, comp["type_arbitrage"], comp["seuil1"], comp["seuil2"]),
            },
            "qualifies": [{
                "id": q["id"], "nom": q["nom"], "prenom": q["prenom"],
                "section": q["section"], "equipe": q["equipe"], "rang": q["rang"],
                "mine": q["club_id"] == conf["club_id"],
                "saisie": partic.get(q["id"]),
            } for q in qualifies],
            "arbitres": arbitres,
        })
    finally:
        conn.close()


@bp.route("/api/confirm/<token>", methods=["POST"])
def enregistrer_confirmation(token):
    """Enregistre la confirmation du club. Rejette toute écriture hors périmètre."""
    data = request.get_json(silent=True) or {}
    participations = data.get("participations", [])
    arbitres = data.get("arbitres", [])

    conn = get_connection()
    try:
        conf = _confirmation(conn, token)
        if conf is None:
            abort(404, description="Lien invalide ou expiré")
        comp_id, club_id = conf["competition_id"], conf["club_id"]
        comp = _row(conn, "SELECT categorie, nom FROM competition WHERE id = ?", (comp_id,))
        club = _row(conn, "SELECT nom FROM club WHERE id = ?", (club_id,))

        # CLOISONNEMENT : chaque qualifie_id doit appartenir au club du token
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
            hors_perimetre = [i for i in ids if i not in autorises]
            if hors_perimetre:
                abort(403, description=f"Tireur(s) hors de votre périmètre : {hors_perimetre}")

        # Validation des niveaux d'arbitre
        for a in arbitres:
            if a.get("niveau") not in NIVEAUX_ARBITRE:
                abort(400, description=f"Niveau d'arbitre invalide : {a.get('niveau')!r}")
        # Validation des champs requis (veste M15 / catégorie d'âge Vétérans…) pour les présents
        requis = [c["key"] for c in champs_tireur(comp["categorie"]) if c.get("required")]
        for p in participations:
            if p.get("present"):
                for key in requis:
                    if not (p.get(key) or "").strip():
                        abort(400, description=f"Champ '{key}' manquant pour un tireur présent")

        # Réécriture idempotente de la saisie du club
        conn.execute("DELETE FROM participation_tireur WHERE confirmation_id = ?", (conf["id"],))
        conn.execute("DELETE FROM arbitre WHERE confirmation_id = ?", (conf["id"],))
        for p in participations:
            conn.execute(
                "INSERT INTO participation_tireur"
                "(confirmation_id, qualifie_id, present, taille_veste, categorie_age)"
                " VALUES (?,?,?,?,?)",
                (conf["id"], p.get("qualifie_id"),
                 1 if p.get("present") else 0,
                 p.get("taille_veste"), p.get("categorie_age")),
            )
        for a in arbitres:
            conn.execute(
                "INSERT INTO arbitre(confirmation_id, nom, prenom, club, niveau)"
                " VALUES (?,?,?,?,?)",
                (conf["id"], a.get("nom"), a.get("prenom"), a.get("club"), a.get("niveau")),
            )
        conn.execute(
            "UPDATE confirmation SET statut='confirmee', date_confirmation=?, confirme_par_email=?"
            " WHERE id=?",
            (datetime.datetime.now().isoformat(timespec="seconds"),
             data.get("confirme_par_email"), conf["id"]),
        )
        conn.commit()

        # Notification secrétariat — best-effort (n'interrompt jamais la confirmation)
        # Détail nominatif : on relit la saisie + les noms des qualifiés.
        tireurs_detail = [
            {
                "nom": r["nom"], "prenom": r["prenom"], "present": bool(r["present"]),
                "taille_veste": r["taille_veste"], "categorie_age": r["categorie_age"],
            }
            for r in conn.execute(
                "SELECT q.nom, q.prenom, pt.present, pt.taille_veste, pt.categorie_age "
                "FROM participation_tireur pt "
                "LEFT JOIN qualifie q ON q.id = pt.qualifie_id "
                "WHERE pt.confirmation_id = ? ORDER BY q.equipe, q.rang, q.nom",
                (conf["id"],),
            ).fetchall()
        ]
        arbitres_detail = [
            {"nom": a.get("nom"), "prenom": a.get("prenom"),
             "club": a.get("club"), "niveau": a.get("niveau")}
            for a in arbitres
        ]
        notif = notifier_confirmation(comp["nom"], club["nom"], tireurs_detail, arbitres_detail)

        return jsonify({
            "statut": "confirmee",
            "tireurs_enregistres": len(participations),
            "arbitres_enregistres": len(arbitres),
            "notification": {"dry_run": notif["dry_run"], "sent": notif["sent"]},
        }), 201
    finally:
        conn.close()
