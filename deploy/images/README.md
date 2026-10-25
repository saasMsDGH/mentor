# Images de qualification

Ces Dockerfiles utilisent la racine du dépôt comme contexte et conservent les
Dockerfiles amont pour les usages existants. Les bases Python 3.11 et Node 24
sont figées par digest. La qualification actuelle vise Linux amd64.

## Préparer puis construire sans réseau de build

Avec Python 3.11, pip et le profil CI installés :

```sh
python scripts/prepare_runtime_dependencies.py api
python scripts/prepare_runtime_dependencies.py web
docker build --network none -f deploy/images/api.Dockerfile -t mentor-api:qualification-work .
docker build --network none -f deploy/images/web.Dockerfile -t mentor-web:qualification-work .
```

La préparation télécharge les wheels Python verrouillés et les archives npm
référencées par le lockfile. Les archives proviennent de PyPI/npm ; aucun code
pédagogique ou document n'est envoyé à ces services. Les caches publics sont
placés sous `.build/`, ignorés par Git. La construction installe les wheels
avec contrôle des hashes et npm en mode offline avec vérification du lockfile.
Le tokenizer est préparé avec les hashes intégrés à tiktoken. Les images de
base sont téléchargées au préalable par leur digest si elles ne sont pas locales.

`requirements-runtime.txt` est le profil source. `requirements-runtime.lock`
fige ses dépendances et leurs hashes pour Python 3.11/Linux amd64 ; une mise à
jour doit régénérer ce lock et être testée. Les bundles ne remplacent pas le
scan de vulnérabilités ni l'audit complet des licences avant promotion.

## Contrats runtime

- API UID/GID 10001, sans CLI Docker, compilateur ou dépendances pytest. Le
  profil exclut les intégrations lourdes OCR/GPU/navigateur. Authentification
  obligatoire, migrations explicites, secrets fournis au runtime.
- Frontend UID/GID 1001, sortie Next.js standalone, cache modifiable sous
  `/app/apps/web/.next/cache`. Le navigateur utilise `/api` en même origine.
  `API_INTERNAL_URL` est réservé au serveur et aux rewrites du build ; le
  Service `mentor-api:8000` doit garder le même nom en qual et prod pour
  promouvoir les mêmes images. Ne pas définir une adresse privée dans
  `NEXT_PUBLIC_API_URL`.
- Racines en lecture seule : `/tmp`, les uploads API et le cache Next doivent
  recevoir des volumes adaptés. Les fixtures utilisent des tmpfs ; le cluster
  doit conserver les uploads sur stockage durable et tester leur restauration.
- La licence MIT OpenTutor est conservée dans `/usr/share/licenses/mentor` ;
  les notices npm disponibles sont collectées, y compris le manifeste des
  packages installés. La notice OFL Space Grotesk reste distribuée sous
  `/licenses/space-grotesk/OFL.txt`. Les métadonnées et licences Python restent
  présentes avec les distributions installées. Cela ne vaut pas audit juridique
  exhaustif de toutes les dépendances.

## Essai fermé des images

```sh
MENTOR_API_TEST_IMAGE=mentor-api:qualification-work \
MENTOR_WEB_TEST_IMAGE=mentor-web:qualification-work \
python scripts/test_postgres.py
```

Le test ajoute au PostgreSQL jetable une API en configuration production et un
frontend standalone, sans port publié. Les images sont non root, sans capacités,
avec racine en lecture seule. Frontend/API communiquent sur un réseau Docker
interne ; PostgreSQL reste accessible uniquement par socket privé. Le test
vérifie le proxy, le refus d'accès anonyme, le schéma migré et les notices. Aucun
serveur d'inférence n'est autorisé dans cette fixture : une readiness 503 est
**attendue** et ne prouve pas une qualification fonctionnelle du modèle.

Les tags `qualification-work` servent seulement à la validation locale. Une
release doit être reconstruite à partir d'un commit figé, publiée dans un
registre autorisé et référencée par les digests réellement publiés. Aucune image
n'a été publiée et aucun déploiement ne découle de ces commandes de test.
