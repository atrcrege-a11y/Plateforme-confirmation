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


def test_date_fr_format():
    # ISO -> français ; déjà français ou vide inchangés
    assert mailer._date_fr("2026-06-05") == "05/06/2026"
    assert mailer._date_fr("2026-06-05T14:30") == "05/06/2026"
    assert mailer._date_fr("13/06/2026") == "13/06/2026"
    assert mailer._date_fr(None) == ""


def test_date_limite_fr_dans_mails():
    _, corps = mailer.construire_rappel("CE X", "Compét Y", "2026-06-05", 3, "http://l")
    assert "05/06/2026" in corps and "2026-06-05" not in corps
    _, corps2 = mailer.construire_creation_selection(
        {"nom": "X", "date_limite": "2026-06-05"}, {"clubs": 2, "qualifies_recus": 5})
    assert "05/06/2026" in corps2 and "2026-06-05" not in corps2


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


# -- Accusé de réception AU CLUB (avec détail) -------------------------

def test_accuse_club_detail():
    sujet, corps = mailer.construire_accuse_club(
        "CDF Équipes Sabre", "CE Strasbourg", TIREURS, ARBITRES)
    assert "enregistrée" in sujet and "CDF Équipes Sabre" in sujet
    assert "bien été enregistrée" in corps
    assert "Présents (2)" in corps
    assert "Léa Durand — veste M" in corps          # détail présent
    assert "Max Roy (Nancy, national)" in corps      # arbitre


def test_message_html_intro_optionnel():
    sans = mailer.construire_message_html("X", "Club Y", TIREURS, [])
    avec = mailer.construire_message_html("X", "Club Y", TIREURS, [], intro="Merci !")
    assert "Merci !" not in sans          # rétro-compatible (secrétariat inchangé)
    assert "Merci !" in avec


def test_accuse_html_montre_la_division():
    eq = [{"nom": "GE Sabre 1", "prenom": "", "present": 1,
           "equipe": "N1 — Hommes", "section": "N1", "taille_veste": None}]
    html = mailer.construire_message_html("CDF", "CE Strasbourg", eq, [],
                                          intro="Votre confirmation a bien été enregistrée. Merci !")
    assert "N1 — Hommes" in html and "bien été enregistrée" in html


def test_notifier_accuse_club_vers_le_club():
    _clean_env()
    r = mailer.notifier_accuse_club("CDF", "CE X", "club@example.fr", TIREURS, ARBITRES)
    assert r["recipients"] == ["club@example.fr"]
    assert r["dry_run"] is True and r["sent"] is False


def test_notifier_accuse_club_sans_email_ne_part_pas():
    r = mailer.notifier_accuse_club("CDF", "CE X", "", TIREURS, [])
    assert r["sent"] is False and r["recipients"] == []
    assert r["error"] == "club_email manquant"


# -- Modification par le club + notification de création ----------------

def test_message_modification_label():
    sujet, corps = mailer.construire_message("CDF", "CE X", TIREURS, ARBITRES, modification=True)
    assert sujet.startswith("[Modification LREGE]")
    assert "a MODIFIÉ" in corps


def test_accuse_modification_label():
    sujet, corps = mailer.construire_accuse_club("CDF", "CE X", TIREURS, [], modification=True)
    assert "mise à jour" in sujet.lower()
    assert "mise à jour" in corps.lower()


def test_notifier_confirmation_modification_html(monkeypatch):
    cap = {}

    def fake(recipients, sujet, corps, html=None):
        cap.update(sujet=sujet, html=html)
        return {"sent": True, "dry_run": False, "recipients": recipients,
                "subject": sujet, "error": None}

    monkeypatch.setattr(mailer, "_envoyer", fake)
    mailer.notifier_confirmation("CDF", "CE X", TIREURS, ARBITRES, modification=True)
    assert cap["sujet"].startswith("[Modification LREGE]")
    assert "Modifié" in cap["html"] and "MODIFIÉE" in cap["html"]


def test_creation_selection_contenu():
    comp = {"nom": "CDF Sabre Seniors", "categorie": "Seniors", "format": "equipe",
            "arme": "sabre", "genre": "HD", "date_limite": "10/03/2026"}
    sujet, corps = mailer.construire_creation_selection(comp, {"clubs": 5, "qualifies_recus": 12})
    assert "Nouvelle sélection" in sujet and "CDF Sabre Seniors" in sujet
    assert "Clubs concernés : 5" in corps and "12" in corps


def test_notifier_creation_vers_secretariat():
    _clean_env()
    r = mailer.notifier_creation_selection({"nom": "X"}, {"clubs": 1, "qualifies_recus": 1})
    assert "atrcrege@gmail.com" in r["recipients"]
    assert "thomas.ducourant@gmail.com" in r["recipients"]
    assert r["dry_run"] is True
