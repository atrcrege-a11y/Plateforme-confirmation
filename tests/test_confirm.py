"""
Tests routes 2.2 — lecture + enregistrement + CLOISONNEMENT par club.
Base temporaire isolée + Flask test client.
"""
import os
import tempfile

import pytest

import migrate
import seed_demo
from db import get_connection
import app as app_module


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["PLATEFORME_DB"] = path  # get_connection() lit l'env à chaque appel
    migrate.migrate(path)
    conn = get_connection(path)
    seed_demo.seed(conn)
    conn.close()
    app_module.app.config["TESTING"] = True
    yield app_module.app.test_client()
    os.environ.pop("PLATEFORME_DB", None)
    os.remove(path)


def test_lecture_scope_par_club(client):
    r = client.get("/api/c/tok-chalons")
    assert r.status_code == 200
    data = r.get_json()
    assert data["club"]["nom"].startswith("C.E. de Châlons")
    # Châlons voit tous les qualifiés, mais seuls les siens ont mine=True
    mine = [q for q in data["qualifies"] if q["mine"]]
    pas_mine = [q for q in data["qualifies"] if not q["mine"]]
    assert {q["nom"] for q in mine} == {"JANER", "WILLEM"}
    assert {q["nom"] for q in pas_mine} == {"HOPFNER", "CLAUDE DESCHASEAUX"}


def test_token_invalide_404(client):
    assert client.get("/api/c/inconnu").status_code == 404


def test_page_html_rendue(client):
    # la page /c/<token> est servie en HTML (le JS appelle ensuite /api/c/<token>)
    r = client.get("/c/tok-chalons")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "tok-chalons" in html and "/static/arbitres.js" in html


def test_m15_champ_veste(client):
    data = client.get("/api/c/tok-chalons").get_json()
    assert [c["key"] for c in data["competition"]["champs"]] == ["taille_veste"]


def test_confirmer_ses_tireurs(client):
    # qualifie ids de Châlons : récupère via GET
    data = client.get("/api/c/tok-chalons").get_json()
    mine = [q["id"] for q in data["qualifies"] if q["mine"]]
    body = {"confirme_par_email": "chalons@x.fr",
            "participations": [{"qualifie_id": mine[0], "present": True, "taille_veste": "M"},
                               {"qualifie_id": mine[1], "present": False}]}
    r = client.post("/api/confirm/tok-chalons", json=body)
    assert r.status_code == 201
    assert r.get_json()["tireurs_enregistres"] == 2
    # statut passé à confirmee
    assert client.get("/api/c/tok-chalons").get_json()["statut"] == "confirmee"


def test_cloisonnement_refus_autre_club(client):
    # Châlons tente d'écrire sur un tireur de Romarimontain (HOPFNER)
    data = client.get("/api/c/tok-chalons").get_json()
    autre = [q["id"] for q in data["qualifies"] if not q["mine"]][0]
    r = client.post("/api/confirm/tok-chalons",
                    json={"participations": [{"qualifie_id": autre, "present": True, "taille_veste": "M"}]})
    assert r.status_code == 403


def test_veste_obligatoire_si_present(client):
    data = client.get("/api/c/tok-chalons").get_json()
    mine = [q["id"] for q in data["qualifies"] if q["mine"]][0]
    r = client.post("/api/confirm/tok-chalons",
                    json={"participations": [{"qualifie_id": mine, "present": True}]})
    assert r.status_code == 400


def test_niveau_arbitre_invalide(client):
    data = client.get("/api/c/tok-chalons").get_json()
    mine = [q["id"] for q in data["qualifies"] if q["mine"]][0]
    r = client.post("/api/confirm/tok-chalons",
                    json={"participations": [{"qualifie_id": mine, "present": False}],
                          "arbitres": [{"nom": "X", "prenom": "Y", "club": "Z", "niveau": "B"}]})
    assert r.status_code == 400


def test_veterans_champs_et_arbitres(client):
    data = client.get("/api/c/tok-vet-chalons").get_json()
    keys = [c["key"] for c in data["competition"]["champs"]]
    assert keys == ["categorie_age"]               # catégorie d'âge, pas veste
    assert data["arbitrage"]["arbitres_requis_nombre"] == 1   # master
    mine = [q["id"] for q in data["qualifies"] if q["mine"]]
    # présent sans catégorie d'âge -> 400
    r = client.post("/api/confirm/tok-vet-chalons", json={
        "participations": [{"qualifie_id": mine[0], "present": True}],
        "arbitres": [{"nom": "A", "prenom": "B", "club": "C", "niveau": "national"}]})
    assert r.status_code == 400
    # complet -> 201
    r2 = client.post("/api/confirm/tok-vet-chalons", json={
        "participations": [{"qualifie_id": mine[0], "present": True, "categorie_age": "V1-V2"},
                           {"qualifie_id": mine[1], "present": False}],
        "arbitres": [{"nom": "A", "prenom": "B", "club": "C", "niveau": "national"}]})
    assert r2.status_code == 201


def test_individuel_sections_et_arbitrage(client):
    data = client.get("/api/c/tok-indiv-chalons").get_json()
    assert data["competition"]["format"] == "individuel"
    assert data["competition"]["champs"] == []          # Senior : pas de champ par tireur
    # sections distinctes parmi les qualifiés du club
    sections = {q["section"] for q in data["qualifies"] if q["mine"]}
    assert sections == {"Qualifiés", "Remplaçants 1-5"}
    # standard, 4 qualifiés club -> 1 arbitre
    assert data["arbitrage"]["arbitres_requis_nombre"] == 1
    mine = [q["id"] for q in data["qualifies"] if q["mine"]]
    r = client.post("/api/confirm/tok-indiv-chalons", json={
        "participations": [{"qualifie_id": i, "present": True} for i in mine],
        "arbitres": [{"nom": "A", "prenom": "B", "club": "C", "niveau": "regional"}]})
    assert r.status_code == 201


def test_m20_equipe_simple(client):
    data = client.get("/api/c/tok-m20-chalons").get_json()
    assert data["competition"]["format"] == "equipe"
    assert data["competition"]["champs"] == []          # aucun champ extra
    assert data["arbitrage"]["arbitres_requis_nombre"] == 0
    mine = [q["id"] for q in data["qualifies"] if q["mine"]]
    # présence seule, sans champ ni arbitre -> 201
    r = client.post("/api/confirm/tok-m20-chalons", json={
        "participations": [{"qualifie_id": i, "present": True} for i in mine]})
    assert r.status_code == 201
