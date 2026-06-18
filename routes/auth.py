"""routes/auth.py — Connexion / déconnexion (session cookie)."""
from flask import Blueprint, render_template, request, redirect, url_for, session

from db import get_connection
import auth

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    erreur = None
    if request.method == "POST":
        email = request.form.get("email", "")
        mdp = request.form.get("mdp", "")
        conn = get_connection()
        try:
            u = auth.authentifier(conn, email, mdp)
        finally:
            conn.close()
        if u:
            session["user"] = {"id": u["id"], "email": u["email"],
                               "nom": u["nom"], "role": u["role"]}
            nxt = request.args.get("next") or url_for("dashboard.page_dashboard")
            return redirect(nxt)
        erreur = "Identifiants incorrects."
    return render_template("login.html", erreur=erreur)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
