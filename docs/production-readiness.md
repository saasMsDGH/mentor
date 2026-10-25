# Conditions de promotion MENTOR vers main

Décision utilisateur du 25 octobre 2026 : **`main` représente la version de
référence de production**. Le premier merge attend une qualification réelle
Kubernetes et Argo CD. Le merge d'une architecture seule ou la réussite des
tests unitaires ne satisfait pas ce critère. Cette règle s'applique aussi aux
PR déjà ouvertes ; aucune fusion ni activation de déploiement n'en découle.

## État réellement constaté

- Les CI des quatre lots de correction/préparation ont réussi sur les runners
  de l'organisation. Les résultats restent attachés à leurs commits testés.
- La base `deploy/kubernetes/base` est inactive : zéro replica, images non
  configurées, aucun overlay qual/prod ou manifeste Argo CD MENTOR livré.
- Les tests PostgreSQL compilent les types et schémas ; ils ne constituent pas
  une migration exécutée sur PostgreSQL réel.
- Le dépôt GitOps `saasMsDGH/admin-platform-gitops` contient les points d'entrée
  `clusters/ovh-qual` et `clusters/ovh-prod`. Aucun fichier MENTOR n'a été repéré
  dans son arbre consulté. Cela ne prouve pas l'absence d'une Application créée
  directement dans un cluster.
- Le contexte Kubernetes local `pkubs` pointe vers une API locale dont la
  connexion est refusée lors de la tentative de lecture seule. L'état vivant
  d'Argo CD et de MENTOR n'est donc **pas établi**. Aucune application n'a été
  synchronisée ou modifiée.
- L'API GitHub indique actuellement `protected: false` pour `main`. Les règles
  de promotion ci-dessous sont documentées, pas encore imposées par une règle
  de protection ou un contrôle de qualification automatisé.

## Conventions GitOps identifiées

Référence examinée : `saasMsDGH/admin-platform-gitops`, commit
`7517b387eb4cff6452949e7fdce42534c2998000` :

- [standard applicatif](https://github.com/saasMsDGH/admin-platform-gitops/blob/7517b387eb4cff6452949e7fdce42534c2998000/docs/app-repo-standard.md) :
  `k8s/base`, `k8s/overlays/qual`, `k8s/overlays/prod`, namespaces `<app>-qual`
  et `<app>-prod`, validation explicite de la production ;
- [racine Argo CD](https://github.com/saasMsDGH/admin-platform-gitops/blob/7517b387eb4cff6452949e7fdce42534c2998000/platform/argocd/root-app.yaml) :
  source Git HTTPS, branche `main`, point d'entrée `clusters/ovh-qual` ;
- [accès GitHub Argo CD](https://github.com/saasMsDGH/admin-platform-gitops/blob/7517b387eb4cff6452949e7fdce42534c2998000/docs/argocd-github-access.md) :
  credentials hors Git et lecture seule ; un état `Healthy` peut coexister avec
  une erreur de comparaison et ne prouve pas une synchronisation réussie.

Ces conventions documentées ne prouvent ni la configuration actuelle du
cluster, ni ses droits, ni l'accès effectif d'Argo CD au dépôt MENTOR. Les
versions du cluster/CNI/Argo CD, le stockage, les DNS, le registre, les modèles
et les connexions aux données restent à relever et à qualifier.

## Ordre de livraison

1. Consolider un candidat contenant le socle applicatif et les correctifs
   nécessaires sur une branche de travail ; figer son commit, ses migrations
   et les digests des images. Tester ce contenu exact.
2. Fournir les overlays qual/prod, les images runtime, les migrations et la
   configuration GitOps adaptée aux conventions observées. Conserver secrets
   et credentials hors Git ; limiter les droits Argo CD aux sources et
   destinations MENTOR nécessaires.
3. Préparer l'Application de qualification sur le **commit candidat figé**,
   avant le premier merge. Elle ne doit pas attendre que du code non qualifié
   arrive dans `main`. La production suivra la version approuvée de `main`,
   avec les mêmes digests d'images que ceux qualifiés.
4. Après autorisation du déploiement de qualification, établir les preuves du
   tableau ci-dessous. L'ajout d'une Application à un point d'entrée déjà
   auto-synchronisé est une activation de déploiement : publier un tel changement
   ne doit pas précéder cette autorisation.
5. Après validation de ces preuves et autorisation du merge/de la promotion,
   fusionner le candidat approuvé et promouvoir les mêmes images. Vérifier
   ensuite la révision et les images réellement exécutées en production.

La convergence Argo CD après promotion est asynchrone. Une livraison n'est
terminée que lorsque Git, l'état synchronisé et les images exécutées concordent.
Aucune seconde chaîne `kubectl apply` ne doit gérer concurremment les ressources
applicatives confiées à Argo CD.

## Preuves exigées avant le premier merge

| Domaine | Preuve attendue sur le candidat |
|---|---|
| CI et images | Tests backend/frontend/build réussis sur le commit candidat ; images construites et référencées par digest ; licences et notices distribuées |
| PostgreSQL | Migration complète sur une vraie base isolée, vérification des données, recherche/pgvector exercés, stratégie de retour arrière documentée |
| Kubernetes | Rollout réel, probes opérationnelles, volumes et permissions vérifiés, redémarrage sans perte, ressources adaptées |
| Argo CD | Dépôt accessible, rendu réussi, absence d'erreur de comparaison/synchronisation, opération réussie, `Synced` et `Healthy` sur le SHA attendu |
| Réseau et identité | HTTPS, connexion, CSRF/CORS, refus entre deux comptes, sorties limitées aux services autorisés, aucun socket Docker ou accès cluster applicatif |
| Parcours métier | Upload → génération autorisée → QCM → réponse → progression FSRS → reprise, exercé via le déploiement et relu après redémarrage |
| Exploitation | Sauvegarde et restauration réellement testées, observabilité et procédure de retour arrière, secrets fournis hors Git |

Un simple `argocd app wait --sync --health` ne suffit pas comme preuve : enregistrer
également la révision observée et les digests des images exécutées, pour exclure
un résultat encore sain sur une ancienne version. Ne pas contourner les probes,
les contrôles de santé ou l'isolation pour obtenir un statut vert.

## Gouvernance à mettre en place

Les protections de `main` doivent exiger une PR approuvée, les validations CI du
candidat et la preuve de qualification Kubernetes/Argo CD correspondante. Définir
le nom de ce contrôle à partir du workflow réellement implémenté, sans annoncer
un contrôle requis inexistant. L'activation de ces règles reste à faire.

La CI conserve exclusivement `[self-hosted, k8s-deploy]` tant que c'est le label
disponible. Séparer les runners CI éphémères sans droits cluster des runners de
déploiement protégés ; Argo CD réconcilie ensuite les ressources selon ses droits
propres. Aucun `ubuntu-latest` ni ouverture réseau générale n'est nécessaire.

Références Argo CD : [Application](https://argo-cd.readthedocs.io/en/stable/user-guide/application-specification/)
et [synchronisation automatique](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/).
