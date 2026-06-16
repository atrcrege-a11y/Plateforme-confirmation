"""
Tests dashboard secrétariat (3.1) — auth admin, agrégat non cloisonné, export xlsx.
Base temporaire isolée + Flask test client.
"""
import io
import os
import tempfile

import pytest

import migrate
import seed_demo
from db import get_connection
import app as app_module

ADMIN = "adm-test"


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["PLATEFORME_DB"] = path
    os.environ["ADMIN_TOKEN"] = ADMIN
    migrate.migrate(path)
    conn = get_connection(path)
    seed_demo.seed(conn)
    conn.close()
    app_module.app.config["TESTING"] = True
    yield app_module.app.test_client()
    os.environ.pop("PLATEFORME_DB", None)
    os.environ.pop("ADMIN_TOKEN", None)
    os.remove(path)


def test_token_admin_invalide_404(client):
    assert client.get("/api/dashboard/mauvais").status_code == 404
    assert client.get(f"/api/dashboard/{ADMIN}").status_code == 200


def test_agregat_non_cloisonne_et_progression(client):
    # avant confirmation : comp1 a 2 clubs, 0 confirmé
    data = client.get(f"/api/dashboard/{ADMIN}").get_json()
    comp1 = next(c for c in data["competitions"] if c["id"] == 1)
    assert comp1["clubs_total"] == 2  # dashboard voit TOUS les clubs (non cloisonné)
    assert comp1["clubs_confirmes"] == 0 and comp1["clubs_en_attente"] == 2

    # Châlons confirme 1 présent
    g = client.get("/api/c/tok-chalons").get_json()
    mine = [q["id"] for q in g["qualifies"] if q["mine"]]
    client.post("/api/confirm/tok-chalons", json={
        "participations": [{"qualifie_id": mine[0], "present": True, "taille_veste": "M"},
                           {"qualifie_id": mine[1], "present": False}]})

    data = client.get(f"/api/dashboard/{ADMIN}").get_json()
    comp1 = next(c for c in data["competitions"] if c["id"] == 1)
    assert comp1["clubs_confirmes"] == 1 and comp1["clubs_en_attente"] == 1
    assert comp1["tireurs_presents"] == 1


def test_export_xlsx(client):
    # confirme Vétérans (1 présent + 1 arbitre) puis exporte la compétition 2
    g = client.get("/api/c/tok-vet-chalons").get_json()
    mine = [q["id"] for q in g["qualifies"] if q["mine"]]
    client.post("/api/confirm/tok-vet-chalons", json={
        "participations": [{"qualifie_id": mine[0], "present": True, "categorie_age": "V1-V2"},
                           {"qualifie_id": mine[1], "present": False}],
        "arbitres": [{"nom": "A", "prenom": "B", "club": "C", "niveau": "national"}]})

    r = client.get(f"/api/dashboard/{ADMIN}/export/2")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["Content-Type"]

    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(r.data))
    assert wb.sheetnames == ["Tireurs", "Arbitres"]
    # 1 entête + 2 lignes tireurs (présent + absent confirmés)
    assert wb["Tireurs"].max_row == 3
    # 1 entête + 1 arbitre
    assert wb["Arbitres"].max_row == 2
    assert wb["Arbitres"].cell(2, 5).value == "national"
