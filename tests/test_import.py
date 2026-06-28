"""
Tests POST /api/import — receveur palette SelecGE (individuel).
Création, idempotence, cloisonnement (1 confirmation/club), token, préservation.
"""
import os
import tempfile

import pytest

import migrate
from db import get_connection
import app as app_module

TOKEN = "admin-local"  # défaut dashboard.DEFAULT_ADMIN_TOKEN


def _payload():
    return {
        "competition": {
            "nom": "FÊTE DES JEUNES", "categorie": "M15", "format": "individuel",
            "arme": "sabre", "genre": "HD", "date": "2026-06-13", "lieu": "PARIS",
            "date_limite": "2026-06-05",
            "arbitres_requis": 1, "type_arbitrage": "standard",
            "seuil1": 4, "seuil2": 9, "source_arbitres": "club",
        },
        "qualifies": [
            {"nom": "JANER", "prenom": "Léo", "club": "C.E. de Châlons",
             "section": "QUOTA FÉDÉRAL", "rang": 1, "equipe": None},
            {"nom": "WILLEM", "prenom": "Jules", "club": "C.E. de Châlons",
             "section": "QUOTA FÉDÉRAL", "rang": 2, "equipe": None},
            {"nom": "HOPFNER", "prenom": "Anna", "club": "CE Romarimontain",
             "section": "QUOTA LREGE", "rang": 3, "equipe": None},
        ],
    }


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["PLATEFORME_DB"] = path
    os.environ.pop("ADMIN_TOKEN", None)  # force le défaut 'admin-local'
    migrate.migrate(path)
    app_module.app.config["TESTING"] = True
    yield app_module.app.test_client()
    os.environ.pop("PLATEFORME_DB", None)
    os.remove(path)


def _counts(path):
    conn = get_connection(path)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
                for t in ("competition", "club", "qualifie", "confirmation")}
    finally:
        conn.close()


def test_import_creation(client):
    r = client.post(f"/api/import/{TOKEN}", json=_payload())
    assert r.status_code == 201, r.get_data(as_text=True)
    res = r.get_json()
    assert res["competition_creee"] is True
    assert res["qualifies_crees"] == 3
    assert res["clubs_crees"] == 2
    assert res["confirmations_creees"] == 2  # 1 par club
    c = _counts(os.environ["PLATEFORME_DB"])
    assert c == {"competition": 1, "club": 2, "qualifie": 3, "confirmation": 2}


def test_idempotence_pas_de_doublon(client):
    client.post(f"/api/import/{TOKEN}", json=_payload())
    r = client.post(f"/api/import/{TOKEN}", json=_payload())
    assert r.status_code == 201
    res = r.get_json()
    assert res["competition_creee"] is False
    assert res["qualifies_crees"] == 0 and res["qualifies_maj"] == 3
    assert res["clubs_crees"] == 0 and res["confirmations_creees"] == 0
    c = _counts(os.environ["PLATEFORME_DB"])
    assert c == {"competition": 1, "club": 2, "qualifie": 3, "confirmation": 2}


def test_token_invalide_404(client):
    r = client.post("/api/import/mauvais-token", json=_payload())
    assert r.status_code == 404
    assert _counts(os.environ["PLATEFORME_DB"])["competition"] == 0


def test_payload_invalide_400(client):
    r = client.post(f"/api/import/{TOKEN}", json={"qualifies": []})  # competition.nom manquant
    assert r.status_code == 400
    assert _counts(os.environ["PLATEFORME_DB"])["competition"] == 0


def test_preserve_confirmation_existante(client):
    client.post(f"/api/import/{TOKEN}", json=_payload())
    path = os.environ["PLATEFORME_DB"]
    conn = get_connection(path)
    conn.execute("UPDATE confirmation SET statut='confirmee' WHERE id=1")
    tok_avant = conn.execute("SELECT token FROM confirmation WHERE id=1").fetchone()["token"]
    conn.commit()
    conn.close()
    # ré-import : ne doit pas réinitialiser le statut ni régénérer le token
    client.post(f"/api/import/{TOKEN}", json=_payload())
    conn = get_connection(path)
    row = conn.execute("SELECT statut, token FROM confirmation WHERE id=1").fetchone()
    conn.close()
    assert row["statut"] == "confirmee"
    assert row["token"] == tok_avant


def test_maj_rang_sur_reimport(client):
    client.post(f"/api/import/{TOKEN}", json=_payload())
    p = _payload()
    p["qualifies"][0]["rang"] = 99  # JANER passe rang 99
    client.post(f"/api/import/{TOKEN}", json=p)
    conn = get_connection(os.environ["PLATEFORME_DB"])
    rang = conn.execute(
        "SELECT rang FROM qualifie WHERE nom='JANER'").fetchone()["rang"]
    conn.close()
    assert rang == 99


def test_arme_normalisee_en_label(client):
    p = _payload()
    p["competition"]["arme"] = "E"            # lettre legacy
    r = client.post(f"/api/import/{TOKEN}", json=p)
    assert r.status_code == 201
    conn = get_connection(os.environ["PLATEFORME_DB"])
    arme = conn.execute("SELECT arme FROM competition WHERE id=?",
                        (r.get_json()["competition_id"],)).fetchone()["arme"]
    conn.close()
    assert arme == "epee"


def test_suivi_lecture_token(client):
    client.post(f"/api/import/{TOKEN}", json=_payload())
    r = client.get(f"/api/suivi/{TOKEN}")
    assert r.status_code == 200
    comps = r.get_json()["competitions"]
    assert len(comps) == 1
    c = comps[0]
    assert c["nom"] == "FÊTE DES JEUNES" and c["arme"] == "sabre" and c["format"] == "individuel"
    assert c["clubs_total"] == 2
    # roster attendus exposé par club
    assert sum(k["attendus_total"] for k in c["clubs"]) == 3
    # token invalide => 404
    assert client.get("/api/suivi/mauvais").status_code == 404


def test_creation_notifie_secretariat_une_seule_fois(client, monkeypatch):
    import routes.import_api as iapi
    calls = []
    monkeypatch.setattr(iapi, "notifier_creation_selection",
                        lambda comp, resume: calls.append(comp.get("nom")))
    client.post(f"/api/import/{TOKEN}", json=_payload())   # création -> notifie
    client.post(f"/api/import/{TOKEN}", json=_payload())   # ré-import -> pas de notif
    assert calls == ["FÊTE DES JEUNES"]
