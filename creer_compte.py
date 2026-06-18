"""creer_compte.py — Crée un compte d'accès au dashboard.

Usage :
    python creer_compte.py <email> <nom> <admin|secretariat> [mot_de_passe]
Si le mot de passe est omis, il est demandé sans écho.
"""
import sys
import getpass

from db import get_connection
import auth


def main():
    if len(sys.argv) < 4:
        print("Usage: python creer_compte.py <email> <nom> <admin|secretariat> [mdp]")
        sys.exit(1)
    email, nom, role = sys.argv[1], sys.argv[2], sys.argv[3]
    mdp = sys.argv[4] if len(sys.argv) > 4 else getpass.getpass("Mot de passe : ")
    conn = get_connection()
    try:
        auth.creer_utilisateur(conn, email, nom, mdp, role)
    finally:
        conn.close()
    print(f"Compte créé : {email} ({role})")


if __name__ == "__main__":
    main()
