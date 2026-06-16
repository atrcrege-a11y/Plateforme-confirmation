"""
Tests rappels automatiques (3.2) — fenêtre J-10/J-7/J-3, exclusion des confirmés,
envoi best-effort dry-run.
"""
import datetime
import os
import tempfile

import pytest

import migrate
import seed_demo
from db import get_connection
import rappels
import mailer


@pytest.fixture()
def conn():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    migrate.migrate(path)
    c = get_connection(path)
    seed_demo.seed(c)
    yield c
    c.close()
    os.remove(path)


def test_fenetre_j7(conn):
    # comp1 date_limite = 2026-04-24 ; today = J-7
    today = datetime.date(2026, 4, 17)
    cibles = rappels.clubs_a_relancer(conn, today)
    assert {c["token"] for c in cibles} == {"tok-chalons", "tok-romari"}
    assert all(c["jours_restants"] == 7 for c in cibles)


def test_hors_fenetre_aucune(conn):
    today = datetime.date(2026, 4, 18)  # J-6, pas dans (10,7,3)
    assert rappels.clubs_a_relancer(conn, today) == []


def test_confirmes_exclus(conn):
    conn.execute("UPDATE confirmation SET statut='confirmee' WHERE token='tok-chalons'")
    conn.commit()
    today = datetime.date(2026, 4, 17)
    cibles = rappels.clubs_a_relancer(conn, today)
    assert {c["token"] for c in cibles} == {"tok-romari"}


def test_envoyer_rappels_dry_run(conn):
    os.environ.pop("SMTP_HOST", None)  # pas de SMTP -> dry-run
    res = rappels.envoyer_rappels(conn, today=datetime.date(2026, 4, 17),
                                  url="https://confirm.crege.fr")
    assert len(res) == 2
    assert all(r["dry_run"] and not r["sent"] for r in res)
    assert all(r["lien"].startswith("https://confirm.crege.fr/c/") for r in res)


def test_message_rappel_contenu():
    sujet, corps = mailer.construire_rappel(
        "Nancy", "CDF M15", "2026-04-24", 7, "https://x/c/tok")
    assert "CDF M15" in sujet
    assert "2026-04-24" in corps and "J-7" in corps and "https://x/c/tok" in corps
