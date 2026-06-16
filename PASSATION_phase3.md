# Passation — Phase 3 → suite
*MAJ : 2026-06-16 — Phase 3 terminée (dashboard secrétariat + export Excel + rappels auto). 29/29 tests verts.*

## Où on en est
- **Phase 1** (SelecGE arbitres) : terminée.
- **Phase 2** (plateforme confirmation) : terminée.
- **Phase 3** (dashboard + rappels) : **terminée**.
  - 3.1 dashboard secrétariat + export .xlsx — fait.
  - 3.2 rappels automatiques J-10/J-7/J-3 — fait.

## Ce qui a été ajouté en phase 3
| Fichier | Rôle |
|---|---|
| `dashboard.py` | Logique : `admin_token()`/`is_admin()`, `agreger(conn)` (agrégat par compétition + détail club), `participations_export()`, `construire_xlsx()` (openpyxl) |
| `routes/dashboard.py` | Blueprint : `/dashboard/<token>` (page), `/api/dashboard/<token>` (JSON), `/api/dashboard/<token>/export/<comp_id>` (.xlsx) |
| `templates/dashboard.html` | Page dashboard (charte identique à la page club) |
| `rappels.py` | `clubs_a_relancer(conn, today)`, `envoyer_rappels()`, CLI cron |
| `mailer.py` | + `construire_rappel()`, `notifier_rappel_club()`, refactor `_envoyer()` commun |
| `tests/test_dashboard.py` | auth admin, agrégat non cloisonné, export xlsx (3 tests) |
| `tests/test_rappels.py` | fenêtre J-10/7/3, exclusion confirmés, dry-run (5 tests) |

## Décisions phase 3 (à respecter)
1. **Auth dashboard = token admin permanent** (env `ADMIN_TOKEN`, défaut dev `admin-local`). Une seule personne (Clément). `/dashboard/<token>`. Token invalide → **404** (ne révèle pas l'existence du dashboard). NON cloisonné : vue globale toutes compétitions/clubs.
2. **Export = Excel (.xlsx)** via openpyxl (ajouté à `requirements.txt`). 2 feuilles : Tireurs (club, équipe, section, nom, prénom, présent, veste, cat. d'âge) + Arbitres. Seules les confirmations `confirmee` sont exportées.
3. **Rappels** : relance envoyée **au club** (pas au secrétariat) quand `date_limite` tombe exactement à J-10/J-7/J-3 et statut `en_attente`. Contient le lien magique `/c/<token>`. Best-effort (mailer). Lien construit via env `BASE_URL` (défaut `http://127.0.0.1:5002`).

## Lancer / tester
```bash
pip install -r requirements.txt
python migrate.py && python seed_demo.py
ADMIN_TOKEN=clement-2026 python app.py     # dashboard : /dashboard/clement-2026
python rappels.py                          # relances du jour (cron 1×/jour)
python -m pytest tests/ -q                 # 29 tests
```

## À faire (prod / suite)
- **Définir `ADMIN_TOKEN` en prod** (valeur secrète, non `admin-local`). Donner l'URL `/dashboard/<token>` à Clément (accès permanent).
- **Réduire les emails à `atrcrege@gmail.com`** une fois le dashboard adopté : `NOTIF_RECIPIENTS="atrcrege@gmail.com"` (cf. mémoire `plateforme-emails-destinataires`).
- **Planifier le cron** `python rappels.py` (1×/jour) + définir `BASE_URL` sur l'URL publique.
- Config SMTP réelle (`SMTP_HOST`…) pour sortir du dry-run.

## Pièges techniques (rappel)
- **Le mount bash tronque les fichiers anciens/édités** (cache périmé, non rafraîchi même en réécrivant). Vérifier/tester via miroir `/tmp` reconstruit depuis la lecture disque (le disque Windows est correct). Confirmé cette session sur 7 fichiers.
- Purger les `__pycache__` avant pytest.

## Normes de travail
1 session = 1 tâche · exécuter avec vraies données avant livraison · incertitude signalée avant livraison · 1 bug = 1 test · résumé 3 lignes max · SQLite (pas PostgreSQL).
