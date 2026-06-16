"""Tests notifications (2.7) — dry-run, destinataires, contenu. Aucun envoi réel."""
import os

import mailer


def _clean_env():
    for k in ("SMTP_HOST", "NOTIF_RECIPIENTS"):
        os.environ.pop(k, None)


def test_message_contient_les_infos():
    sujet, corps = mailer.construire_message("CDF M15", "Escrime Nancy", 4, 1)
    assert "Escrime Nancy" in sujet and "CDF M15" in sujet
    assert "Tireurs confirmés : 4" in corps and "Arbitres saisis : 1" in corps


def test_dry_run_sans_smtp():
    _clean_env()  # pas de SMTP_HOST -> dry-run, pas d'envoi
    r = mailer.notifier_confirmation("CDF M15", "Nancy", 4, 1)
    assert r["dry_run"] is True and r["sent"] is False and r["error"] is None
    # destinataires de test par défaut
    assert "atrcrege@gmail.com" in r["recipients"]
    assert "thomas.ducourant@gmail.com" in r["recipients"]


def test_destinataires_surchargeables():
    _clean_env()
    os.environ["NOTIF_RECIPIENTS"] = "administration@crege.fr"
    try:
        r = mailer.notifier_confirmation("X", "Y", 1, 0)
        assert r["recipients"] == ["administration@crege.fr"]
    finally:
        os.environ.pop("NOTIF_RECIPIENTS", None)
