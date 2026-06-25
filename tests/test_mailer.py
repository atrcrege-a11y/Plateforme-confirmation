"""Tests notifications — dry-run, destinataires, contenu nominatif. Aucun envoi réel."""
import os
import mailer


def _clean_env():
    for k in ("SMTP_HOST", "NOTIF_RECIPIENTS"):
        os.environ.pop(k, None)


TIREURS = [
    {"nom": "Durand", "prenom": "Léa", "present": True, "taille_veste": "M",
     "categorie_age": None},
    {"nom": "Petit", "prenom": "Tom", "present": True, "taille_veste": None,
     "categorie_age": "V1-V2"},
    {"nom": "Absent", "prenom": "Paul", "present": False, "taille_veste": None,
     "categorie_age": None},
]
ARBITRES = [{"nom": "Roy", "prenom": "Max", "club": "Nancy", "niveau": "national"}]


def test_message_detail_nominatif():
    sujet, corps = mailer.construire_message("CDF M15", "Escrime Nancy", TIREURS, ARBITRES)
    assert "Escrime Nancy" in sujet and "CDF M15" in sujet
    assert "Tireurs présents (2)" in corps and "Tireurs absents (1)" in corps
    assert "Léa Durand — veste M" in corps
    assert "Tom Petit — V1-V2" in corps
    assert "Paul Absent" in corps
    assert "Max Roy (Nancy, national)" in corps


def test_dry_run_sans_smtp():
    _clean_env()
    r = mailer.notifier_confirmation("CDF M15", "Nancy", TIREURS, ARBITRES)
    assert r["dry_run"] is True and r["sent"] is False and r["error"] is None
    assert "atrcrege@gmail.com" in r["recipients"]
    assert "thomas.ducourant@gmail.com" in r["recipients"]


def test_destinataires_surchargeables():
    _clean_env()
    os.environ["NOTIF_RECIPIENTS"] = "administration@crege.fr"
    try:
        r = mailer.notifier_confirmation("X", "Y", TIREURS, [])
        assert r["recipients"] == ["administration@crege.fr"]
    finally:
        os.environ.pop("NOTIF_RECIPIENTS", None)


def test_message_html_visuel():
    # Reproduit le détail club du dashboard : table tireurs + badges.
    tireurs = [
        {"nom": "Durand", "prenom": "Léa", "present": True, "taille_veste": "M",
         "categorie_age": None, "equipe": None, "section": "Hommes — Qualifiés"},
        {"nom": "Absent", "prenom": "Paul", "present": False, "taille_veste": None,
         "categorie_age": None, "equipe": None, "section": "Dames — Remplaçants"},
    ]
    html = mailer.construire_message_html("CDF M15", "Escrime Nancy", tireurs, ARBITRES)
    # En-tête
    assert "Escrime Nancy" in html and "CDF M15" in html
    assert "Confirmé" in html
    assert "1/2" in html  # 1 présent / 2 tireurs
    # Colonnes du tableau (mêmes intitulés que le dashboard)
    for col in ("Tireur", "Équipe / section", "Présence", "Veste"):
        assert col in html
    # Lignes tireurs : nom, section, présence, veste
    assert "Durand Léa" in html and "Hommes — Qualifiés" in html
    assert "Absent Paul" in html and "Dames — Remplaçants" in html
    assert "Présent" in html and "Absent" in html
    # Badges colorés (vert présent / rouge absent), comme le dashboard
    assert "#2f7d4f" in html and "#b3261e" in html
    # Arbitre nominatif
    assert "Max Roy" in html


def test_notif_confirmation_envoie_html(monkeypatch):
    # notifier_confirmation doit passer une version HTML à _envoyer.
    captures = {}

    def fake_envoyer(recipients, sujet, corps, html=None):
        captures["html"] = html
        captures["corps"] = corps
        return {"sent": True, "dry_run": False, "recipients": recipients,
                "subject": sujet, "error": None}

    monkeypatch.setattr(mailer, "_envoyer", fake_envoyer)
    mailer.notifier_confirmation("CDF M15", "Escrime Nancy", TIREURS, ARBITRES)
    assert captures["html"] and "<table" in captures["html"]
    assert "Escrime Nancy" in captures["html"]
    assert captures["corps"]  # version texte conservée
