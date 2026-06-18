"""auth.py — Authentification par session + rôles (admin / secrétariat).

Mots de passe hachés via werkzeug (fourni par Flask). Deux décorateurs :
  - login_requis     : pages HTML — redirige vers /login si non connecté
  - api_auth(*roles) : endpoints JSON — 401 si non connecté, 403 si mauvais rôle
"""
from functools import wraps

from flask import session, redirect, url_for, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash


def hash_mdp(mdp):
    return generate_password_hash(mdp)


def creer_utilisateur(conn, email, nom, mdp, role):
    """Crée un compte. role ∈ {'admin','secretariat'}. email normalisé."""
    if role not in ("admin", "secretariat"):
        raise ValueError(f"role invalide : {role!r}")
    conn.execute(
        "INSERT INTO utilisateur(email, nom, mdp_hash, role) VALUES (?,?,?,?)",
        (email.strip().lower(), nom, hash_mdp(mdp), role),
    )
    conn.commit()


def trouver_utilisateur(conn, email):
    return conn.execute(
        "SELECT * FROM utilisateur WHERE email = ?", (email.strip().lower(),)
    ).fetchone()


def authentifier(conn, email, mdp):
    """Retourne la ligne utilisateur si email+mdp valides, sinon None."""
    u = trouver_utilisateur(conn, email)
    if u and check_password_hash(u["mdp_hash"], mdp):
        return u
    return None


def utilisateur_courant():
    """dict {id,email,nom,role} de la session, ou None."""
    return session.get("user")


def login_requis(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def api_auth(*roles):
    """Protège un endpoint JSON. Sans rôle listé => tout utilisateur connecté."""
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            u = session.get("user")
            if not u:
                return jsonify({"error": "non authentifié"}), 401
            if roles and u["role"] not in roles:
                return jsonify({"error": "accès refusé"}), 403
            return f(*args, **kwargs)
        return wrapper
    return deco
