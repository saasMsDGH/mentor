# Architecture cible — MENTOR

Statut : **proposée, non déployée**. Date : 2026-10-24.

## 1. Stratégie de réutilisation

1. Importer et figer OpenTutor au commit `2d2c003654cfbc90c173c9db6867ae65a65e8313`, conserver sa licence MIT, le code FastAPI/Next.js et ses suites de tests.
2. Exécuter les tests d'origine et documenter les résultats avant les refactorings.
3. Adapter progressivement la persistance, la sécurité et l'expérience mobile ; ne pas réécrire toute l'application.
4. S'inspirer des flux documentaires de Study Assistant et des examens d'Exameow, sans copier des modules Apache-2.0 sans audit explicite de leur intégration et de leurs notices.
5. Livrer par tranches verticales démontrables, chacune validée par tests.

## 2. Composants logiques

```text
PWA Next.js/React (mobile + desktop)
        |
HTTPS / Ingress / authentification OIDC ou sessions
        |
FastAPI : users, learning paths, documents, courses, concepts,
          questions, assessments, attempts, mastery, tutor, admin
        |                           |
        | REST                      | jobs/queue
        v                           v
PostgreSQL + pgvector         Redis + workers Python
        |                           |
        |                        OCR / extraction
        |                        RAG / génération LLM
        v                           |
 S3 compatible <-------------------+
        |
Passerelle IA OpenAI-compatible / vLLM / fournisseurs autorisés
```

Le serveur API demeure stateless. Les tâches longues sont asynchrones et identifiées par ID. L'inférence GPU peut être déportée hors du namespace MENTOR.

## 3. Kubernetes : séparation des responsabilités

Namespace `mentor` et, en pratique, séparation des environnements qual/prod. Déploiements : `web`, `api`, `worker-ingestion`, `worker-generation`, `scheduler`. Redis et PostgreSQL peuvent être opérés par une plateforme mutualisée disposant de sauvegardes. S3 est un service privé externe ou un stockage objet interne.

- ConfigMaps pour les paramètres non sensibles ; Secrets ou external secret store pour les clés.
- ServiceAccount par service avec permissions minimales ; NetworkPolicies ingress/egress.
- Readiness/liveness/startup probes ; requests/limits et HPA ou KEDA pour les workers.
- Ingress TLS, protections contre les abus d'API, rate limits et quotas de génération.
- Logs structurés, métriques Prometheus, latences OCR/RAG/LLM, traces si utiles.
- Sauvegardes/restaurations testées des données, documents et configurations.
- Aucune image de service applicatif ne monte `/var/run/docker.sock`. Le sandbox d'exécution d'OpenTutor doit être désactivé ou remplacé par un service isolé avant exposition réseau.
- Pas de migrations destructives automatiques au démarrage d'un pod ; Job dédié et stratégie de rollback.

## 4. Persistance et domaines métiers

Les entités existantes d'OpenTutor sont conservées jusqu'à l'inventaire SQLAlchemy/Alembic et la migration PostgreSQL. Extensions prévues :

| Domaine | Entités principales | Invariant |
|---|---|---|
| Identité | users, organizations, memberships | Isolation autorisée à chaque requête |
| Parcours | learning_paths, curricula, curriculum_versions, modules, lessons, concepts, prerequisites | Versions publiées stables |
| Sources | documents, document_versions, extraction_versions, document_chunks, source_references | Lien vérifiable vers page/passage/version |
| Publication | generated_contents, content_validations | Brouillon ≠ contenu validé |
| Évaluation | question_versions, options, assessment_templates, assessments, attempts, attempt_answers, grading_policies | Barème et questions figés pour l'historique |
| Adaptation | review_events, user_concept_mastery, spaced_repetition_states, mastery_snapshots | Événements datés, traitement idempotent |
| IA | providers, models, prompt_versions, generation_jobs | Traçabilité modèle/prompt et permissions sources |
| Audit | audit_events | Append-only pour les événements sensibles |

Les identifiants de concepts restent stables entre versions documentaires ; lorsqu'un concept change substantiellement, établir une relation de remplacement plutôt que réécrire l'historique.

## 5. Pipeline documentaire — inspiration Study Assistant

`uploaded → scanned → extracted → OCR-reviewed → segmented → indexed → mapped-to-concepts → draft-generated → validated → published`.

Chaque document a : propriétaire/organisation, classification, checksum, format MIME, version, provenance, dates de publication et de validité lorsque connues. Chaque extraction a son propre identifiant/version et un état d'erreur explicite. Chaque segment conserve la position dans le document source, l'identifiant/version d'extraction, le numéro de page/section, les offsets et une empreinte.

L'interface doit permettre de voir le document et le texte extrait côte à côte, corriger l'OCR, relancer l'indexation, repérer doublons/contradictions/obsolescence et invalider les contenus générés sur une source révisée. Les citations affichées par les cours/QCM sont vérifiées par existence des passages correspondants. Les documents entrants restent des données non fiables (protection contre les injections de prompt). Aucun transfert externe sans politique de confidentialité explicite.

## 6. Génération pédagogique

Utiliser les services OpenTutor de tutorat et génération là où ils sont testables. Ajouter une chaîne de validation : sources autorisées → contexte récupéré → génération structurée → schémas Pydantic → contrôle des citations → détection d'ambiguïtés/doublons → approbation → publication.

Distinguer connaissances officielles vérifiées, documents fournis, contenus générés et hypothèses. Aucune formule juridique inventée. Journaliser la version de modèle, la température et le prompt, avec identifiants de sources.

## 7. Examens — inspiration Exameow

Distinguer question de sa version et session d'examen de son modèle.

- Mode entraînement : explication immédiate, indices configurables.
- Mode évaluation : chronométrage et correction différée.
- Mode examen blanc : barème versionné, coefficients, pénalités, crédit partiel explicite, règle de navigation, auto-sauvegarde.
- Mode diagnostic/remédiation : banque équilibrée par concepts/difficultés.
- Une tentative garde le snapshot des énoncés/options, des bonnes réponses, du barème, des versions et des réponses réellement reçues.
- Notation déterministe côté serveur ; score sur 20 ou 100 séparé du score de maîtrise ; impossibilité de réécrire le résultat d'une tentative lorsque le référentiel est publié à nouveau.
- Gestion des expirations, double soumission, idempotency key et reprises réseau.

## 8. Apprentissage adaptatif

Préserver FSRS/BKT et les mécanismes LOOM/LECTOR d'OpenTutor tant qu'ils passent les tests. Séparer les trois couches : estimation statistique de maîtrise, politique explicable de choix des exercices, génération LLM. Les erreurs de mise à jour de maîtrise sont instrumentées et rejouables. Ne pas considérer une réponse correcte isolée comme un acquis durable.

## 9. Sécurité et accès

OpenTutor est orienté bêta mono-utilisateur locale avec authentification désactivée par défaut. **Ne pas exposer le déploiement standard sur Internet ou au réseau professionnel.** Avant tout accès : choix d'authentification, gestion de sessions, RBAC côté serveur, contrôles d'accès objets, scan uploads, isolation S3, TLS, CSRF/XSS/CORS, limitations, tests d'autorisation et suppression des montages dangereux.

L'utilisateur doit être explicitement autorisé à charger tout document professionnel interne. Les contenus sensibles sont bloqués par défaut sans configuration de traitement adaptée.

## 10. Décisions ouvertes avant implémentation

- Stratégie de migration SQLite → PostgreSQL (Alembic + scripts de réconciliation et tests).
- Choix auth (OIDC Keycloak/équivalent vs sessions internes), selon environnement.
- Choix file Redis pour les tâches longues ; politique retries/DLQ et cohérence des transactions.
- PWA offline : stockage chiffré si possible, règles de conflit, suppression au logout.
- Isolation des fonctions d'exécution de code si elles deviennent utiles.
- Mesures de qualité des contenus et seuil de validation humaine.

**Critère d'acceptation global :** une fonctionnalité n'est livrée que si la route API, l'interface, la persistance, la sécurité, les tests et la documentation fonctionnent réellement.
