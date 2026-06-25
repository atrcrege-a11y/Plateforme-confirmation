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


# --- Version HTML : récap visuel par club (reproduit le détail du dashboard) ---

def _esc(s):
    s = "" if s is None else str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _badge(texte, bg, fg):
    return (f'<span style="display:inline-block;font-size:12px;padding:3px 10px;'
            f'border-radius:8px;background:{bg};color:{fg}">{texte}</span>')


def construire_message_html(competition_nom, club_nom, tireurs, arbitres):
    OK_BG, OK = "#e9f5ee", "#2f7d4f"
    KO_BG, KO = "#f6e4e3", "#b3261e"
    TXT, MUT, BORD = "#1f2328", "#5f6b76", "#e0ddd5"
    presents = [t for t in tireurs if t.get("present")]
    TH = (f"text-align:left;padding:6px 8px;color:{MUT};"
          f"font-weight:600;font-size:12px")
    TD = f"padding:6px 8px;border-top:1px solid {BORD};font-size:14px"

    lignes = []
    for t in tireurs:
        nom = f"{_esc(t.get('nom', ''))} {_esc(t.get('prenom', ''))}".strip()
        sec = _esc(t.get("equipe") or t.get("section") or "—")
        pres = (_badge("Présent", OK_BG, OK) if t.get("present")
                else _badge("Absent", KO_BG, KO))
        veste = _esc(t.get("taille_veste") or "—")
        lignes.append(
            f'<tr><td style="{TD}">{nom}</td>'
            f'<td style="{TD};color:{MUT}">{sec}</td>'
            f'<td style="{TD}">{pres}</td>'
            f'<td style="{TD}">{veste}</td></tr>')

    table = (
        f'<table style="width:100%;border-collapse:collapse;margin-top:10px">'
        f'<thead><tr><th style="{TH}">Tireur</th>'
        f'<th style="{TH}">Équipe / section</th>'
        f'<th style="{TH}">Présence</th>'
        f'<th style="{TH}">Veste</th></tr></thead>'
        f'<tbody>{"".join(lignes)}</tbody></table>')

    arb = ""
    if arbitres:
        items = "".join(
            f'<li>{_esc(a.get("prenom", ""))} {_esc(a.get("nom", ""))} '
            f'({_esc(a.get("club", ""))}, {_esc(a.get("niveau", ""))})</li>'
            for a in arbitres)
        arb = (f'<p style="margin:12px 0 4px;font-weight:600;font-size:13px;color:{TXT}">'
               f'Arbitres ({len(arbitres)})</p>'
               f'<ul style="margin:0;padding-left:18px;font-size:13px;color:{TXT}">'
               f'{items}</ul>')

    return (
        f'<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
        f'color:{TXT};background:#f4f4f2;padding:16px">'
        f'<div style="max-width:640px;margin:0 auto;border:1px solid {BORD};'
        f'border-radius:12px;padding:16px 20px;background:#fff">'
        f'<h2 style="font-size:17px;font-weight:600;margin:0 0 2px">'
        f'{_esc(club_nom)} &nbsp; {_badge("Confirmé", OK_BG, OK)}</h2>'
        f'<p style="margin:2px 0 0;color:{MUT};font-size:13px">{_esc(competition_nom)}</p>'
        f'<p style="margin:6px 0 0;color:{MUT};font-size:13px">'
        f'<b style="color:{TXT}">{len(presents)}/{len(tireurs)}</b> présents'
        f' · <b style="color:{TXT}">{len(arbitres)}</b> arbitre(s)</p>'
        f'{table}{arb}'
        f'<p style="margin:14px 0 0;color:{MUT};font-size:12px">'
        f'— Plateforme de confirmation LREGE</p>'
        f'</div></div>')


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


def _envoyer(recipients, sujet, corps, html=None):
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
        if html:
            msg.add_alternative(html, subtype="html")
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
    html = construire_message_html(competition_nom, club_nom, tireurs, arbitres)
    return _envoyer(_recipients(), sujet, corps, html)


def notifier_rappel_club(club_email, club_nom, competition_nom,
                         date_limite, jours_restants, lien):
    sujet, corps = construire_rappel(club_nom, competition_nom,
                                     date_limite, jours_restants, lien)
    return _envoyer([club_email], sujet, corps)
