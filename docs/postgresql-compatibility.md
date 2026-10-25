# Préparation du dialecte PostgreSQL — en expérimentation

Cette branche est une **étape technique**, pas une prise en charge opérationnelle de PostgreSQL.

## Modifications proposées

- `DATABASE_URL=postgresql+asyncpg://...` autorisé explicitement.
- Colonnes UUID compatibles natif PostgreSQL, texte sous SQLite.
- Mapping JSON → JSONB et TEXT → TSVECTOR sur PostgreSQL.
- Vecteurs SQLite stockés en JSON texte ; vecteurs PostgreSQL stockés en `VECTOR(1536)` via pgvector.
- Dépendances optionnelles isolées dans `apps/api/requirements-postgres.txt`.
- Tests de compilation des types et de sérialisation SQLite, sans prétendre valider une vraie base PostgreSQL.

## Blocages à résoudre avant activation Kubernetes

1. **Schéma initial** : les migrations Alembic amont semblent incrémentales ; il faut établir une migration baseline complète et une stratégie de conversion des données.
2. **Extension** : `CREATE EXTENSION vector` doit être disponible sur le cluster PostgreSQL, avec droits adaptés.
3. **Recherche** : les colonnes `TSVECTOR` exigent une stratégie `to_tsvector` (langue/configuration), des index GIN et une validation des requêtes, pas un simple changement de type.
4. **Embeddings** : la dimension 1536 est héritée de l'amont. Le modèle d'embeddings choisi doit être compatible, ou le schéma doit devenir configuré par modèle.
5. **Sécurité** : connexion TLS, secrets et RBAC. Pas d'ouverture réseau automatique.
6. **Validation** : tests unitaires + intégration réelle dans un PostgreSQL isolé, migration avant/après, contrôle de perte de données, sauvegarde/restauration.

Ne pas fusionner sans les gates ci-dessus et sans vert complet de la baseline OpenTutor.
