# Validation constatée le 25 octobre 2026

## Point de départ GitHub

- PR #8, commit `83a15929219e3bcd53aebbc332b56bf08da97c35`,
  [run 40209338922](https://github.com/saasMsDGH/mentor/actions/runs/40209338922) :
  frontend et provenance réussis ; backend : 1 échec, 976 réussites, 5 ignorés.
- PR #10, commit `c39453d3b0917c7e441afe357b9c5f9545bc4875`,
  [run 40209546413](https://github.com/saasMsDGH/mentor/actions/runs/40209546413) :
  même test HTML en échec ; 977 réussites, 5 ignorés ; frontend et provenance réussis.
- PR #9, commit `05d6848d0847b4947e8ed5296e91aabe7c801e0b` : aucun contrôle
  renvoyé pour ce commit. Le filtre CI omettait les branches `wip/postgresql-*`.
- Les jobs examinés ont les labels `[self-hosted, k8s-deploy]` et le runner
  `org-runner-subst`. Aucun runner GitHub hébergé n'a été utilisé par nos changements.

## Résultats locaux des branches dédiées

Python 3.11.14, environnement virtuel du dépôt ; backend SQLite isolé, profil
`requirements-ci.txt`, puis `requirements-postgres.txt` pour les deux derniers lots.
Les suites complètes conservent le seuil de couverture existant de 45 %.

| Branche | Validation | Résultat |
|---|---|---|
| `fix/baseline-url-title` | suite backend hors lifecycle SQLite | 977 réussis, 5 ignorés ; couverture 49,28 % |
| `fix/baseline-url-title` | lifecycle SQLite séparé | 6 réussis |
| `fix/ci-learning-loop` | suite backend hors lifecycle SQLite | 979 réussis, 5 ignorés ; couverture 49,57 % |
| `fix/ci-learning-loop` | parcours API isolé, réseau IP bloqué | 2 réussis |
| `fix/postgresql-validation` | suite backend hors lifecycle SQLite | 987 réussis, 5 ignorés ; couverture 49,36 % |
| `fix/postgresql-validation` | dialecte + pgvector, sans base réelle | 10 réussis ; 33 tables et 30 index compilés |
| `fix/postgresql-validation` | lifecycle SQLite séparé | 6 réussis |
| `feature/kubernetes-qualification-prep` | suite backend hors lifecycle SQLite | 992 réussis, 5 ignorés ; couverture 49,36 % |
| `feature/kubernetes-qualification-prep` | contrats Kubernetes statiques | 5 réussis |
| `feature/kubernetes-qualification-prep` | rendu local Kustomize | 10 ressources, namespace vérifié, aucun serveur contacté |

Deux avertissements Python restent dans les suites complètes, sans échec.
Le run intermédiaire [40211559844](https://github.com/saasMsDGH/mentor/actions/runs/40211559844)
a révélé un échec supplémentaire : `next/font/google` expirait lors du téléchargement
de Space Grotesk depuis Google Fonts. Le correctif `6da81fa`, reporté sur les
quatre branches, embarque la police à une révision figée et sa licence OFL 1.1
(voir `apps/web/src/app/fonts/README.md`). La notice est distribuée dans `public/`
et les empreintes sont contrôlées en CI.

Après ce correctif, validation frontend locale : **217 tests réussis**, lint
sans erreur (un avertissement existant dans `timeline-view.tsx`), build Next.js
et TypeScript réussis avec accès réseau restreint. Les dépendances verrouillées
ont été installées au préalable ; ce résultat ne prétend pas qu'une installation
npm à froid fonctionne sans accès au registre.

Lors du contrôle distant ultérieur du 25 octobre, les quatre exécutions corrigées
sont terminées avec le résultat `success` :

- socle : [40212485194](https://github.com/saasMsDGH/mentor/actions/runs/40212485194), commit `6da81fa` ;
- boucle pédagogique : [40212496352](https://github.com/saasMsDGH/mentor/actions/runs/40212496352), commit `a67ea27` ;
- dialecte PostgreSQL : [40212498463](https://github.com/saasMsDGH/mentor/actions/runs/40212498463), commit `d436bbd` ;
- préparation Kubernetes : [40212500437](https://github.com/saasMsDGH/mentor/actions/runs/40212500437), commit `807eb47`.

Ces résultats concernent les commits cités, pas une qualification Kubernetes ou
Argo CD. Les changements documentaires ultérieurs ne constituent pas une
validation de déploiement. Le test pédagogique a également été revalidé après interdiction
explicite des résolutions DNS : 2 réussites.

Commandes utilisées (variables réservées aux tests locaux, pas à un déploiement) :

```sh
ENVIRONMENT=development DATABASE_URL=sqlite+aiosqlite:////tmp/mentor-local-tests.db \
CODE_SANDBOX_BACKEND=process python -m pytest tests/ -q \
--ignore=tests/test_sqlite_mode.py --timeout=60
ENVIRONMENT=development DATABASE_URL=sqlite+aiosqlite:////tmp/mentor-local-tests.db \
CODE_SANDBOX_BACKEND=process python -m pytest tests/test_sqlite_mode.py \
-q -o addopts= --timeout=60
kubectl kustomize deploy/kubernetes/base
```

## Limites des quatre lots initiaux

Aucune fusion, aucun déploiement, aucune connexion au cluster et aucune base
PostgreSQL réelle. La licence MIT et le copyright OpenTutor restent présents ; la police
Space Grotesk ajoute sa propre notice SIL OFL 1.1 conservée ;
aucun code d'un autre projet de référence n'a été importé. Un audit exhaustif
des licences des dépendances n'a pas été réalisé.

Le test pédagogique utilise un fournisseur simulé et bloque les connexions IP ;
les suites amont n'ont pas une garantie générale d'exécution hors réseau
(tiktoken télécharge ses données à froid). Le socle Kubernetes refuse les flux
non explicitement autorisés et conserve zéro replica ; il ne prouve pas
l'isolation effective d'un cluster sans validation du CNI.

Séparer les runners CI éphémères sans droits cluster des runners de déploiement
protégés. Le label `k8s-deploy` est conservé dans ces branches conformément au
runner actuellement disponible ; aucun réglage de l'organisation n'a été modifié.

## Candidat consolidé #15 et accès rétablis

Ces observations ultérieures remplacent les limites d'accès et de PostgreSQL
des lots initiaux, sans constituer une qualification du déploiement :

- `a9a763f`, [run 40223763535](https://github.com/saasMsDGH/mentor/actions/runs/40223763535) :
  **999 tests backend réussis, 8 ignorés**, couverture **49,71 %** ;
  **6 tests SQLite réussis**. L'étape PostgreSQL Docker échoue car
  `/var/run/docker.sock` n'existe pas sur `org-runner-subst`.
- Sur ce même run, **221 tests frontend**, lint et build réussissent, ainsi
  que le contrôle de provenance. Le job images est ignoré par dépendance au
  backend en échec ; il n'a pas validé les images à distance.
- Après ajout des contrats Argo CD, suite backend locale finale :
  **1 018 réussis, 8 ignorés**, couverture **49,71 %**.
- Localement : **5 tests PostgreSQL réels réussis**, migration/downgrade/
  réapplication, types et index, parcours pédagogique avec IA simulée et
  restauration comparant les données des **34 tables**.
- Images API/web construites sans réseau de build ; essai sur réseau interne
  sans port publié, racines en lecture seule, identités non root, proxy même
  origine, accès anonyme refusé et notices distribuées vérifiés. Readiness
  **503 attendue** en l'absence de modèle autorisé.
- Accès `pkubs` et SSH IONOS rétablis en lecture seule. Versions et blocages
  vivants consignés dans [production-readiness](production-readiness.md).
- Contrats Argo CD locaux : **19 tests réussis**, dont rejet des preuves de
  rollout périmées/incomplètes et rendu des overlays qual/prod. Dry-run
  serveur Namespace/AppProject/Application accepté, sans ressources créées.

Aucune fusion, publication d'image, synchronisation Argo CD ni modification
de base distante n'a été effectuée. Les résultats locaux ne rendent pas verte
la qualification runtime distante bloquée par le runner.
