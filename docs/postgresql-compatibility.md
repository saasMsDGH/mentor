# Préparation du dialecte PostgreSQL — en expérimentation

Cette branche est une **étape technique**, pas une prise en charge opérationnelle de PostgreSQL.

## Modifications proposées

- `DATABASE_URL=postgresql+asyncpg://...` autorisé explicitement.
- Colonnes UUID compatibles natif PostgreSQL, texte sous SQLite.
- Mapping JSON → JSONB et TEXT → TSVECTOR sur PostgreSQL.
- Vecteurs SQLite stockés en JSON texte ; vecteurs PostgreSQL stockés en `VECTOR(1536)` via pgvector.
- Dépendances optionnelles isolées dans `apps/api/requirements-postgres.txt`.
- Tests de compilation des types et de sérialisation SQLite, sans prétendre valider une vraie base PostgreSQL.

## Blocages identifiés au stade du prototype #9

1. **Schéma initial** : les migrations Alembic amont semblent incrémentales ; il faut établir une migration baseline complète et une stratégie de conversion des données.
2. **Extension** : `CREATE EXTENSION vector` doit être disponible sur le cluster PostgreSQL, avec droits adaptés.
3. **Recherche** : les colonnes `TSVECTOR` exigent une stratégie `to_tsvector` (langue/configuration), des index GIN et une validation des requêtes, pas un simple changement de type.
4. **Embeddings** : la dimension 1536 est héritée de l'amont. Le modèle d'embeddings choisi doit être compatible, ou le schéma doit devenir configuré par modèle.
5. **Sécurité** : connexion TLS, secrets et RBAC. Pas d'ouverture réseau automatique.
6. **Validation** : tests unitaires + intégration réelle dans un PostgreSQL isolé, migration avant/après, contrôle de perte de données, sauvegarde/restauration.

Le candidat consolidé ci-dessous traite le schéma neuf et sa validation locale.
Les garanties de production restent soumises aux conditions de promotion.

## Validation ajoutée après la PR #9

La branche `fix/postgresql-validation` reprend les corrections de tests du socle
sans fusionner les PR. Le filtre de branches CI couvre désormais aussi
`wip/postgresql-*`. La CI installe le profil PostgreSQL afin que les assertions
pgvector ne soient plus ignorées faute de dépendance.

Les tests compilent toutes les tables et tous les index ORM pour le dialecte
PostgreSQL, puis exercent les véritables processeurs de paramètres/résultats
SQLAlchemy de pgvector. Le type MENTOR vérifie explicitement dimension et
valeurs finies avant l'envoi à PostgreSQL ; la sérialisation SQLite historique
est conservée. Ce contrôle ne dépend pas d'une validation implicite du pilote.

```sh
python -m pip install -r apps/api/requirements-postgres.txt
ENVIRONMENT=development DATABASE_URL=sqlite+aiosqlite:////tmp/mentor-tests.db \
python -m pytest tests/test_postgres_dialect.py -q -o addopts= --timeout=30
```

**Aucune base PostgreSQL réelle n'est contactée par ces tests.** Compiler un
schéma ORM ne prouve ni son application, ni le fonctionnement des requêtes de
recherche ou des migrations Alembic. La première révision Alembic vérifie une
table déjà existante : une baseline complète et figée reste à construire.
Ne pas remplacer les migrations par `create_all()` dans un déploiement.

## Candidat consolidé : migration PostgreSQL réellement testée

La branche `feature/production-candidate` réunit les lots pédagogie et
qualification. Elle ajoute un historique Alembic PostgreSQL distinct, figé,
pour **une base neuve uniquement** :

```sh
cd apps/api
alembic -c alembic-postgres.ini upgrade head
```

L'extension `vector` doit être provisionnée au préalable par l'opérateur de
base. La migration applicative ne réclame pas de droits superutilisateur.
La chaîne incrémentale OpenTutor reste conservée dans `alembic.ini` ; elle ne
sert pas de baseline PostgreSQL. Aucune adoption automatique d'une ancienne
base PostgreSQL ni conversion des données SQLite n'est fournie par ce lot.

La baseline `mentor_pg_0001` crée les 33 tables ORM, leurs contraintes/index,
les types UUID/JSONB/TSVECTOR/vector, les index GIN et HNSW. Les scripts restent
indépendants des modèles futurs. L'API refuse `create_all()` sous PostgreSQL et
ne tamponne pas un schéma au démarrage. Les probes vérifient les tables
attendues et la révision Alembic réelle ; un modèle indisponible ou dégradé
maintient la readiness fermée.

Validation locale reproductible :

```sh
python -m pip install -r apps/api/requirements-postgres.txt
python scripts/test_postgres.py
```

Le contrôleur utilise l'image pgvector/PostgreSQL 18 identifiée par son
digest dans le script. Il crée un conteneur jetable, sans réseau ni port publié,
et un socket Unix temporaire. Il génère les mots de passe sans les afficher,
sépare un rôle de migration et un rôle applicatif DML, exécute les migrations
aller/retour et les mêmes tests document→QCM→FSRS sur la vraie base.
Il teste UUID/JSONB/vector, requêtes vectorielles et plein texte, GIN/HNSW,
readiness et refus d'une révision incomplète. Enfin, un `pg_dump` est restauré
dans une seconde base jetable : les empreintes et nombres de lignes des
34 tables, version Alembic comprise, sont comparés. Les données sources sont
uniquement les fixtures de test, jamais une base existante.

Ces tests ne prouvent pas la restauration des fichiers uploadés ni du stockage
objet, l'isolation réseau du cluster, une migration de données existantes ou la
performance d'un corpus réel. Les requêtes RAG héritées utilisent encore leur
repli générique ; la présence des index ne signifie pas qu'elles les exploitent
toutes. Le `downgrade base` testé détruit les tables de la base jetable : ce
n'est pas une procédure de retour arrière autorisée pour une production.
