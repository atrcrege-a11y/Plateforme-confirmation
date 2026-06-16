"""
migrate.py — Création / migration de la base SQLite.

Applique schema.sql (idempotent : CREATE TABLE IF NOT EXISTS) puis pose
PRAGMA user_version. Les migrations futures s'ajoutent dans MIGRATIONS,
indexées par numéro de version cible.

Usage :
    python migrate.py            # migre la base par défaut (plateforme.db)
    PLATEFORME_DB=/chemin/x.db python migrate.py
"""
import os

from db import get_connection, DB_PATH, BASE_DIR

SCHEMA_VERSION = 1  # incrémenter à chaque nouvelle migration

# Migrations incrémentales futures : {version_cible: [requêtes SQL]}
MIGRATIONS = {
    # 2: ["ALTER TABLE ... "],
}


def _apply_base_schema(conn):
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())


def migrate(db_path=None):
    """Crée/migre la base et retourne la version finale."""
    conn = get_connection(db_path)
    try:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        # Base vierge ou v0 : appliquer le schéma complet
        if current == 0:
            _apply_base_schema(conn)
        # Migrations incrémentales
        for version in sorted(MIGRATIONS):
            if version > current:
                for stmt in MIGRATIONS[version]:
                    conn.execute(stmt)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
        final = conn.execute("PRAGMA user_version").fetchone()[0]
        return final
    finally:
        conn.close()


if __name__ == "__main__":
    v = migrate()
    print(f"Base migrée : {DB_PATH} (schema_version={v})")
