"""
prod_settings_example.py — Modèle de configuration de PRODUCTION.

NE PAS mettre de secrets ici. Copier ce fichier en `prod_settings.py`
(ignoré par git) et y renseigner les vraies valeurs. `prod_settings.py` est
importé par le fichier WSGI et par `cron_rappels.py` AVANT le chargement de
l'application : il sert uniquement à poser les variables d'environnement.

Générer un secret solide (ADMIN_TOKEN ou SECRET_KEY) :
    python -c "import secrets; print(secrets.token_urlsafe(24))"
"""
import os

# Chemin ABSOLU de la base (même fichier pour le web et le cron).
# Sur PythonAnywhere : /home/<pseudo>/plateforme-confirmation/plateforme.db
os.environ.setdefault("PLATEFORME_DB",
                      "/home/CHANGEME/plateforme-confirmation/plateforme.db")

# Clé de signature des sessions de connexion (OBLIGATOIRE en prod).
# Sans elle, les cookies de session ne sont pas sûrs. Générer comme ci-dessus.
os.environ.setdefault("SECRET_KEY", "CHANGEME-cle-session-secrete")

# Cookie envoyé uniquement en HTTPS (1 en prod PythonAnywhere, 0 en local HTTP).
os.environ.setdefault("COOKIE_SECURE", "1")

# Token du déclencheur cron /cron/rappels/<token> (appel machine cron-job.org).
os.environ.setdefault("ADMIN_TOKEN", "CHANGEME-token-secret")

# URL publique (réécrit les liens dans les emails de rappel).
os.environ.setdefault("BASE_URL", "https://CHANGEME.pythonanywhere.com")

# Destinataires des notifications de confirmation (dashboard en place -> toi seul).
os.environ.setdefault("NOTIF_RECIPIENTS", "atrcrege@gmail.com")

# SMTP Gmail (mot de passe d'application, pas le mot de passe du compte).
os.environ.setdefault("SMTP_HOST", "smtp.gmail.com")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USER", "atrcrege@gmail.com")
os.environ.setdefault("SMTP_PASSWORD", "CHANGEME-mot-de-passe-application")
os.environ.setdefault("SMTP_FROM", "atrcrege@gmail.com")
