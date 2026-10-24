# ADR-0001 — OpenTutor comme base applicative

**Statut : accepté pour expérimentation, conditionné à P0.**  
**Date : 2026-10-24.**

## Contexte

MENTOR vise une PWA d'apprentissage adaptatif, accessible sur mobile et poste de travail, alimentée par des sources documentaires et des modèles IA auto-hébergés ou autorisés. Le plan initial mentionnait Vue/Quasar et NestJS, mais la reconstruction des moteurs pédagogiques en retarderait la validation.

## Décision

Conserver dans un premier temps le frontend Next.js/React et le backend FastAPI d'OpenTutor. Initialiser MENTOR à partir du commit amont `2d2c003654cfbc90c173c9db6867ae65a65e8313`, et conserver les notices MIT d'origine.

Réutiliser/adapter les mécanismes existants de QCM, FSRS, BKT, LOOM/LECTOR et tutorat après test de fonctionnement. Leurs fonctions expérimentales ne deviennent pas automatiquement des exigences « livrées ».

Ajouter aux exigences MENTOR les pratiques de traçabilité/OCR/validation inspirées de Study Assistant (Apache-2.0) et les règles de sessions/barèmes/examens inspirées d'Exameow (Apache-2.0). Ne copier du code de ces projets que si une décision distincte approuve le périmètre et la conformité des notices.

## Conséquences

- Réduction du coût de reconstruction de fonctionnalités pédagogiques.
- Nécessité d'auditer les dépendances et de maintenir une relation explicite à l'amont.
- Migration de SQLite, authentification en réseau et PWA mobile nécessaires.
- Kubernetes est la cible, mais ne justifie pas la réécriture de la stack.
- Ce choix sera réévalué si les tests P0 échouent ou si la dette technique est prohibitive.

## Alternatives considérées

- Développement complet Vue/NestJS : meilleur contrôle initial, délais et risques pédagogiques accrus.
- Study Assistant comme base : excellente approche documentaire, moteur adaptatif moins central.
- Exameow comme base : bonne orientation examens, cursus pédagogique à construire.
