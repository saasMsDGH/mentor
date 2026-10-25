# Base de qualification Kubernetes — inactive

Cette base Kustomize est une proposition à revoir, conservée comme socle inactif.
Les deux Deployments restent à **zéro replica** et utilisent des noms d'images
non configurées. Cette base seule ne fournit aucun Ingress, Secret, Job de migration, worker
ou déploiement automatique. Les compléments du candidat sont dans `k8s/`. Aucun manifeste n'a été appliqué.

Elle prépare : namespace à politique de pods `restricted`, compte de service
sans jeton API, conteneurs non root, filesystem en lecture seule, capacités
supprimées, ressources et probes, Services internes et PVC d'uploads. Les UID,
capacités et tailles sont des valeurs de départ à qualifier sur les images
construites ; le PVC ne fournit aucune garantie de sauvegarde ou de stockage S3.

L'isolation refuse entrées et sorties par défaut, avec une seule exception :
serveur Next.js → API, même namespace, TCP/8000. **DNS, bases, modèles et Internet
restent bloqués.** Cela empêche volontairement un usage fonctionnel avant revue
des destinations réelles. L'application n'a aucun montage de socket Docker ;
l'exécution de code par conteneur doit échouer sans runtime disponible, jamais
basculer vers un processus non isolé.

## Promotion et Argo CD

Cette préparation ne satisfait pas encore la règle `main = production`.
Le candidat consolidé ajoute `k8s/base` et `k8s/overlays/qual|prod`, conformément
aux conventions de l'organisation. Il conserve cette base historique, supprime
son Namespace du rendu applicatif et cible `mentor-qual` / `mentor-prod`.
Le projet Argo CD, les namespaces administrés séparément et l'Application
manuelle sont décrits dans le [runbook Argo CD](../argocd/README.md).

Le tunnel `pkubs` répond désormais ; Kubernetes 1.36.3, Argo CD 3.5.1, les
sélecteurs Traefik/CoreDNS et la classe Longhorn ont été observés en lecture
seule. Les overlays ajoutent les seules exceptions DNS, Traefik et PostgreSQL
IONOS recensées. Le profil qual sélectionne Gemini ; aucun accès inférence n'est encore autorisé. Le rendu qual
prévoit un replica ; le rendu prod reste à zéro et sans exposition HTTP.
Aucun de ces rendus n'est appliqué. Voir les
[conditions de promotion](../../docs/production-readiness.md).

## Vérifications hors cluster

Avec les dépendances de `apps/api/requirements-ci.txt` :

```sh
python -m pytest tests/test_kubernetes_preparation.py -q -o addopts=
kubectl kustomize deploy/kubernetes/base > /tmp/mentor-qualification.yaml
```

La CI exécute les contrats de sécurité Python sur `[self-hosted, k8s-deploy]`.
Le rendu Kustomize est local et ne contacte pas le cluster. Ces contrôles ne
valident ni un schéma contre un serveur Kubernetes, ni l'application effective
des NetworkPolicies, ni le fonctionnement des images.

## Prérequis restant à qualifier

- Vérifier l'application effective des NetworkPolicies par le CNI, les refus
  réseau et l'accès TLS PostgreSQL. L'adresse IONOS est limitée à un `/32`
  TCP/5433 ; ce manifeste ne change aucun pare-feu ni tunnel existant.
- Publier après autorisation les images réduites de `deploy/images`, par digest,
  et valider les permissions du PVC Longhorn, son redémarrage et sa restauration.
  Les tests locaux readonly/non root ne prouvent pas le fonctionnement du PVC.
- Fournir hors Git `mentor-api-runtime` (`DATABASE_URL` DML, `JWT_SECRET_KEY`,
  `ENCRYPTION_KEY`), `mentor-postgres-migration` (`DATABASE_URL` DDL),
  `mentor-model-credentials` (`GEMINI_API_KEY` pour qual). La ConfigMap qual
  `mentor-model-runtime` fournit `LLM_PROVIDER=gemini` et le modèle explicite.
  Référencer les secrets selon la procédure opérateur ; ne pas mettre de
  valeurs dans Git, un ticket ou les sorties de CI.
- Provisionner une base MENTOR neuve isolée avec vector et deux rôles restreints.
  La baseline figée et sa restauration ont été exercées sur PostgreSQL local ;
  aucune migration ni création de rôle n'a été exécutée sur IONOS.
- Le choix Gemini est préparé dans le profil qual. Ajouter une sortie
  contrôlée vers le domaine Google après validation opérateur, sans autoriser
  tout Internet sur TCP/443. Tester upload, génération, QCM, FSRS et reprise
  avec deux comptes, sans exposer le Service privé dans le navigateur.
- Qualifier HTTPS, connexion, CSRF/CORS, SSE, sauvegarde des uploads,
  observabilité, ressources et retour arrière. L'overlay prod sans ingress et
  à zéro replica est un emplacement réservé, pas une production prête.

## Runners

Le label `k8s-deploy` est conservé parce qu'il est celui actuellement demandé.
Séparer les runners **CI éphémères sans droits cluster** des runners de
**déploiement protégés par approbation**, avec groupes et labels distincts.
Un label seul n'isole pas un runner : limiter dépôts autorisés, credentials,
montages et accès réseau. Ne jamais exécuter une contribution externe sur un
runner disposant d'accès de déploiement. Aucun changement de runners ou de
cluster n'est effectué par cette préparation.

Références : [recommandations applicatives Kubernetes](https://kubernetes.io/docs/concepts/security/application-security-checklist/)
et [NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).
