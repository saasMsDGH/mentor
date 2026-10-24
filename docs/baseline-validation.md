# Baseline technique OpenTutor → MENTOR

Date d'observation : 2026-10-25 (Europe/Paris)

## Provenance et périmètre

- Dépôt amont : `zijinz456/OpenTutor`.
- Révision importée et gelée : `2d2c003654cfbc90c173c9db6867ae65a65e8313`.
- Licence conservée : MIT ; document source sous `docs/upstream/opentutor/`.
- Dépôt cible : `saasMsDGH/mentor`, branche `feature/import-opentutor`.
- 897 fichiers vérifiés immédiatement après l'import, dont 666 sous `apps/` et 94 sous `tests/`.
- Import effectué par le workflow `Import OpenTutor pinned baseline` : https://github.com/saasMsDGH/mentor/actions/runs/40137368628 (succès).
- Les workflows amont n'ont pas été activés automatiquement ; seuls les workflows MENTOR sont exécutables.

## CI et premières découvertes

- Workflow CI MENTOR : `.github/workflows/ci.yml`, exécution sans secrets d'application et avec accès GitHub en lecture.
- CI `40137504308` : erreur ESLint initiale sur `timeline-view.tsx` (constante inutilisée, setState dans un effet).
- Correction MENTOR : gestion asynchrone des objectifs avec annulation logique à la désactivation du composant, préservation des objectifs du bon parcours et état d'erreur visible.
- CI `40137654421` : lint et **216 tests frontend** réussis, puis échec du build sur `setup/template-step.tsx` (bloc `summary` manquant dans `Record<BlockType, Icon>`).
- Correction MENTOR : entrée `summary` ajoutée dans les icônes, le registre des types persistants et les tailles par défaut, avec test de non-régression dans `layout-storage.test.ts`.
- **La réussite du build et la suite Python restent à confirmer par les validations du dernier commit.** Ne pas marquer P0 comme terminé avant une CI verte.

Lien vers les exécutions : https://github.com/saasMsDGH/mentor/actions

## Limites de l'environnement importé

- Produit bêta orienté mono-utilisateur local ; accès réseau multi-utilisateur non qualifié.
- Docker Compose amont : `AUTH_ENABLED=false` par défaut, montage Docker socket dans l'API. Ne pas déployer tel quel sur Kubernetes ni exposer sur Internet.
- `config.py` rejette une URL PostgreSQL. `models/compat.py` utilise des types SQLite pour UUID/JSON/vector.
- `alembic/env.py` saute les migrations SQLite : un `alembic upgrade head` réussi sur SQLite ne valide **pas** les migrations PostgreSQL.
- Les algorithmes BKT, FSRS, LOOM et LECTOR doivent être validés sur un jeu d'essais pédagogiques et non simplement sur les tests unitaires existants.

## Critères de sortie de la baseline

1. CI Python : dépendances installées, sources compilées, tests et couverture documentés.
2. CI frontend : ESLint, Vitest et `next build` réussis.
3. Tests API de bout en bout utilisant un LLM simulé : importer un document, générer du contenu, lancer un quiz et conserver la progression.
4. Audit des restrictions d'authentification, de stockage, du sandbox et des dépendances.
5. Refus de toute exposition réseau avant la résolution des obstacles sécurité et persistance.

La PR #8 reste **brouillon** tant que ces conditions ne sont pas satisfaites.
