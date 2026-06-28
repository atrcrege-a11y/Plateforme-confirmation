"""
Test pont ÉQUIPES SÉNIORS : la plateforme accepte le payload SelecGE équipes
séniors (format=equipe) et la division (N1/N2/N3) ressort dans le dashboard
ET dans le mail de confirmation.
"""
import os
import tempfile

import pytest

import migrate
from db import get_connection
import app as app_module
from mailer import construire_message_html

TOKEN = "admin-local"


def _payload_seniors():
    # Contrat tel que construire_payload_equipes_seniors (SelecGE) le produit.
    return {
        "competition": {
            "nom": "CDF Équipes Sabre", "categorie": "Seniors", "format": "equipe",
            "arme": "sabre", "genre": "HD", "date": "2026-03-21", "lieu": "PARIS",
            "date_limite": "2026-03-10",
            "arbitres_requis": 0, "type_arbitrage": "none",
            "seuil1": 4, "seuil2": 9, "source_arbitres": "aucun",
        },
        "qualifies": [
            {"nom": "GE Sabre 1", "prenom": "", "club": "Strasbourg",
             "section": "N1", "rang": 1, "equipe": "N1 — Hommes"},
            {"nom": "GE Sabre 2", "prenom": "", "club": "Metz",
             "section": "N2", "rang": 9, "equipe": "N2 — Hommes"},
            {"nom": "GE Sabre 3", "prenom": "", "club": "Nancy",
             "section": "N3 FFE", "rang": 10, "equipe": "N3 FFE — Hommes"},
            {"nom": "GE Dames 1", "prenom": "", "club": "Mulhouse",
             "section": "N1", "rang": 1, "equipe": "N1 — Dames"},
        ],
    }


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["PLATEFORME_DB"] = path
    os.environ.pop("ADMIN_TOKEN", None)
    migrate.migrate(path)
    app_module.app.config["TESTING"] = True
    yield app_module.app.test_client()
    os.environ.pop("PLATEFORME_DB", None)
    os.remove(path)


def test_import_equipes_seniors_accepte(client):
    r = client.post(f"/api/import/{TOKEN}", json=_payload_seniors())
    assert r.status_code == 201, r.get_data(as_text=True)
    res = r.get_json()
    assert res["qualifies_crees"] == 4
    assert res["clubs_crees"] == 4          # 4 clubs distincts
    assert res["confirmations_creees"] == 4  # 1 confirmation par club


def test_division_stockee_section_et_equipe(client):
    client.post(f"/api/import/{TOKEN}", json=_payload_seniors())
    conn = get_connection(os.environ["PLATEFORME_DB"])
    try:
        comp = conn.execute("SELECT format FROM competition").fetchone()
        assert comp["format"] == "equipe"
        rows = conn.execute(
            "SELECT nom, section, equipe FROM qualifie ORDER BY equipe"
        ).fetchall()
    finally:
        conn.close()
    sections = {r["section"] for r in rows}
    assert {"N1", "N2", "N3 FFE"} <= sections
    # division lisible dans equipe (colonne mail)
    n1h = [r for r in rows if r["nom"] == "GE Sabre 1"][0]
    assert n1h["equipe"] == "N1 — Hommes"


def test_division_visible_dans_mail(client):
    # Le mail HTML affiche t.equipe en priorité → la division doit apparaître.
    tireurs = [
        {"nom": "GE Sabre 1", "prenom": "", "equipe": "N1 — Hommes",
         "section": "N1", "present": 1, "taille_veste": None},
        {"nom": "GE Sabre 3", "prenom": "", "equipe": "N3 FFE — Hommes",
         "section": "N3 FFE", "present": 1, "taille_veste": None},
    ]
    html = construire_message_html("CDF Équipes Sabre", "Strasbourg", tireurs, [])
    assert "N1 — Hommes" in html
    assert "N3 FFE — Hommes" in html
    assert "GE Sabre 1" in html
