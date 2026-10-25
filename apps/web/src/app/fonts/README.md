# Space Grotesk locale

Police variable originale (graisses 300–700), sans modification du binaire.
L'import `next/font/local` préserve `--font-space-grotesk` et `display: swap`,
et supprime le téléchargement Google Fonts pendant `next build`.

- Source figée : [google/fonts, e7db6ca](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/spacegrotesk).
- Fichier amont : `SpaceGrotesk[wght].ttf`, renommé localement `SpaceGrotesk.ttf`.
- Révision déclarée du projet de police : `03507d024a01282884232081fc6011c09ff4e849`.
- Licence : SIL Open Font License 1.1, copyright 2020 The Space Grotesk Project Authors.
- Notice originale conservée dans `public/licenses/space-grotesk/OFL.txt` pour
  être distribuée dans l'image frontend, qui copie le dossier `public/`.
- Empreintes du binaire et de la notice dans `SHA256SUMS`, vérifiables depuis
  la racine du dépôt avec `sha256sum -c apps/web/src/app/fonts/SHA256SUMS`.

La licence OFL de la police s'ajoute à la licence MIT du code OpenTutor ; elle
ne la remplace pas. Aucun accès sortant à Google Fonts n'est requis au build.

La notice conserve son texte et son copyright ; seules les fins de ligne et
les espaces en fin de ligne ont été normalisés pour les conventions Git.
