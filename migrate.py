"""migrate.py — Création / migration de la base SQLite."""
import os
from db import get_connection, DB_PATH, BASE_DIR

SCHEMA_VERSION = 5  # incrémenter à chaque nouvelle migration

MIGRATIONS = {
    2: [
        "CREATE TABLE IF NOT EXISTS utilisateur ("
        " id INTEGER PRIMARY KEY,"
        " email TEXT NOT NULL UNIQUE,"
        " nom TEXT NOT NULL,"
        " mdp_hash TEXT NOT NULL,"
        " role TEXT NOT NULL CHECK(role IN ('admin','secretariat')))",
    ],
    3: [
        "ALTER TABLE confirmation ADD COLUMN corrige_par TEXT",
        "ALTER TABLE confirmation ADD COLUMN date_correction TEXT",
    ],
    4: [
        "ALTER TABLE qualifie ADD COLUMN genre TEXT",
    ],
    5: [
        "ALTER TABLE qualifie ADD COLUMN rang_label TEXT",
    ],
}


def _apply_base_schema(conn):
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())


def migrate(db_path=None):
    """Crée/migre la base et retourne la version finale."""
    conn = get_connection(db_path)
    try:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        if current == 0:
            _apply_base_schema(conn)
            current = SCHEMA_VERSION  # base neuve = schema.sql complet, pas de migration à rejouer
        for version in sorted(MIGRATIONS):
            if version > current:
                for stmt in MIGRATIONS[version]:
                    conn.execute(stmt)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
        return conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()


if __name__ == "__main__":
    v = migrate()
    print(f"Base migrée : {DB_PATH} (schema_version={v})")
