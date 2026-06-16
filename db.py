"""
db.py — Accès SQLite (stdlib, sans ORM).

Connexion configurée avec :
  - row_factory = sqlite3.Row (accès par nom de colonne)
  - PRAGMA foreign_keys = ON (cascades respectées)
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(BASE_DIR, "plateforme.db")


def db_path():
    """Chemin de la base, résolu à chaque appel (PLATEFORME_DB > défaut)."""
    return os.environ.get("PLATEFORME_DB", DEFAULT_DB)


# Conservé pour compat (affichage migrate.py). Préférer db_path() pour le runtime.
DB_PATH = db_path()


def get_connection(path=None):
    """Retourne une connexion SQLite prête à l'emploi.

    Le chemin est résolu dynamiquement (env PLATEFORME_DB) si non fourni, pour
    que les tests puissent isoler la base sans recharger les modules.
    """
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
