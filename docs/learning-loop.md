# Boucle pédagogique persistée

Le test `tests/test_mentor_learning_journey.py` complète le smoke de la PR #10 :
import Markdown réel, extraction de QCM via le parseur et un fournisseur simulé,
réponse fausse, échéance FSRS, reprise de la question puis réponse correcte.
Les tentatives et compteurs sont relus depuis une nouvelle session SQLite.
Les connexions IP sont interdites par la fixture ; l'estimation de tokens est
remplacée en test pour éviter le téléchargement initial du tokenizer. La
vérification de disponibilité LLM est simulée uniquement dans ce test.

`GET /api/quiz/{course_id}/due-review?limit=20` retourne les questions actives,
non diagnostiques, rattachées aux nœuds dont `next_review_at` est atteint pour
l'utilisateur connecté. La limite est comprise entre 1 et 100 ; l'ordre est
échéance, ordre de question, identifiant. Chaque réponse contient la question,
les options, `content_node_id` et `next_review_at`, sans correction. Le cours
est contrôlé avec la même vérification de propriétaire que les autres routes
quiz. `POST /api/quiz/submit` conserve la notation et la mise à jour FSRS existantes.

L'échéance reste calculée au niveau du **nœud documentaire**, pas de chaque
question : répondre à une question reprogramme le nœud et retire ses autres
questions de la file jusqu'à la prochaine échéance. Ce comportement reprend
le modèle de progression existant. Il ne constitue pas un moteur d'examen.

Validation ciblée, avec les dépendances de `requirements-ci.txt` :

```sh
ENVIRONMENT=development DATABASE_URL=sqlite+aiosqlite:////tmp/mentor-tests.db \
CODE_SANDBOX_BACKEND=process python -m pytest \
tests/test_mentor_learning_journey.py -q -o addopts= --timeout=30
```

Le fournisseur simulé prouve l'intégration et la validation structurelle,
pas la fidélité d'un LLM réel. Le lien vers un nœud n'est pas encore une citation
versionnée de page/passage. Publication humaine, versions documentaires,
tentatives d'examen figées et interface de révision restent à développer.
