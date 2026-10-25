# Gemini pour la qualification MENTOR

Choix utilisateur du 25 octobre 2026 : **Gemini**. En l'absence de précision sur
le routage, le profil qual prépare l'accès Google natif déjà pris en charge par
OpenTutor. Il ne passe pas par OmniRoute et n'ajoute pas de fournisseur de
repli. Aucun appel Google réel ni document n'a été envoyé par ce lot.

## Configuration préparée

`k8s/overlays/qual/model.yaml` contient uniquement les paramètres publics :
`LLM_PROVIDER=gemini` et `LLM_MODEL=gemini-3.8-flash`. Cette version stable est
le choix proposé pour le candidat, à vérifier avec le compte prévu ; le modèle
ne dépend pas des valeurs par défaut historiques de l'application.

L'API utilise le SDK OpenAI existant et l'endpoint
`https://generativelanguage.googleapis.com/v1beta/openai/`.
La clé est lue depuis le Secret opérateur
`mentor-model-credentials`, champ `GEMINI_API_KEY`. Ce Secret n'est ni généré
ni stocké dans Git. Ne pas mettre une clé Google dans `OPENAI_API_KEY` ou
réutiliser une clé du routeur OmniRoute. Aucun accès navigateur à cette clé
n'est nécessaire ; seul le conteneur API la reçoit.

Références officielles consultées :
[compatibilité OpenAI, génération/streaming et métadonnées de modèle](https://ai.google.dev/gemini-api/docs/openai),
[modèle stable Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).
Leur description est utilisée pour les contrats HTTP ; aucun code d'exemple
Google ni nouvelle bibliothèque n'est importé dans le projet.

## Readiness réellement probante

Le contrôle Gemini ne se contente plus de l'état initial « sain » du circuit
breaker. Il vérifie les métadonnées **authentifiées du modèle configuré**, par
GET, avec délai de 5 secondes et sans retry automatique. Il n'envoie ni prompt
ni document. Une clé refusée, un modèle absent/différent, une limitation de
requêtes, une panne ou une connexion indisponible maintiennent l'état dégradé.
Les diagnostics ne conservent que des catégories ; les corps d'erreur du
fournisseur ne sont pas publiés dans les logs de la sonde.

L'overlay donne 10 secondes à la readiness et une période de 30 secondes.
Le moniteur existant conserve son cache de santé. L'accès aux métadonnées ne
prouve pas qu'une génération aboutit : quota, réponse QCM, streaming et parcours
pédagogique restent à exercer sur le compte de qualification autorisé.

L'essai des images locales avec clé Gemini factice et réseau interne fermé
confirme le refus 503 de l'API et du proxy ; la même exécution valide les
5 tests PostgreSQL et la restauration des 34 tables. Elle n'emploie aucune
clé Google réelle et ne prouve pas la disponibilité de Gemini.

## Isolation conservée

Aucune exception Internet n'est ajoutée. DNS et PostgreSQL IONOS restent les
seules sorties prévues. L'accès au domaine Google demeure **bloqué** et la
qualification ne peut donc pas réussir en l'état.

Préparer avec l'opérateur un chemin limité à
`generativelanguage.googleapis.com:443`, en conservant la vérification TLS.
Les NetworkPolicies standards ne sélectionnent pas un FQDN ; aucune capacité
FQDN du réseau actuel n'a été confirmée. Ne pas remplacer cette restriction
par une permission TCP/443 vers tout Internet ou par une IP Google obtenue
ponctuellement. Aucun proxy, CNI, pare-feu ou service partagé n'est modifié.

Gemini est ici le fournisseur de **génération**. Le moteur d'embeddings hérité
n'a pas de fournisseur Gemini : en mode auto sans autre clé compatible il
utilise le repli sans embeddings. Les tests pgvector valident le stockage et
les opérations vectorielles, pas la production d'embeddings par Gemini. Le
choix/dimension du modèle d'embeddings reste un lot distinct.

## Vérification locale sans accès Google

Avec le profil CI Python installé :

```sh
ENVIRONMENT=development DATABASE_URL=sqlite+aiosqlite:////tmp/mentor-local-tests.db \
python -m pytest tests/test_gemini_qualification.py \
  tests/test_argocd_qualification.py -q -o addopts= --timeout=30
```

Le vrai SDK s'exécute sur un transport HTTP en mémoire : authentification,
chemin du modèle, refus et reprise de readiness, payload QCM, streaming et
comptage d'usage sont vérifiés. Ce résultat n'est pas une génération Gemini
réelle. L'activation Kubernetes reste soumise à l'autorisation de déploiement
et aux autres [conditions de promotion](production-readiness.md).
