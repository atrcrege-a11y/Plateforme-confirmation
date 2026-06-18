"""Tests authentification — login, rôles, protection dashboard."""
import os
import tempfile

import pytest

import migrate
import seed_demo
import auth
from db import get_connection
import app as app_module


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["PLATEFORME_DB"] = path
    migrate.migrate(path)
    conn = get_connection(path)
    seed_demo.seed(conn)
    auth.creer_utilisateur(conn, "admin@x.fr", "Admin", "pw-admin", "admin")
    auth.creer_utilisateur(conn, "secr@x.fr", "Secrétariat", "pw-secr", "secretariat")
    conn.close()
    app_module.app.config["TESTING"] = True
    yield app_module.app.test_client()
    os.environ.pop("PLATEFORME_DB", None)
    os.remove(path)


def _login(client, email, mdp):
    return client.post("/login", data={"email": email, "mdp": mdp})


def test_dashboard_exige_connexion(client):
    # API non connecté -> 401 ; page non connectée -> redirection /login
    assert client.get("/api/dashboard").status_code == 401
    r = client.get("/dashboard")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_login_mauvais_identifiants(client):
    r = _login(client, "admin@x.fr", "mauvais")
    assert r.status_code == 200 and "incorrect" in r.get_data(as_text=True).lower()
    assert client.get("/api/dashboard").status_code == 401


def test_login_admin_puis_acces(client):
    r = _login(client, "admin@x.fr", "pw-admin")
    assert r.status_code == 302
    assert client.get("/api/dashboard").status_code == 200


def test_secretariat_voit_dashboard_et_export(client):
    _login(client, "secr@x.fr", "pw-secr")
    assert client.get("/api/dashboard").status_code == 200
    # confirme une compétition puis vérifie l'export accessible au secrétariat
    g = client.get("/api/c/tok-vet-chalons").get_json()
    mine = [q["id"] for q in g["qualifies"] if q["mine"]]
    client.post("/api/confirm/tok-vet-chalons", json={
        "participations": [{"qualifie_id": mine[0], "present": True, "categorie_age": "V1-V2"}]})
    assert client.get("/api/dashboard/export/2").status_code == 200


def test_logout(client):
    _login(client, "admin@x.fr", "pw-admin")
    assert client.get("/api/dashboard").status_code == 200
    client.get("/logout")
    assert client.get("/api/dashboard").status_code == 401


def test_email_insensible_casse(client):
    assert _login(client, "ADMIN@X.FR", "pw-admin").status_code == 302
