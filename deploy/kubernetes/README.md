# Base de qualification Kubernetes — inactive

Cette base Kustomize est une proposition à revoir, sans cible cluster connue.
Les deux Deployments restent à **zéro replica** et utilisent des noms d'images
non configurées. Aucun Ingress, Secret, Job de migration, worker, base de données
ou déploiement automatique n'est fourni. Aucun manifeste n'a été appliqué.

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

## Conditions pour un futur overlay opérateur

- Identifier la version Kubernetes, le CNI et sa prise en charge des politiques,
  les classes de stockage, le contrôleur Ingress et les sélecteurs DNS réels.
  Aucune adresse de cluster, de base, de modèle ou de domaine n'est présumée.
- Construire et analyser les images, conserver la licence MIT et les notices
  amont ; sélectionner des digests immuables. Valider UID, permissions du PVC,
  chemins écrits, cache tokenizer et démarrage avec racine en lecture seule.
  Le Dockerfile API amont installe encore le CLI Docker : une image de
  qualification réduite et sans dépendance à un démon reste à produire.
- Fournir hors Git le Secret `mentor-api-runtime` avec `DATABASE_URL`,
  `JWT_SECRET_KEY` et `ENCRYPTION_KEY`, ainsi que la ConfigMap
  `mentor-model-runtime` avec les champs existants `LLM_PROVIDER`,
  `CUSTOM_LLM_BASE_URL`, `CUSTOM_LLM_MODEL`. Le fournisseur custom est prévu
  pour un endpoint autorisé compatible OpenAI ; une éventuelle clé fournisseur
  doit elle aussi être injectée par référence à un secret, jamais en clair.
  Configurer TLS PostgreSQL, origines CORS exactes et authentification du modèle
  selon l'infrastructure autorisée.
- Définir des exceptions réseau minimales pour DNS, PostgreSQL et inférence
  autorisée. Ne pas ajouter de sortie générale vers Internet. Vérifier les
  refus depuis les pods et l'impossibilité d'accéder aux documents d'un autre
  utilisateur. Les conteneurs d'init, sidecars, workers et migrations doivent
  recevoir leurs propres permissions et exceptions revues.
- Produire une baseline Alembic réelle, tester migration, rollback adapté,
  réconciliation et restauration. La PR #9 est un prototype de dialecte et ne
  fournit pas encore cette garantie. Ne pas activer `APP_AUTO_CREATE_TABLES`.
- Résoudre les URL Next.js compilées : `NEXT_PUBLIC_API_URL` est utilisé par
  le navigateur et les rewrites serveur. Une URL Kubernetes privée ne doit pas
  être exposée comme endpoint navigateur. Qualifier le routage même origine,
  SSE, connexion, CSRF et HTTPS avant toute exposition. Aucun domaine n'est
  inventé ici ; aucun Ingress permissif n'est fourni.
- Préparer stockage objet privé, travailleurs, observabilité et sauvegardes
  avant d'augmenter les replicas. La base inactive n'est pas une application
  Kubernetes opérationnelle et ne justifie aucune promotion de M0/M1.

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
