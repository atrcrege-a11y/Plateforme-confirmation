"""
test_envoi_reel.py — Test d'envoi email RÉEL (phase de test, pas un test unitaire).

Envoie vers une adresse cible (par défaut Thomas) :
  1) un RAPPEL de club (flux rappels.py complet, lu depuis une base temporaire)
  2) une NOTIFICATION de confirmation (flux secrétariat)

Base temporaire jetable : ne touche jamais plateforme.db ni les vraies données.

Pré-requis SMTP (sinon mode dry-run = rien n'est envoyé) — Gmail :
    export SMTP_HOST=smtp.gmail.com
    export SMTP_PORT=587
    export SMTP_USER=atrcrege@gmail.com
    export SMTP_PASSWORD="<mot de passe d'application Google, pas le mdp du compte>"
    export SMTP_FROM=atrcrege@gmail.com
    # facultatif : lien cliquable dans le rappel
    export BASE_URL=http://127.0.0.1:5002

Usage :
    python test_envoi_reel.py                          # cible = Thomas
    python test_envoi_reel.py autre@exemple.fr         # cible custom
"""
import datetime
import os
import sys
import tempfile

import migrate
import seed_demo
import mailer
import rappels
from db import get_connection

CIBLE_DEFAUT = "thomas.ducourant@gmail.com"


def main():
    cible = sys.argv[1] if len(sys.argv) > 1 else CIBLE_DEFAUT
    if not os.environ.get("SMTP_HOST"):
        print("⚠️  SMTP_HOST non défini → DRY-RUN (aucun email réel ne partira).")
        print("    Définis les variables SMTP (voir en-tête du fichier) pour envoyer pour de vrai.\n")

    # Base temporaire jetable
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["PLATEFORME_DB"] = path
    migrate.migrate(path)
    conn = get_connection(path)
    seed_demo.seed(conn)

    # Toutes les adresses clubs -> cible : aucun envoi possible vers les emails
    # factices du jeu de démo (pas de rebond).
    today = datetime.date.today()
    limite = (today + datetime.timedelta(days=7)).isoformat()
    conn.execute("UPDATE club SET email = ?", (cible,))
    # Compétition à CLUB UNIQUE (Vétérans, id=2) calée à J-7 : un seul rappel partira.
    conn.execute("UPDATE competition SET date_limite = ? WHERE id = 2", (limite,))
    conn.commit()

    print(f"Cible        : {cible}")
    print(f"Date limite  : {limite} (J-7)\n")

    # 1) Rappel (flux complet rappels.py)
    res = rappels.envoyer_rappels(conn)
    for r in res:
        if r["club_email"] != cible:
            continue
        etat = "DRY-RUN" if r["dry_run"] else ("ENVOYÉ ✓" if r["sent"] else f"ERREUR: {r['error']}")
        print(f"[RAPPEL]       {etat} → {r['club_email']}  ({r['lien']})")

    # 2) Notification de confirmation (flux secrétariat) → forcée vers la cible
    os.environ["NOTIF_RECIPIENTS"] = cible
    n = mailer.notifier_confirmation("Compétition de test", "Club de test (Thomas)", 3, 1)
    etat = "DRY-RUN" if n["dry_run"] else ("ENVOYÉ ✓" if n["sent"] else f"ERREUR: {n['error']}")
    print(f"[NOTIFICATION] {etat} → {', '.join(n['recipients'])}")

    conn.close()
    os.remove(path)
    os.environ.pop("PLATEFORME_DB", None)


if __name__ == "__main__":
    main()
