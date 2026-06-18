"""
mailer.py — Notifications email au secrétariat (2.7).

Envoi best-effort : une panne SMTP ne doit JAMAIS faire échouer une
confirmation de club. Si SMTP n'est pas configuré (SMTP_HOST absent), on bascule
en mode dry-run (rien n'est envoyé, le message est retourné pour log/inspection).

Configuration par variables d'environnement :
  SMTP_HOST, SMTP_PORT (def. 587), SMTP_USER, SMTP_PASSWORD, SMTP_FROM
  NOTIF_RECIPIENTS : destinataires séparés par des virgules.

Destinataires par défaut = phase de test. En prod, définir :
  NOTIF_RECIPIENTS="administration@crege.fr"
(réductible à "atrcrege@gmail.com" une fois le dashboard 3.1 en place).
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

# Phase de test (cf. Clément) ; surchargé par NOTIF_RECIPIENTS.
RECIPIENTS_DEFAUT = "atrcrege@gmail.com,thomas.ducourant@gmail.com"


def _recipients():
    raw = os.environ.get("NOTIF_RECIPIENTS", RECIPIENTS_DEFAUT)
    return [a.strip() for a in raw.split(",") if a.strip()]


def _ligne_tireur(t):
    """'Prénom Nom — veste M' / '… — V1-V2' selon les champs renseignés."""
    base = f"{t.get('prenom', '')} {t.get('nom', '')}".strip()
    if t.get("taille_veste"):
        return f"- {base} — veste {t['taille_veste']}"
    if t.get("categorie_age"):
        return f"- {base} — {t['categorie_age']}"
    return f"- {base}"


def construire_message(competition_nom, club_nom, tireurs, arbitres):
    """Construit (sujet, corps) de la notification — détail NOMINATIF.

    tireurs  : liste de dicts {nom, prenom, present, taille_veste, categorie_age}.
    arbitres : liste de dicts {nom, prenom, club, niveau}.
    """
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
    """Construit (sujet, corps) d'un email de relance à un club non confirmé."""
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
    """Envoi SMTP best-effort. Ne lève jamais.

    Retourne {sent, dry_run, recipients, subject, error}. Sans SMTP_HOST :
    mode dry-run (rien n'est envoyé).
    """
    resultat = {"sent": False, "dry_run": False, "recipients": recipients,
                "subject": sujet, "error": None}

    host = os.environ.get("SMTP_HOST")
    if not host:
        resultat["dry_run"] = True  # SMTP non configuré : on n'envoie pas
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
    except Exception as e:  # best-effort : on n'interrompt jamais l'appelant
        resultat["error"] = str(e)
    return resultat


def notifier_confirmation(competition_nom, club_nom, tireurs, arbitres):
    """Notifie le secrétariat (détail nominatif). Best-effort : ne lève jamais.

    tireurs/arbitres : listes de dicts (cf. construire_message).
    Retourne un dict : {sent, dry_run, recipients, subject, error}.
    """
    sujet, corps = construire_message(competition_nom, club_nom, tireurs, arbitres)
    return _envoyer(_recipients(), sujet, corps)


def notifier_rappel_club(club_email, club_nom, competition_nom,
                         date_limite, jours_restants, lien):
    """Relance un club non confirmé (envoi au club). Best-effort : ne lève jamais."""
    sujet, corps = construire_rappel(club_nom, competition_nom,
                                     date_limite, jours_restants, lien)
    return _envoyer([club_email], sujet, corps)
