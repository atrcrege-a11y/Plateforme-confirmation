# wsgi_pythonanywhere_example.py — MODÈLE pour le fichier WSGI de PythonAnywhere.
#
# Ne pas exécuter en local. Copier ce contenu dans l'éditeur WSGI de
# PythonAnywhere (onglet Web -> "WSGI configuration file"), en remplaçant
# <pseudo> par ton nom d'utilisateur PythonAnywhere.
import sys

# 1) Rendre le projet importable
projet = "/home/<pseudo>/plateforme-confirmation"
if projet not in sys.path:
    sys.path.insert(0, projet)

# 2) Charger la config de prod (variables d'environnement) AVANT l'app
import prod_settings  # noqa: E402,F401

# 3) Exposer l'application Flask sous le nom attendu par WSGI : "application"
from app import app as application  # noqa: E402
