# Plateforme Confirmation LREGE

Plateforme de confirmation des participations (clubs confirment tireurs/équipes + arbitres).
Backend Flask + SQLite (stdlib, sans ORM).

## Installation
```bash
pip install -r requirements.txt
python migrate.py        # crée plateforme.db à partir de schema.sql
```

## Lancer (dev)
```bash
python app.py            # http://127.0.0.1:5002
```

## Structure
| Fichier | Rôle |
|---|---|
| `schema.sql` | Schéma SQLite (6 tables) — source de vérité |
| `migrate.py` | Création/migration idempotente (PRAGMA user_version) |
| `db.py` | Connexion SQLite (Row factory + foreign_keys ON) |
| `app.py` | Fabrique Flask + route `/health` |
| `routes/confirm.py` | Squelette : `/c/<token>` (lien magique), `/api/dashboard` |
| `tests/test_schema.py` | Tests schéma (migration, relations, contraintes, cascade) |

## Modèle de données
`club` et `competition` (importée de l'export SelecGE, avec son bloc arbitrage)
alimentent `qualifie` (qui est qualifié, par club). Le club accède via un **lien
magique** (`confirmation.token`, par club × compétition, sans mot de passe), ce qui
crée/édite une `confirmation` ; il y rattache `participation_tireur` (présence,
taille de veste M15, catégorie d'âge vétérans) et `arbitre` (Nom/Prénom/Club/Niveau).

## Tests
```bash
python -m pytest tests/ -q
```

## Endpoints
| Route | Méthode | Rôle |
|---|---|---|
| `/c/<token>` | GET | **Page web** de confirmation (M15 équipes — 2.3). Le JS appelle l'API ci-dessous |
| `/api/c/<token>` | GET | Données du périmètre club : compétition, qualifiés (`mine` true/false), bloc arbitrage, saisie déjà enregistrée |
| `/api/confirm/<token>` | POST | Enregistre présences + arbitres. **Cloisonnement** : rejette (403) toute écriture sur un tireur d'un autre club. Valide veste (présents) et niveaux d'arbitre |
| `/health` | GET | Sonde |

Front : `templates/confirmation.html` + `static/arbitres.js` (composant arbitres réutilisable, 2.2b).

Démo de bout en bout : `python migrate.py && python seed_demo.py` (imprime un lien `/c/<token>` par club), puis `python app.py`.

## Notifications email (2.7)
Envoi **best-effort** à chaque confirmation (une panne SMTP n'échoue jamais la confirmation).
Sans `SMTP_HOST`, mode **dry-run** (rien n'est envoyé). Variables :

| Var | Rôle |
|---|---|
| `SMTP_HOST`,`SMTP_PORT`(587),`SMTP_USER`,`SMTP_PASSWORD`,`SMTP_FROM` | Connexion SMTP |
| `NOTIF_RECIPIENTS` | Destinataires (virgules). Défaut **test** : `atrcrege@gmail.com,thomas.ducourant@gmail.com` |

Prod : `NOTIF_RECIPIENTS="administration@crege.fr"` (réductible à `atrcrege@gmail.com` une fois le dashboard 3.1 en place).

## Variables d'environnement
- `PLATEFORME_DB` : chemin de la base (défaut `./plateforme.db`).
- SMTP + `NOTIF_RECIPIENTS` : voir ci-dessus.

## À venir
- **3.1** : dashboard secrétariat (suivi clubs confirmés/non confirmés).
- **3.2** : rappels automatiques (J-10/J-7/J-3).
