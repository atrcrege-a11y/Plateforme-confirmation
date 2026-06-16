# Passation — Plateforme Confirmation LREGE
*MAJ : 2026-06-16 — fin de Phase 1*

## Contexte projet
- **Objectif** : plateforme de confirmation des participations (clubs confirment tireurs/équipes + arbitres).
- **Deadline globale** : 30 sept. 2026, go-live octobre.
- **Dépôt** : `C:\Users\ATR EGE\Desktop\LREGE` (git). Modules : SelecGE, SelecMaster, EscriTools, CalendrierLREGE, SYNESC…
- **Phase 1** = refonte SelecGE (gestion arbitres) → **TERMINÉE**. Bloquait la Phase 2.

## Décisions métier confirmées (→ REGLES.md §5, ligne 8 + notes Specs 10.1/10.2)
- **SelecGE n'a pas de BD.** Config = JSON disque (`config_selection.json`), données = cache pickle. La couche SQLAlchemy/Alembic du spec 10.1 **ne s'applique pas** — on a étendu le dict `arbitrage_config`.
- **Règle arbitrage** (les formules du spec étaient buguées) :
  - `none` → 0 arbitre, toujours.
  - `standard` → seuils 4/9 plafonné à 2 : `<4`→0, `4-8`→1, `≥9`→2. Seuils configurables (`seuil1`/`seuil2`).
  - `master` → 1 arbitre dès 1 tireur, sans contrainte au-delà (constant 1).
- **« Pas d'arbitre requis » toujours possible** : via `type_arbitrage="none"` OU `arbitres_requis=False` (prioritaire, force 0).

## Phase 1 — livré
| Tâche | État | Fichiers |
|---|---|---|
| 1.1 champs arbitres + règle calcul | ✓ | `crege_app/core/arbitrage.py` (enum `TypeArbitrage`, `calculer_arbitres_requis`, `normaliser_arbitrage_config`, `arbitres_nombre`) |
| 1.2 UI dropdown type_arbitrage | ✓ | `templates/index.html` (select `fArbType`, `updateArbType`, `buildArbConfig`, `buildArbTexte`, restauration) |
| 1.3 saisie arbitres | → reportée **2.2b** (Phase 2, plateforme) | — |
| 1.4 export JSON | ✓ | `crege_app/core/arbitrage.py` (`export_arbitrage_json`, `regle_texte`) + endpoint `GET\|POST /api/export/arbitrage` dans `routes/misc.py` |
| 1.5 tests | ✓ 35/35 | `tests/test_arbitrage.py` (10 cas) |

Contrat export (Specs 10.2) : `{arbitres_requis, type_arbitrage, source, seuils:{seuil1,seuil2}, arbitres_nombre, regle}`. `arbitres_nombre=null` tant que le nb de tireurs engagés est inconnu (param `tireurs` optionnel).

## À FAIRE avant de clore la Phase 1 (action utilisateur)
- [ ] **`python audit.py` en local** (dans `SelecGE/`) — la régression génération (étapes 1-2, vraies données FFE) n'a pas pu tourner dans le sandbox (PDF FFE absents). Étape 0 (intégrité) OK. Risque faible : `feuille.py` non modifié.

## Pièges techniques (à savoir)
- **Le mount bash tronque les gros fichiers fraîchement édités.** Lectures `grep`/`cat`/`pytest` côté sandbox peuvent voir une version partielle/ancienne → faux SyntaxError, tests périmés. **Vérifier hors mount** : miroir `/tmp` + réinjection des fichiers édités (via Read disque), ou rendu Flask. Le fichier sur le disque Windows est, lui, correct.
- Purger les `__pycache__` avant pytest (bytecode périmé avec assertion-rewrite).

## Phase 2 — prochaine étape (NOUVEAU FIL)
**2.1 — Backend : Setup + BD** (3h, Specs 8). C'est un changement d'archi majeur, **distinct de SelecGE** : PostgreSQL, migrations, API skeleton Flask.
À préciser avant de coder :
1. Périmètre exact de la plateforme de confirmation.
2. **Schéma de données** : le payload complet de la sélection (clubs/tireurs/équipes qualifiés) reste à définir — 1.4 n'a couvert que le bloc arbitrage.
3. Confirmer choix techno (PostgreSQL vs SQLite) et hébergement (VPS OVH, tâche 5.1).

Suite des tâches Phase 2 : 2.1 → 2.2 (API /confirm,/dashboard) → 2.2b (composant saisie arbitres) → 2.3 M15 → 2.4 Vétérans → 2.5 Individuels → 2.6 M17/M20/Sénior ; 2.7 emails (dépend 2.2).

## Normes de travail (rappel)
1 session = 1 tâche atomique · exécuter avec vraies données avant livraison · diagnostic avant correction · incertitude signalée avant livraison · 1 bug corrigé = 1 test ajouté · résumé livraison 3 lignes max.
