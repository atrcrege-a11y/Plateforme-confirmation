# Passation — Phase 2 → Phase 3
*MAJ : 2026-06-16 — Phase 2 terminée (plateforme de confirmation fonctionnelle de bout en bout)*

## Où on en est
- **Phase 1** (refonte SelecGE — gestion arbitres) : terminée. Voir `PASSATION_phase1.md` + `SelecGE/REGLES.md §5`.
- **Phase 2** (plateforme de confirmation) : **terminée**, 21/21 tests verts.
- **Phase 3** (dashboard + rappels) : à démarrer → **3.1 dashboard secrétariat** (4h), puis **3.2 rappels** (2h).

## Architecture de la plateforme (dossier dédié)
Backend **Flask + SQLite** (stdlib, sans ORM), front **vanilla JS** servi en statique. Zéro build, déployable simplement.

| Fichier | Rôle |
|---|---|
| `schema.sql` | 6 tables : `club, competition, qualifie, confirmation, participation_tireur, arbitre` |
| `migrate.py` | Migration idempotente (`PRAGMA user_version`) |
| `db.py` | Connexion SQLite (Row factory, FK ON, chemin via env `PLATEFORME_DB`) |
| `app.py` | Fabrique Flask + `/health` |
| `routes/confirm.py` | Page `/c/<token>`, API `/api/c/<token>` (GET), `/api/confirm/<token>` (POST), `/api/dashboard` (stub) |
| `arbitrage.py` | Règle d'arbitrage + 5 niveaux officiels |
| `champs.py` | Champs de saisie par catégorie (moteur générique) |
| `mailer.py` | Notifications email best-effort (2.7) |
| `seed_demo.py` | Jeu de démo : 4 compétitions (M15, Vétérans, Individuel, M20) + tokens |
| `templates/confirmation.html` | Page de confirmation (générique, pilotée par l'API) |
| `static/arbitres.js` | Composant arbitres réutilisable |
| `tests/` | `test_schema.py`, `test_confirm.py`, `test_mailer.py` — 21 tests |

## Décisions clés (à respecter)
1. **SQLite** (pas PostgreSQL) — optimal pour la ligue, migrable plus tard.
2. **Auth = lien magique** par couple (club, compétition) : `confirmation.token`, sans mot de passe.
3. **Cloisonnement serveur** : un club ne confirme QUE ses tireurs. Le POST rejette (403) toute écriture sur un `qualifie` d'un autre club — jamais se fier au front. (mémoire : `plateforme-cloisonnement-clubs`)
4. **Moteur générique** : `champs.py` décide des champs par tireur selon la catégorie — M15→veste, Vétérans→catégorie d'âge (V1-V2/V3-V4), autres→présence seule. Le template, l'API et la validation s'adaptent. Une seule page pour les 4 types.
5. **Niveaux d'arbitre** (5) : `regional_formation, regional, national_formation, national, international` (corrigé — PAS D/C/B/A/N/NN).
6. **Règle arbitrage** : standard = seuils 4/9 plafond 2 ; master = 1 dès 1 tireur ; none = 0.
7. **Emails** : best-effort (panne SMTP n'échoue jamais une confirmation). Destinataires via `NOTIF_RECIPIENTS`. Test : atrcrege@gmail.com + thomas.ducourant@gmail.com. Prod : administration@crege.fr. (mémoire : `plateforme-emails-destinataires`)

## Endpoints
- `GET /c/<token>` → page HTML de confirmation.
- `GET /api/c/<token>` → données scoped : compétition (+`champs`), qualifiés (`mine` true/false), bloc arbitrage, saisie existante.
- `POST /api/confirm/<token>` → enregistre présences + arbitres (idempotent), valide champs requis + niveaux, **403 hors périmètre**, notifie le secrétariat.
- `GET /api/dashboard` → **stub à implémenter en 3.1**.

## Lancer / tester
```bash
pip install -r requirements.txt
python migrate.py && python seed_demo.py    # imprime les liens /c/<token>
python app.py                               # http://127.0.0.1:5002/c/tok-chalons
python -m pytest tests/ -q                  # 21 tests
```
Tokens de démo : `tok-chalons`, `tok-romari` (M15), `tok-vet-chalons` (Vétérans), `tok-indiv-chalons` (Individuel), `tok-m20-chalons` (M20).

## Phase 3 — à faire (NOUVEAU FIL)
**3.1 Dashboard secrétariat** (`/api/dashboard` + page) :
- Vue par compétition : clubs **confirmés / en attente**, progression (X/Y clubs), nb tireurs confirmés, nb arbitres.
- Détail par club, accès aux saisies.
- **Exports** (CSV/Excel des participations confirmées) — à cadrer (format attendu par le secrétariat ?).
- Accès dashboard : à protéger (le dashboard n'est pas cloisonné — c'est la vue secrétariat globale). Décider l'auth secrétariat (lien admin ? mot de passe ?).
- Rappel : Clément veut un **accès dashboard permanent** → une fois en place, réduire les emails à `atrcrege@gmail.com` seul.

**3.2 Rappels automatiques** : cron J-10 / J-7 / J-3 avant `date_limite`, emails de relance aux clubs **non confirmés**. Réutilise `mailer.py`.

## Pièges techniques
- **Le mount bash tronque les gros fichiers fraîchement édités** → vérifier via miroir `/tmp` (réinjecter les fichiers édités depuis la lecture disque) ou via le rendu Flask. Les fichiers sur le disque Windows sont corrects.
- Purger les `__pycache__` avant pytest.
- SelecGE : lancer `python audit.py` en local (régression génération non testable en sandbox).

## Normes de travail
1 session = 1 tâche atomique · exécuter avec vraies données avant livraison · incertitude signalée avant livraison · 1 bug = 1 test · résumé 3 lignes max · pas de PostgreSQL (SQLite).
