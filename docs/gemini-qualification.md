# Gemini via OmniRoute pour la qualification MENTOR

L'utilisateur a retenu Gemini puis autorisé la création d'une clé OmniRoute
dédiée. Le profil qual passe désormais par **l'instance OmniRoute existante** ;
les clés Google restent gérées par celle-ci et ne sont pas copiées dans MENTOR.
Le connecteur Gemini natif reste disponible et testé indépendamment du profil.

## Configuration préparée

`k8s/overlays/qual/model.yaml` fournit les paramètres publics :

| Paramètre | Valeur |
|---|---|
| `LLM_PROVIDER` | `custom` (connecteur OpenAI compatible existant) |
| `CUSTOM_LLM_BASE_URL` | `http://omniroute.omniroute.svc.cluster.local/v1` |
| `CUSTOM_LLM_MODEL` | `gemini/gemini-3.1-flash-lite` |
| Clé côté MENTOR | Secret `mentor-model-credentials`, champ `CUSTOM_LLM_API_KEY` |

L'endpoint interne et le port de pod 20128 ont été constatés dans le cluster.
La route vient du catalogue **synchronisé de la connexion Gemini**, consulté
via son API de gestion, et utilise un modèle
[stable documenté par Google](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite).
La liste générale d'OmniRoute annonçait aussi `gemini/gemini-3.7-flash`, mais
celle-ci était refusée à la génération car absente du catalogue synchronisé.
Aucun catalogue partagé ni compte fournisseur n'a été modifié pour contourner
ce refus. Vérifier les deux catalogues lors d'un changement de modèle.

## Clé dédiée réellement créée

La clé `mentor-qualification` a été créée par l'API de gestion locale officielle
d'OmniRoute 3.8.50, avec l'autorisation explicite de l'utilisateur. Elle est
conservée, sans affichage ni fichier local de clé, dans le Secret
**`omniroute/mentor-qualification-client`**, champ `CUSTOM_LLM_API_KEY`.
Les annotations indiquent l'identifiant de gestion, le modèle et l'expiration.
Ce Secret est une réserve opérateur ; aucune Application ni namespace MENTOR
n'a été créé pour le consommer.

Restrictions relues après création : connexion Gemini dédiée uniquement,
modèle explicite, aucun combo, aucun droit d'administration, scope
`self:usage`, expiration sept jours après création. Pour cette clé seulement,
`noLog=true`, cache en mode bypass et compression désactivée. Ces réglages ne
modifient pas les autres clés. Ils ne constituent pas une garantie générale
de non-conservation de données chez le fournisseur.

Avant toute mutation, l'API a confirmé `cloudConfigured=false` et l'absence de
destination cloud, malgré le drapeau `cloudEnabled=true`. Le code installé
retourne sans synchroniser lorsqu'aucune destination n'est configurée. Ne pas
activer une destination cloud sans revue : la synchronisation de cette version
inclut les clés et les credentials fournisseurs. Aucun réglage cloud n'a été
modifié. Référence du code examiné :
[OmniRoute, révision 0915890](https://github.com/diegosouzapw/OmniRoute/tree/091589089cd134a94df9f6cdab9ba562b2cefd18).
Aucun code OmniRoute n'est copié dans MENTOR et aucune dépendance n'est ajoutée.

Après autorisation du déploiement, l'opérateur devra fournir cette clé au Secret
`mentor-qual/mentor-model-credentials` par la procédure de secrets retenue,
sans la copier dans Git, la description de PR ou le terminal. Cette propagation
n'est pas encore effectuée. Renouveler la clé avant son expiration par la même
procédure ; ne pas réutiliser une clé d'administration ou un compte tiers.

## Réseau et santé

L'overlay autorise uniquement les pods API MENTOR à joindre les pods
`app=omniroute` du namespace `omniroute`, TCP/20128. Le namespaceSelector et le
podSelector sont dans le même peer (ET). Le port 80 du Service est traduit vers
20128 ; la politique cible le port du pod. Les autres sorties restent limitées
à DNS et PostgreSQL IONOS. Aucune sortie directe Google ni permission générale
Internet n'est ajoutée ; aucune politique n'a été appliquée au cluster par ce lot.

La sonde du connecteur custom utilise maintenant la même authentification
Bearer que la génération. Elle exige le modèle exact dans `/v1/models`,
limite la durée globale à cinq secondes et désactive les retries. Le connecteur
Gemini natif conserve sa vérification authentifiée de métadonnées du modèle.
Les diagnostics ne publient que des catégories, jamais les corps d'erreur.

**Le catalogue ne prouve pas la disponibilité de la génération en amont.**
Le décalage constaté sur Gemini 3.7 le démontre. Une preuve de génération réelle
et le parcours métier depuis le déploiement restent indispensables, en plus
des probes. Ne pas donner de droit de gestion à la clé applicative pour lire
le catalogue administrateur.

## Vérifications

```sh
ENVIRONMENT=development DATABASE_URL=sqlite+aiosqlite:////tmp/mentor-local-tests.db \
python -m pytest tests/test_omniroute_qualification.py \
  tests/test_gemini_qualification.py tests/test_argocd_qualification.py \
  -q -o addopts= --timeout=30
```

Ces tests utilisent le vrai SDK sur un transport HTTP en mémoire : Bearer,
modèle, refus et reprise, QCM, SSE et rendu réseau. Les vérifications réelles
sur la clé créée ont constaté : catalogue 200, accès anonyme 401,
administration 403 et autre modèle 403. Les résultats de génération synthétique
sont consignés dans [le rapport daté](validation-2026-10-25.md).

La génération réelle reste **non validée** : refus 400 pour la route statique
Gemini 3.7 absente du catalogue synchronisé, réponses 503 puis 504 sur le chemin
Gemini 3.1 Flash-Lite, et refus 404 pour Gemini 2.5 Flash. Après ces essais, la clé
et le profil restent limités à Gemini 3.1 Flash-Lite. Aucun succès de génération
n'est déduit du catalogue 200. Seules des phrases synthétiques publiques ont
été utilisées ; aucun document utilisateur n'a été envoyé. Aucun rafraîchissement
forcé du catalogue partagé ni changement de compte fournisseur n'a été effectué.

Gemini est ici le fournisseur de **génération**. Le moteur d'embeddings hérité
n'a pas d'intégration Gemini/OmniRoute ; sans autre fournisseur compatible,
son mode auto utilise le repli sans embeddings. Les tests pgvector prouvent
le stockage et les opérations vectorielles, pas la génération d'embeddings.
Le choix/dimension du modèle d'embeddings reste distinct.

Ce travail ne constitue pas la qualification Kubernetes complète. Celle-ci
reste soumise aux [conditions de promotion](production-readiness.md), aux
images publiées et au runner CI isolé actuellement manquant.
