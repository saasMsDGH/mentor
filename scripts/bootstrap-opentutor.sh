#!/usr/bin/env bash
# Import reproductible d'OpenTutor dans le dépôt MENTOR.
# N'exécute ni build, ni test, ni push. À lancer depuis une copie de travail Git.
set -euo pipefail

UPSTREAM_URL="https://github.com/zijinz456/OpenTutor.git"
UPSTREAM_COMMIT="2d2c003654cfbc90c173c9db6867ae65a65e8313"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "$ROOT/.git" ]]; then
  echo "ERREUR : $ROOT n'est pas un clone Git du dépôt MENTOR." >&2
  exit 1
fi
if [[ -e "$ROOT/apps/api/main.py" || -e "$ROOT/apps/web/package.json" ]]; then
  echo "ERREUR : du code applicatif est déjà présent. Import interrompu sans écrasement." >&2
  exit 1
fi
for tool in git tar mktemp; do
  command -v "$tool" >/dev/null || { echo "Outil manquant : $tool" >&2; exit 1; }
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone --quiet "$UPSTREAM_URL" "$TMP/opentutor"
git -C "$TMP/opentutor" checkout --quiet --detach "$UPSTREAM_COMMIT"
ACTUAL="$(git -C "$TMP/opentutor" rev-parse HEAD)"
[[ "$ACTUAL" == "$UPSTREAM_COMMIT" ]] || { echo "Commit inattendu : $ACTUAL" >&2; exit 1; }

# Préserver le README, les décisions et la roadmap MENTOR.
# Importer les autres sources d'OpenTutor, y compris sa licence MIT.
tar -C "$TMP/opentutor" --exclude='./.git' --exclude='./README.md' --exclude='./docs' -cf - . | tar -C "$ROOT" -xf -

# Conserver les documents amont séparément pour éviter de confondre les deux projets.
mkdir -p "$ROOT/docs/upstream/opentutor"
cp -a "$TMP/opentutor/docs/." "$ROOT/docs/upstream/opentutor/"
cp "$TMP/opentutor/README.md" "$ROOT/docs/upstream/opentutor/README.md"
printf '%s\n' "$UPSTREAM_COMMIT" > "$ROOT/docs/upstream/opentutor/UPSTREAM_COMMIT"

echo "OpenTutor importé au commit $ACTUAL."
echo "Inspecter git status, vérifier les licences, tester et committer séparément."
echo "Ne pas exposer docker-compose.yml en réseau : AUTH_ENABLED=false par défaut, Docker socket monté."
