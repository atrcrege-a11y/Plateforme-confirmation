"""
cron_rappels.py — Point d'entrée pour la tâche planifiée (1×/jour).

Charge la configuration de prod (variables d'env via prod_settings) PUIS lance
l'envoi des rappels. À utiliser comme commande de la « Scheduled task »
PythonAnywhere :

    python3.10 /home/<pseudo>/plateforme-confirmation/cron_rappels.py

En l'absence de prod_settings.py (ex. en local), tombe en dry-run via les
variables d'env déjà présentes — aucun envoi accidentel.
"""
try:
    import prod_settings  # noqa: F401  (pose les variables d'environnement)
except ModuleNotFoundError:
    pass

from rappels import run

if __name__ == "__main__":
    run()
