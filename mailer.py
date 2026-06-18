"""mailer.py — Notifications email au secrétariat (détail nominatif). Best-effort."""
import os
import smtplib
import ssl
from email.message import EmailMessage

RECIPIENTS_DEFAUT = "atrcrege@gmail.com,thomas.ducourant@gmail.com"


def _recipients():
    raw = os.environ.get("NOTIF_RECIPIENTS", RECIPIENTS_DEFAUT)
    return [a.strip() for a in raw.split(",") if a.strip()]


def _ligne_tireur(t):
    base = f"{t.get('prenom', '')} {t.get('nom', '')}".strip()
    if t.get("taille_veste"):
        return f"- {base} — veste {t['taille_veste']}"
    if t.get("categorie_age"):
        return f"- {base} — {t['categorie_age']}"
    return f"- {base}"


def construire_message(competition_nom, club_nom, tireurs, arbitres):
    presents = [t for t in tireurs if t.get("present")]
    absents = [t for t in tireurs if not t.get("present")]
    sujet = f"[Confirmation LREGE] {club_nom} — {competition_nom}"
    lignes = [
        f"Le club « {club_nom} » a confirmé sa participation.",
        "",
        f"Compétition : {competition_nom}",
        "",
        f"Tireurs présents ({len(presents)}) :",
    ]
    lignes += [_ligne_tireur(t) for t in presents] or ["- (aucun)"]
    if absents:
        lignes += ["", f"Tireurs absents ({len(absents)}) :"]
        lignes += [f"- {(a.get('prenom', '') + ' ' + a.get('nom', '')).strip()}"
                   for a in absents]
    lignes += ["", f"Arbitres ({len(arbitres)}) :"]
    lignes += [f"- {(a.get('prenom', '') + ' ' + a.get('nom', '')).strip()}"
               f" ({a.get('club', '')}, {a.get('niveau', '')})"
               for a in arbitres] or ["- (aucun)"]
    lignes += ["", "— Plateforme de confirmation LREGE"]
    return sujet, "\n".join(lignes)


def construire_rappel(club_nom, competition_nom, date_limite, jours_restants, lien):
    sujet = f"[Rappel LREGE] Confirmation attendue — {competition_nom}"
    corps = (
        f"Bonjour {club_nom},\n\n"
        f"La participation de votre club à « {competition_nom} » n'est pas encore "
        f"confirmée.\n\n"
        f"Date limite : {date_limite} (J-{jours_restants}).\n"
        f"Confirmez via votre lien : {lien}\n\n"
        f"— Plateforme de confirmation LREGE"
    )
    return sujet, corps


def _envoyer(recipients, sujet, corps):
    resultat = {"sent": False, "dry_run": False, "recipients": recipients,
                "subject": sujet, "error": None}
    host = os.environ.get("SMTP_HOST")
    if not host:
        resultat["dry_run"] = True
        return resultat
    try:
        msg = EmailMessage()
        msg["Subject"] = sujet
        msg["From"] = os.environ.get("SMTP_FROM", "no-reply@crege.fr")
        msg["To"] = ", ".join(recipients)
        msg.set_content(corps)
        port = int(os.environ.get("SMTP_PORT", "587"))
        user = os.environ.get("SMTP_USER")
        pwd = os.environ.get("SMTP_PASSWORD")
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls(context=ssl.create_default_context())
            if user and pwd:
                s.login(user, pwd)
            s.send_message(msg)
        resultat["sent"] = True
    except Exception as e:
        resultat["error"] = str(e)
    return resultat


def notifier_confirmation(competition_nom, club_nom, tireurs, arbitres):
    sujet, corps = construire_message(competition_nom, club_nom, tireurs, arbitres)
    return _envoyer(_recipients(), sujet, corps)


def notifier_rappel_club(club_email, club_nom, competition_nom,
                         date_limite, jours_restants, lien):
    sujet, corps = construire_rappel(club_nom, competition_nom,
                                     date_limite, jours_restants, lien)
    return _envoyer([club_email], sujet, corps)
