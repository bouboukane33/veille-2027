# Identité visuelle CCR 2026

L'interface reprend les références digitales du document « CCR — Charte graphique 2026 » fourni pour ce projet : palette prioritaire page 12, palette secondaire page 13, typographie page 17.

| Usage | Référence |
| --- | --- |
| Bleu CCR, navigation et actions principales | `#002B3B` |
| Gris 1, textes et variations du bleu | `#2D515E` |
| Gris 2 | `#9BB9BE` |
| Gris 3, contours et surfaces | `#C6D3D7` |
| Gris 4 | `#DDE3E8` |
| Gris 5, fond de page | `#F0F3F5` |
| Jaune 1, accents ponctuels | `#D9F551` |
| Jaune 2 | `#E8FF98` |

Les graphiques utilisent aussi des nuances de la palette secondaire, dont `#1E7DCC`. La couleur d'une série n'indique pas une affiliation politique.

Albert Sans est embarquée avec l'application via le paquet épinglé `@fontsource-variable/albert-sans`. Le navigateur ne dépend pas d'un appel à Google Fonts. La licence SIL Open Font License est distribuée dans `web/public/fonts/AlbertSans-OFL.txt`.

## Portraits

`web/src/portraits.ts` associe les noms des personnalités à des assets locaux et aux informations de crédit : auteur, licence, lien vers la licence et photographie originale. Les crédits des entrées disponibles sont présentés dans « Sources & méthode ». L'image est décorative pour les lecteurs d'écran, car le nom apparaît immédiatement à côté ; les initiales restent disponibles si une image ne peut pas être chargée.

Ajouter uniquement une photographie vérifiée de la personne, avec une licence autorisant cet usage et les attributions correspondantes. Le registre reste indépendant du snapshot Supabase : une modification des portraits ne nécessite pas de nouvelle collecte et ne modifie pas les données réelles. Les personnalités suivies ne sont pas automatiquement présentées comme des candidats officiellement déclarés.
