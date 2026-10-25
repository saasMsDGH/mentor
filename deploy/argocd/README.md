# Qualification Argo CD MENTOR — préparation sans activation

`main` représente la production. Le premier merge attend les preuves décrites
par [production-readiness](../../docs/production-readiness.md). Aucun fichier
ici ne crée une Application automatiquement ; aucune synchronisation ou
publication d'image n'a été réalisée.

## Ressources et responsabilités

- `project.yaml` limite Argo CD au dépôt MENTOR, à `mentor-qual` / `mentor-prod`
  et aux seuls types de ressources applicatives nécessaires. Il n'autorise ni
  Secret, ni RBAC, ni ressource cluster.
- `namespace-qual.yaml` / `namespace-prod.yaml` sont administrés séparément
  avec Pod Security `restricted`, version 1.36. Ils ne font pas partie de la
  source applicative Argo CD.
- `scripts/render_argocd_candidate.py` produit le namespace qual, le projet
  et une Application **manuelle**, sur SHA Git complet et deux références GHCR
  par digest. Ces repositories sont les cibles proposées ; les images doivent
  réellement y être publiées après autorisation. Le script ne publie rien.
- `k8s/overlays/qual` suit le standard existant de l'organisation :
  `mentor.qual.dgsynthex.online`, Traefik, résolveur `qual-dns`, middleware
  `platform-security-headers` du namespace `kube-system`. Ces dépendances
  doivent encore être exercées ensemble. Le PVC choisit explicitement
  `longhorn` car deux StorageClasses sont marquées par défaut dans le cluster.
- `k8s/overlays/prod` reste à zéro replica et sans ingress. Aucun Application
  prod n'est générée ; ne pas réutiliser le domaine/certificat de qualification
  comme configuration de production.

L'Application ne contient pas de politique `automated` et utilise
`CreateNamespace=false`. Ne pas l'ajouter à une racine GitOps auto-synchronisée
avant autorisation : cet ajout peut activer un déploiement.

## Ordre de synchronisation prévu

1. Vague `-2` : compte de service sans token et toutes les NetworkPolicies,
   dont le refus par défaut. L'opérateur a déjà fourni namespace et secrets.
2. Vague `-1` : Job **Sync** `mentor-migrate`, image API du candidat,
   `alembic -c alembic-postgres.ini upgrade head`. Il reçoit uniquement le
   DSN DDL de `mentor-postgres-migration`. Pas de droits superutilisateur,
   JWT ou clé de chiffrement. Un échec bloque la suite ; aucune relance
   automatique (`backoffLimit: 0`). Le hook est recréé avant la prochaine
   synchronisation et son résultat expire après 24 h.
3. Vague `0` : services, volume et applications. Le démarrage de l'API utilise
   le rôle DML et refuse de créer/tamponner le schéma. Sa readiness reste
   fermée sans schéma à jour et inférence disponible.

Le Job n'est pas PreSync : lors du premier déploiement, PreSync précéderait la
création du compte de service et des règles réseau dont il dépend.

## Prérequis opérateur

Avant toute activation, publier les images approuvées du commit testé et
vérifier les droits de lecture du registre depuis le cluster ; préparer l'accès
Git HTTPS en lecture seule d'Argo CD selon la procédure existante, hors Git.
Ne pas substituer un identifiant d'image locale au digest de manifeste publié.

Sur IONOS, prévoir une **base MENTOR neuve dédiée**, vector préinstallé, un
propriétaire DDL et un rôle applicatif DML avec privilèges par défaut sur les
futures tables/séquences. La baseline ne convertit aucune base existante.
Qualifier TLS et la chaîne de confiance PostgreSQL sans désactiver la validation
pour faire passer les tests. Aucun provisionnement distant n'a été réalisé.

Les références prévues, à fournir hors Git par la procédure de secrets de
l'organisation, sont :

| Ressource | Champs attendus |
|---|---|
| Secret `mentor-postgres-migration` | `DATABASE_URL` du rôle DDL |
| Secret `mentor-api-runtime` | `DATABASE_URL` DML, `JWT_SECRET_KEY`, `ENCRYPTION_KEY` |
| Secret `mentor-model-credentials` | `GEMINI_API_KEY` pour le profil qual |
| ConfigMap `mentor-model-runtime` (fournie par l’overlay qual) | `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-3.8-flash` |

Le choix utilisateur est **Gemini**. Le profil qual utilise le connecteur natif
existant, via l'endpoint Google compatible OpenAI, sans nouvelle dépendance.
Le modèle stable proposé est `gemini-3.8-flash`, explicitement configuré ;
il reste à vérifier avec le compte prévu. Voir le
[contrat Gemini](../../docs/gemini-qualification.md). La clé Google n'est pas
une clé OmniRoute : aucune clé d'une autre application n'est reprise.

Les seules sorties actuellement prévues sont DNS et IONOS `/32:5433`.
**L'accès Google reste bloqué** jusqu'à la préparation d'une sortie contrôlée
vers `generativelanguage.googleapis.com:443`. Une NetworkPolicy Kubernetes
standard ne filtre pas par domaine. La capacité FQDN du cluster n'est pas
établie ; ne pas ajouter `0.0.0.0/0:443` ou figer une résolution DNS éphémère.
Préparer une solution opérateur compatible avec le réseau existant, puis tester
accès autorisé et refus. Le profil n'est pas qualifié tant que cela manque.

## Rendu et simulation, sans création de ressources

Avec le profil Python CI, `kubectl` 1.36.3 vérifié et les trois variables locales
renseignées avec le SHA testé et les **digests publiés** du candidat :

```sh
python scripts/render_argocd_candidate.py \
  --revision "$CANDIDATE_SHA" \
  --api-image "$MENTOR_API_IMAGE" --web-image "$MENTOR_WEB_IMAGE" \
  > /tmp/mentor-argocd-candidate.yaml
kubectl --context pkubs apply --dry-run=server \
  -f /tmp/mentor-argocd-candidate.yaml -o name
kubectl kustomize k8s/overlays/qual > /tmp/mentor-qual-template.yaml
python -m pytest tests/test_argocd_qualification.py -q -o addopts=
```

Le rendu Kustomize direct garde les images placeholder : les remplacements par
digest sont dans l'Application générée. Les tests de contrat rendent les vrais
overlays ; ils ne prouvent pas la résolution Git/registre ni l'admission des
workloads dans un namespace absent. Le dry-run serveur effectué le 25 octobre
utilisait des hashes synthétiques uniquement pour vérifier les schémas des trois
ressources de contrôle. Il n'a créé ni namespace, ni projet, ni Application.

## Capturer la preuve après déploiement explicitement autorisé

Captures réservées à un opérateur de confiance, depuis le cluster attendu.
Elles restent privées ; ne pas joindre les JSON complets à Git ou à une PR.
Les manifests doivent référencer les secrets, jamais contenir leurs valeurs.

```sh
umask 077
mkdir -p /tmp/mentor-qualification-evidence
kubectl --context pkubs -n argocd get application mentor-qual -o json \
  > /tmp/mentor-qualification-evidence/application.json
kubectl --context pkubs -n mentor-qual get deployments -o json \
  > /tmp/mentor-qualification-evidence/deployments.json
kubectl --context pkubs -n mentor-qual get replicasets -o json \
  > /tmp/mentor-qualification-evidence/replicasets.json
kubectl --context pkubs -n mentor-qual get pods -o json \
  > /tmp/mentor-qualification-evidence/pods.json
python scripts/verify_argocd_qualification.py \
  --application /tmp/mentor-qualification-evidence/application.json \
  --deployments /tmp/mentor-qualification-evidence/deployments.json \
  --replicasets /tmp/mentor-qualification-evidence/replicasets.json \
  --pods /tmp/mentor-qualification-evidence/pods.json \
  --revision "$CANDIDATE_SHA" \
  --api-image "$MENTOR_API_IMAGE" --web-image "$MENTOR_WEB_IMAGE"
```

Le validateur exige `Synced / Healthy`, le SHA attendu dans la source, l'état
synchronisé et l'opération réussie, ainsi qu'un hook de migration réussi. Il
vérifie deux Deployments complets, leurs ReplicaSets actuels et suffisamment de
pods prêts exécutant les digests attendus. Une ancienne opération saine, zéro
replica, une génération non observée ou une exclusion Argo ne qualifie pas.

Pour un index multiarchitecture, les options `--api-runtime-digest` et
`--web-runtime-digest` doivent provenir du manifeste amd64 vérifié **dans
l'index publié approuvé**, pas simplement du digest observé dans le pod. Les
captures doivent appartenir à la même observation ; en cas de rollout en cours,
attendre sa fin et les reprendre.

Cette preuve est nécessaire mais ne remplace pas les essais HTTPS, deux
comptes, upload→génération→QCM→FSRS→reprise après redémarrage, isolation réseau,
probes, sauvegarde des fichiers et restauration dans l'environnement réel.

## Limite CI constatée

Le runner actuel ne possède pas `/var/run/docker.sock`. Les contrôles unitaires
et de rendu peuvent y tourner ; la qualification des images reste **bloquante**
avec un diagnostic explicite. Ne pas ignorer ce job ni déclarer les résultats
locaux comme résultat CI. Préparer un runner CI éphémère avec moteur local
isolé et sans credentials/droits cluster, distinct des runners de déploiement.
Tous les jobs conservent les labels demandés `[self-hosted, k8s-deploy]` ; les
labels/groupes dédiés devront être alignés lors de cette séparation opérateur.
Aucun socket de nœud de production, mode réseau host ou privilège ajouté au
runner partagé n'est proposé pour contourner ce blocage.
