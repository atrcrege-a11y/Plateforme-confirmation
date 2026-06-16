"""
Tests schéma SQLite (2.1) : création, relations, contraintes, cascade.
Base temporaire isolée (pas la base de prod).
"""
import os
import sqlite3
import tempfile

import pytest

import migrate
from db import get_connection


@pytest.fixture()
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    migrate.migrate(path)
    yield path
    os.remove(path)


def _seed(conn):
    conn.execute("INSERT INTO club(id,nom,code_ffe,email) VALUES (1,'Escrime Nancy','54N','nancy@x.fr')")
    conn.execute(
        "INSERT INTO competition(id,nom,categorie,format,arbitres_requis,type_arbitrage)"
        " VALUES (1,'CDF M15','M15','equipe',1,'master')"
    )
    conn.execute(
        "INSERT INTO confirmation(id,competition_id,club_id,token) VALUES (1,1,1,'tok-abc')"
    )
    conn.execute(
        "INSERT INTO qualifie(id,competition_id,club_id,nom,prenom,section,equipe)"
        " VALUES (1,1,1,'Durand','Léa','qualifie','GE1')"
    )
    conn.commit()


def test_migration_pose_la_version(db_path):
    conn = get_connection(db_path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == migrate.SCHEMA_VERSION
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"club", "competition", "qualifie", "confirmation",
                "participation_tireur", "arbitre"} <= tables
    finally:
        conn.close()


def test_migration_idempotente(db_path):
    # relancer la migration ne casse rien
    assert migrate.migrate(db_path) == migrate.SCHEMA_VERSION


def test_relations_et_jointure(db_path):
    conn = get_connection(db_path)
    try:
        _seed(conn)
        row = conn.execute(
            "SELECT cl.nom AS club, co.nom AS comp, q.equipe "
            "FROM qualifie q "
            "JOIN club cl ON cl.id=q.club_id "
            "JOIN competition co ON co.id=q.competition_id"
        ).fetchone()
        assert row["club"] == "Escrime Nancy" and row["comp"] == "CDF M15" and row["equipe"] == "GE1"
    finally:
        conn.close()


def test_token_unique(db_path):
    conn = get_connection(db_path)
    try:
        _seed(conn)
        conn.execute("INSERT INTO club(id,nom,email) VALUES (2,'Metz','metz@x.fr')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO confirmation(id,competition_id,club_id,token)"
                " VALUES (2,1,2,'tok-abc')"  # même token -> rejeté
            )
    finally:
        conn.close()


def test_cascade_suppression_confirmation(db_path):
    conn = get_connection(db_path)
    try:
        _seed(conn)
        conn.execute(
            "INSERT INTO arbitre(confirmation_id,nom,prenom,club,niveau)"
            " VALUES (1,'Petit','Marc','Nancy','national')"
        )
        conn.commit()
        conn.execute("DELETE FROM confirmation WHERE id=1")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM arbitre").fetchone()[0] == 0
    finally:
        conn.close()


def test_check_niveau_invalide(db_path):
    conn = get_connection(db_path)
    try:
        _seed(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO arbitre(confirmation_id,nom,prenom,club,niveau)"
                " VALUES (1,'X','Y','Z','depart')"  # niveau hors liste officielle
            )
    finally:
        conn.close()


def test_niveaux_officiels_acceptes(db_path):
    # 5 niveaux LREGE (cf. SelecGE feuille.py)
    conn = get_connection(db_path)
    try:
        _seed(conn)
        for n in ('regional_formation', 'regional',
                  'national_formation', 'national', 'international'):
            conn.execute(
                "INSERT INTO arbitre(confirmation_id,nom,prenom,club,niveau)"
                " VALUES (1,'A','B','C',?)", (n,))
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM arbitre").fetchone()[0] == 5
    finally:
        conn.close()
