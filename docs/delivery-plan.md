# Plan de livraison MENTOR — exécution incrémentale

Statut : **plan de travail**, non preuve de livraison. Révision : 2026-10-25.
Références : `docs/architecture.md`, `docs/roadmap.md`, PR #8 (socle), PR #9 (prototype PostgreSQL), tickets #2–#7.

## Principes de livraison

- Préserver Next.js et FastAPI initialement ; ne pas réécrire OpenTutor pendant la phase de stabilisation.
- Tout build et test CI se fait sur un runner auto-hébergé de l'organisation, jamais sur `ubuntu-latest`.
- Séparer dès que possible les runners de **CI non privilégiés** et les runners `k8s-deploy` qui disposent de droits cluster. Jamais d'exécution de code de pull request externe sur runner de déploiement.
- Ne pas développer simultanément le RAG complexe, les examens et la migration PostgreSQL avant d'avoir une baseline reproductible.
- Utiliser des modèles simulés en CI ; les tests réels d'inférence locale se font dans un environnement contrôlé.
- Les sources professionnelles internes ne peuvent être importées que si leur traitement sur cette infrastructure est explicitement autorisé.

## Ordre de livraison et gates

| Jalons | Contenu principal | Gate avant le jalon suivant |
|---|---|---|
| M0 – Baseline importée | OpenTutor gelé, licence, CI, tests unitaires, smoke API | Tests lint/build/backend verts, régressions documentées et import source vérifié |
| M1 – Qualif K3s privée | PostgreSQL avec migrations réelles, authentification obligatoire, images non-root, stockage durable, S3, déploiement Helm/Kustomize, sécurité | 2 comptes isolés, redémarrage sans perte, accès HTTPS, aucune capacité Docker socket, restauration testée |
| M2 – Première boucle pédagogique | Upload PDF → extraction → programme validé → cours sourcé → 10-20 QCM → réponses notées → progrès consultables | Parcours complet sur smartphone et ordinateur, références vérifiables et sans faux boutons |
| M3 – Référentiel documentaire fiable | OCR corrigeable, documents et extractions versionnés, provenance page/passage, dates de validité, contradictions, publication humaine | Une correction OCR ou nouvelle version invalide correctement les contenus dérivés |
| M4 – Examens | Banque versionnée, sujets blancs, barèmes, coefficients, pénalités, timer serveur, tentative figée, correction reproductible | Ancien examen recalculable à l'identique, pas de fuite de correction, reprise réseau validée |
| M5 – Adaptation | FSRS + modèle de maîtrise, séances 3/5/10/20/30 min, lacunes et prérequis, planification | Scénarios de maîtrise/oubli produisent une sélection différente et explicable |
| M6 – Expérience mature | PWA offline limitée, synchronisation/idempotence, dashboards avancés, notifications opt-in, accessibilité | E2E mobile et desktop, synchronisation sans doublons, restauration et supervision |

**M1 est une qualification privée**, non une ouverture à des utilisateurs externes. Les jalons M2/M3 peuvent être développés par flux vertical, mais les garanties documentaires M3 sont nécessaires avant de considérer le parcours « concours » comme fiable.

## Phase immédiate — fermer M0

1. Lire les logs de la dernière CI #40205418050 sur le runner de l'organisation : échec antérieur Python durant collecte à cause de `ENVIRONMENT=test` incompatible avec le mode single-user, ainsi qu'un timeout frontend de 5s.
2. Vérifier la CI du correctif `787585edf4a3fe187060a163d28d56df542690d7`, garder l'authentification obligatoire dans tout déploiement réseau.
3. Ajouter un smoke API local à LLM simulé (fixture versionnée), avec création de cours, import, quiz, soumission et progression.
4. Réexécuter les tests backend spécifiques FSRS, BKT, LOOM, LECTOR, et noter les fonctionnalités expérimentales non utilisées.
5. Exiger des résultats de CI (logs et rapports) avant de finaliser l'intégration sur `main`.

## Phase M1 — travail à paralléliser avec prudence

**Lot données** (PR #9, volontairement en brouillon) : convertir les types SQLAlchemy, créer baseline Alembic PostgreSQL, gérer `CREATE EXTENSION vector`, index GIN, migrations vérifiées et tests de réconciliation SQLite→PostgreSQL. Valider sur PostgreSQL réel en qualif.

**Lot sécurité** : ne plus monter le socket Docker, isoler/désactiver les capacités d'exécution arbitraire et navigateur, session réelle avec parcours de connexion web, RBAC et contrôle d'objets. Une API JWT seule n'est pas un produit authentifié complet.

**Lot infra** : chart Helm et valeurs qualif, API et frontend Deployments, services, Ingress HTTPS, Jobs migrations, workers, Secrets/ExternalSecrets, NetworkPolicies, resources, probes, métriques Prometheus, sauvegardes et exercices de restauration.

**Lot exploitation** : noms d'hôte/Ingress et endpoint OpenAI-compatible paramétrables ; aucune URL interne ni credential codé en dur ; modèles vLLM distants de la charge de l'application.

## Première recette utilisateur cible (M2)

Scénario E2E sur documents publics autorisés :
1. Se connecter sur PC, créer le parcours de concours.
2. Importer un PDF valide et voir les étapes de traitement.
3. Visualiser extraction et sources, valider un plan de cours.
4. Lire un cours pédagogique avec citations page/section réellement résolues.
5. Générer 20 QCM sourcés, réaliser une session sur smartphone.
6. Obtenir score, correction, historique, notions fragiles.
7. Reprendre la session et consulter les statistiques sur PC.

Le référentiel concours reste paramétrable. Les modules d'exemple ne constituent pas des informations officiellement applicables.

## Arbitrages techniques anticipés

- PostgreSQL/pgvector : préférable pour isolation, données relationnelles et recherche ; dimension d'embeddings validée selon le modèle, pas imposée implicitement à 1536.
- Redis pour tâches simples ; RabbitMQ à décider seulement si la charge ou les besoins de livraison l'exigent.
- LLM : interface OpenAI-compatible et vLLM existant ; séparation génération, validation et embedding si nécessaire.
- UX : français avant ouverture réelle, mobile-first ; les vues chinoises/anglaises héritées d'OpenTutor sont à traduire.
- Score pédagogique (probabilité de maîtrise) distinct de la note d'examen ; moteur de notation déterministe.

## Interdictions de promotion

Ne pas annoncer « prêt Kubernetes » si : test PostgreSQL réel non passé, interface de connexion absente, Docker socket accessible, documents non isolés, RBAC non vérifié, authentification désactivée ou aucune sauvegarde testée.
