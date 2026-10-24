# Roadmap de réalisation — MENTOR

Statut : **backlog initial**, non livré.

## P0 — Baseline OpenTutor et audit (priorité absolue)

- Importer le code depuis le commit OpenTutor gelé ; conserver `LICENSE`, l'attribution et les références au dépôt amont.
- Vérifier installabilité et tests unitaires, API, Playwright, build frontend et analyse des dépendances.
- Documenter le jeu de données de test et une installation locale de référence.
- Auditer l'accès Docker socket, le sandbox, l'authentification et les flux fichiers.
- Créer les premiers fichiers ADR, guide développeur, inventaire des tables et contrats API.

**Definition of done :** repository compilable, suite tests exécutée avec résultats consignés et liste de vulnérabilités/classifications ; aucune exposition extérieure.

## P1 — Plateforme sécurisée, persistante et déployable sur K8s

- PostgreSQL/pgvector avec migration Alembic et vérification des données.
- Authentification obligatoire en déploiement réseau, contrôle d'accès par utilisateur/organisation et tests de permissions.
- Images runtime sans montages de code ni Docker socket.
- Helm chart ou manifests Kustomize, Job migration, probes, NetworkPolicy, Secrets et Ingress HTTPS.
- S3 privé, workers séparés, pipeline CI, métriques et sauvegarde/restauration.
- Squelette PWA mobile-first permettant navigation, sessions courtes et continuité multi-appareil.

**DoD :** déploiement en qualification sur Kubernetes, redémarrage sans perte, un même utilisateur reprend sa progression sur mobile et PC, accès non autorisé rejeté.

## P2 — Référentiel documentaire fiable (Study Assistant)

- Import PDF/DOCX/PPTX et OCR selon besoins ; états de traitements.
- Visionneuse document/texte extrait, correction OCR avec réindexation.
- Sources/version/extraction/segment/page/offset, validité temporelle et checksum.
- RAG hybride vérifiable avec citations cliquables, versions de prompts et modèles.
- Validation humaine du programme, cours et QCM ; rejet d'une citation introuvable.
- Détection des doublons et des contradictions, invalidation des contenus dérivés obsolètes.

**DoD :** PDF réglementaire importé → cours sourcé → page exacte retrouvable ; après correction OCR, index mis à jour ; contradiction signalée.

## P3 — Évaluations robustes (Exameow)

- Banque QCM (unique/multiple), versionnage, validations et liens aux concepts.
- Mode entraînement, évaluation, diagnostic et examen blanc.
- Barème versionné, coefficient matière, pénalités/crédit partiel configurables, notes sur 20/100.
- Timer côté serveur, brouillon auto-sauvegardé, tentative figée, correction détaillée, résultats.
- Tests idempotence, reprise après coupure, chronomètre, intégrité des réponses, recalcul reproductible.

**DoD :** réaliser un examen blanc complet sur téléphone, retrouver le même historique sur PC, reproduire exactement une ancienne note.

## P4 — Adaptation et révisions quotidiennes

- Mise à jour événementielle et explicable des états FSRS/BKT.
- Concepts et prérequis, LOOM/LECTOR après validation expérimentale.
- Séances quotidiennes 3/5/10/20/30 minutes : acquisition, réactivation, erreurs, correction.
- Analyse des erreurs, remédiation ciblée, planning modulé selon la date d'examen et la disponibilité.
- Tests contre exemples : bonne réponse fortuite, confusion durable, absence, notions obsolètes.

**DoD :** les réponses modifient les priorités de révision de façon explicable sans rendre l'algorithme dépendant des seuls choix du LLM.

## P5 — Expérience mature

- PWA hors ligne sur contenus préchargés, sync idempotente et conflits gérés.
- Tuteur intégré aux leçons avec citations et politiques de confidentialité.
- Statistiques de progression/rétention/incertitude.
- Notifications opt-in, accessibilité WCAG 2.2 AA visée, revue performance mobile.

## Référentiel de démonstration

« Concours d'officier de gendarmerie interne — Préparation 2027 ». Le découpage proposé est **indicatif**, aucune modalité de concours ne doit être codée en dur et aucun contenu ne doit être présenté comme officiel sans source vérifiée.

## Tests transversaux obligatoires

- Tests unitaires et d'intégration, tests API, autorisations et isolation multi-utilisateur.
- Tests migrations, import/OCR/index, vérification des références et schémas générés.
- Tests pédagogiques (FSRS, maîtrise, sélection), snapshot/barème d'examen.
- E2E Playwright smartphone/desktop, synchronisation et persistance.
- Évaluations de qualité LLM sur corpus de référence ; mocks pour CI déterministe.
- Contrôle de licences/dépendances et audit sécurité avant mise en réseau.

## Priorisation d'exécution

**Ne pas paralléliser P2/P3 à grande échelle avant stabilisation P0/P1.** Les schémas de source et de question versionnés doivent être définis tôt pour éviter les migrations destructives et la perte de traçabilité.
