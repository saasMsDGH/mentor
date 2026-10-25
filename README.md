# MENTOR

MENTOR est une plateforme d'apprentissage adaptatif, auto-hébergeable et pensée pour les étudiants et professionnels préparant des concours, examens et certifications.

> **État : import amont effectué sur `feature/import-opentutor`, validation CI en cours.** Le projet n'est pas encore déployable en production et n'a pas encore été sécurisé pour un accès multi-utilisateur. Les fonctionnalités cibles restent à valider individuellement.

## Règle de promotion vers main

`main` représente la version de référence de production. Le premier merge exige
une qualification Kubernetes réelle du candidat et une validation Argo CD sur
le commit attendu, ainsi que les tests applicatifs et de persistance. Une CI
verte ou un rendu Kustomize local ne suffit pas. Voir les
[conditions de promotion Kubernetes / Argo CD](docs/production-readiness.md).

## Décision de socle

- **[OpenTutor](https://github.com/zijinz456/OpenTutor)** : base applicative, tuteur, quiz, FSRS/BKT, graphe de maîtrise et planification.
- **[Study Assistant](https://github.com/neuronection/study-assistant)** : référence de conception pour l'extraction/OCR, la provenance des sources, la correction humaine et la publication pédagogique.
- **[Exameow](https://github.com/heshengtao/exameow)** : référence de conception pour les examens blancs, banques de questions, barèmes et sessions chronométrées.

Le code d'OpenTutor est sous licence MIT (copyright Zijin Zhang, 2026). Study Assistant et Exameow sont sous Apache-2.0. Une fonctionnalité inspirée d'un projet ne doit pas être considérée comme du code réutilisable sans examen des licences, des dépendances et des notices applicables.

**Version amont visée :** OpenTutor `2d2c003654cfbc90c173c9db6867ae65a65e8313` (22 octobre 2026). Toute mise à jour de l'amont fera l'objet d'une revue séparée.

## Architecture cible

- Frontend : conserver initialement **Next.js/React/TypeScript** d'OpenTutor ; PWA mobile-first et accessibilité à développer.
- API : conserver initialement **FastAPI/SQLAlchemy/Alembic** ; contrôles RBAC et accès multi-appareils.
- Données : **PostgreSQL + pgvector** ; migration vérifiée depuis SQLite, sans perdre d'historique pédagogique.
- Documents : stockage privé **S3-compatible**, extraction/OCR asynchrones, traçabilité et versionnement de bout en bout.
- Asynchrone : **Redis + workers** pour ingestion, génération, indexation et planification des révisions.
- IA : fournisseurs compatibles OpenAI, notamment **vLLM**, avec validation structurée des contenus et citations.
- Cible d'exploitation : **Kubernetes**, Ingress HTTPS, secrets externalisés, observabilité, sauvegardes testées.

## Principes non négociables

1. Une réponse pédagogique factuelle doit pouvoir être reliée à une source et à une version.
2. Une question d'examen publiée est validée et conserve la version présentée lors de chaque tentative.
3. La note d'examen et l'estimation de maîtrise sont deux métriques distinctes.
4. Les mises à jour pédagogiques sont explicables, déterministes lorsqu'elles affectent les scores, et testées.
5. Un document confidentiel ne part jamais vers un modèle non autorisé.
6. Ne pas exposer le Docker socket dans les pods applicatifs.
7. Une interface ne doit jamais annoncer comme opérationnelle une fonctionnalité non implémentée.

## Démarrage des travaux

Voir [l'architecture](docs/architecture.md), [la feuille de route](docs/roadmap.md) et [les décisions d'architecture](docs/adr/0001-opentutor-as-foundation.md).

Le code OpenTutor a été importé à la révision figée, avec sa licence MIT et ses sources de tests. Les travaux suivants sont : tests amont, audit de sécurité, migration PostgreSQL, PWA, pipeline documentaire sourcé puis examens. **Ne pas exposer le Docker Compose amont sur un réseau : authentification désactivée et socket Docker monté par défaut.**

Le premier parcours de démonstration sera « Concours d'officier de gendarmerie interne — Préparation 2027 ». Il est **indicatif**, jamais présenté comme référentiel officiel sans source contrôlée.

## Préparation de qualification

Voir les [overlays Kubernetes](deploy/kubernetes/README.md), le
[runbook Argo CD manuel](deploy/argocd/README.md), les
[images de qualification](deploy/images/README.md) et les
[résultats de validation constatés](docs/validation-2026-10-25.md).
Cette préparation ne constitue pas une qualification de production.
