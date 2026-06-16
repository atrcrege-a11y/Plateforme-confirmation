"""
rappels.py — Relances automatiques des clubs non confirmés (3.2).

Pour chaque confirmation restée `en_attente`, on relance le club quand la
date_limite tombe exactement à J-10, J-7 ou J-3. À lancer une fois par jour
(cron) :

    python rappels.py                 # envoie selon la date du jour
    BASE_URL=https://... python rappels.py

L'email part vers l'adresse du club et contient son lien magique /c/<token>.
Envoi best-effort (mailer) : une panne SMTP n'interrompt pas la boucle.
"""
import datetime
import os

from db import get_connection
from mailer import notifier_rappel_club

# Jours avant date_limite déclenchant une relance.
JOURS_RAPPEL = (10, 7, 3)


def base_url():
    return os.environ.get("BASE_URL", "http://127.0.0.1:5002").rstrip("/")


def _parse_date(s):
    try:
        return datetime.date.fromisoformat((s or "").strip())
    except ValueError:
        return None


def clubs_a_relancer(conn, today, jours=JOURS_RAPPEL):
    """Confirmations en attente dont date_limite tombe à J-{jours}.

    Retourne une liste de dicts : token, club_nom, club_email, competition_nom,
    date_limite, jours_restants.
    """
    rows = conn.execute(
        "SELECT cf.token, cl.nom AS club_nom, cl.email AS club_email, "
        "       co.nom AS competition_nom, co.date_limite "
        "FROM confirmation cf "
        "JOIN club cl ON cl.id = cf.club_id "
        "JOIN competition co ON co.id = cf.competition_id "
        "WHERE cf.statut = 'en_attente'"
    ).fetchall()

    cibles = []
    for r in rows:
        limite = _parse_date(r["date_limite"])
        if limite is None:
            continue
        restants = (limite - today).days
        if restants in jours:
            cibles.append({
                "token": r["token"],
                "club_nom": r["club_nom"],
                "club_email": r["club_email"],
                "competition_nom": r["competition_nom"],
                "date_limite": r["date_limite"],
                "jours_restants": restants,
            })
    return cibles


def envoyer_rappels(conn, today=None, url=None):
    """Envoie les relances du jour. Retourne la liste des résultats par cible."""
    today = today or datetime.date.today()
    url = (url or base_url()).rstrip("/")
    resultats = []
    for c in clubs_a_relancer(conn, today):
        lien = f"{url}/c/{c['token']}"
        notif = notifier_rappel_club(
            c["club_email"], c["club_nom"], c["competition_nom"],
            c["date_limite"], c["jours_restants"], lien)
        resultats.append({**c, "lien": lien,
                          "sent": notif["sent"], "dry_run": notif["dry_run"],
                          "error": notif["error"]})
    return resultats


def run():
    """Point d'entrée CLI / cron : envoie les relances du jour et journalise."""
    conn = get_connection()
    try:
        res = envoyer_rappels(conn)
    finally:
        conn.close()
    stamp = datetime.date.today().isoformat()
    if not res:
        print(f"[{stamp}] Aucune relance à envoyer aujourd'hui.")
    for r in res:
        etat = "DRY-RUN" if r["dry_run"] else ("ENVOYÉ" if r["sent"] else f"ERREUR ({r['error']})")
        print(f"[{stamp}] [{etat}] J-{r['jours_restants']} {r['club_nom']:<30} {r['competition_nom']}")
    return res


if __name__ == "__main__":
    run()
