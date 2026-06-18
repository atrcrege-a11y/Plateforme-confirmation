"""Tests notifications (2.7) — dry-run, destinataires, contenu. Aucun envoi réel."""
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
    assert "Léa Durand — veste M" in corps          # veste nominative
    assert "Tom Petit — V1-V2" in corps             # catégorie d'âge
    assert "Paul Absent" in corps                    # absent listé
    assert "Max Roy (Nancy, national)" in corps      # arbitre nominatif


def test_dry_run_sans_smtp():
    _clean_env()  # pas de SMTP_HOST -> dry-run, pas d'envoi
    r = mailer.notifier_confirmation("CDF M15", "Nancy", TIREURS, ARBITRES)
    assert r["dry_run"] is True and r["sent"] is False and r["error"] is None
    # destinataires de test par défaut
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
