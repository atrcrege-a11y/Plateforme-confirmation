# Déploiement en production — PythonAnywhere

Cible : héberger la plateforme sur PythonAnywhere (Python/Flask, stockage
persistant pour SQLite, tâche planifiée intégrée pour les rappels).
URL de départ : `https://<pseudo>.pythonanywhere.com` (un sous-domaine
`confirmation.crege.fr` pourra être branché plus tard).

Remplace partout `<pseudo>` par ton nom d'utilisateur PythonAnywhere.

---

## 1. Compte
1. Créer un compte sur https://www.pythonanywhere.com (l'offre gratuite
   « Beginner » suffit pour démarrer ; ~5 €/mois si tu veux ton domaine).
2. Noter le nom d'utilisateur `<pseudo>`.

## 2. Envoyer le code
Deux options, au choix :
- **Git** (si le projet est sur un dépôt) : onglet *Consoles* → *Bash* :
  ```bash
  git clone <url-du-depot> plateforme-confirmation
  ```
- **Upload manuel** : onglet *Files* → créer le dossier `plateforme-confirmation`
  et y téléverser tous les fichiers du projet (sauf `*.db`, `__pycache__`,
  `prod_settings.py`).

Le dossier final attendu : `/home/<pseudo>/plateforme-confirmation`.

## 3. Environnement Python (virtualenv)
Console *Bash* :
```bash
cd ~/plateforme-confirmation
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Configuration secrète (`prod_settings.py`)
```bash
cd ~/plateforme-confirmation
cp prod_settings_example.py prod_settings.py
# générer un token admin solide :
python -c "import secrets; print(secrets.token_urlsafe(24))"
```
Éditer `prod_settings.py` (onglet *Files*) et renseigner :
- `PLATEFORME_DB` → `/home/<pseudo>/plateforme-confirmation/plateforme.db`
- `ADMIN_TOKEN` → le token généré ci-dessus (le garder secret)
- `BASE_URL` → `https://<pseudo>.pythonanywhere.com`
- `SMTP_PASSWORD` → ton mot de passe d'application Gmail
- (les autres valeurs Gmail / NOTIF_RECIPIENTS sont déjà bonnes)

## 5. Créer la base
```bash
cd ~/plateforme-confirmation && source .venv/bin/activate
python -c "import prod_settings; import migrate; print('schema v', migrate.migrate())"
```
> Ceci crée une base **vide**. Les vraies compétitions/clubs/qualifiés devront
> être importés (voir « Données réelles » plus bas). Pour une démo immédiate :
> `python -c "import prod_settings, migrate, seed_demo; from db import get_connection; c=get_connection(); seed_demo.seed(c); c.close()"`

## 6. Créer la Web app
1. Onglet *Web* → *Add a new web app* → *Manual configuration* → *Python 3.10*.
2. **Virtualenv** : renseigner `/home/<pseudo>/plateforme-confirmation/.venv`.
3. **Source code** / **Working directory** : `/home/<pseudo>/plateforme-confirmation`.
4. **WSGI configuration file** : cliquer le lien, **tout remplacer** par le contenu
   de `wsgi_pythonanywhere_example.py` (en remplaçant `<pseudo>`).
5. Cliquer **Reload**.

Vérifier : ouvrir `https://<pseudo>.pythonanywhere.com/health` → doit renvoyer
`{"status":"ok",...}`.

## 7. Dashboard
Ton accès permanent (à garder pour toi) :
```
https://<pseudo>.pythonanywhere.com/dashboard/<ADMIN_TOKEN>
```
Un mauvais token renvoie 404 (le dashboard n'est pas découvrable).

## 8. Rappels automatiques (tâche planifiée)
Onglet *Tasks* → *Scheduled tasks* → créer une tâche **quotidienne** (ex. 07:00) :
```
/home/<pseudo>/plateforme-confirmation/.venv/bin/python /home/<pseudo>/plateforme-confirmation/cron_rappels.py
```
Elle relance chaque jour les clubs non confirmés dont la date limite tombe à
J-10 / J-7 / J-3. La sortie est consultable dans le log de la tâche.

## 9. Vérification finale
- `/health` répond ✓
- Dashboard accessible avec ton token, 404 sinon ✓
- Un lien club `/c/<token>` s'ouvre (après import de données réelles) ✓
- Tâche planifiée : la lancer une fois à la main (*Run now*) et lire le log ✓

---

## Données réelles (prérequis pour un usage réel)
La base déployée est **vide**. Il manque un import des compétitions, clubs et
qualifiés depuis l'export SelecGE → **tâche suivante à cadrer** (format de
l'export ? CSV/Excel/JSON ?). En attendant, seul `seed_demo.py` (données
fictives) permet de tester l'interface.

## Maintenance
- **Mettre à jour le code** : `git pull` (ou ré-upload) puis *Reload* la web app.
- **Sauvegarde** : télécharger régulièrement `plateforme.db` (onglet *Files*).
- **Changer le token admin** : modifier `ADMIN_TOKEN` dans `prod_settings.py` puis *Reload*.
- **Logs** : onglet *Web* → *Error log* (web) ; onglet *Tasks* (rappels).
