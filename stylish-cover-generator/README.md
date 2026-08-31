# Stylish Cover Generator

Plugin calibre qui fabrique de vraies couvertures de webnovel / dark fantasy à
partir de l'illustration que le livre possède déjà (ou de n'importe quelle
image de votre disque) et de ses métadonnées.

Testé sur **calibre 9.13 / Qt 6 / Python 3.14 / Pillow 12** sous Windows 11.
Compatible calibre 6 et supérieur.

## Exemples

![Les quatre presets](docs/presets-comparison.jpg)

<sub>Une seule illustration, les mêmes métadonnées, les quatre presets aux
réglages par défaut. `asian_fantasy` n'affiche sa colonne verticale que si un
titre asiatique est renseigné, sans quoi sa composition reste proche de
`dark_fantasy`.</sub>

<table>
<tr>
<td width="45%"><img src="docs/cover-dark-fantasy-hugo.png" alt="Le dernier jour d'un condamne, preset Dark Fantasy"></td>
<td>

Preset `dark_fantasy` sur un fond clair et texturé : le contraste automatique
a détecté la luminosité derrière le bloc de texte et renforcé l'ombre et le
dégradé, sans assombrir l'illustration elle-même.

Le titre s'est réparti tout seul sur trois lignes équilibrées, le filet doré
sépare le titre de l'auteur.

</td>
</tr>
</table>

![La fenetre d'apercu](docs/preview-dialog.png)

<sub>La fenêtre d'aperçu : rendu instantané à gauche, métadonnées et réglages
rapides à droite. Ici les intensités d'effets ont été poussées à la main
(ombre 140 %, dégradé 166 %) avant application.</sub>

## Les presets

| Preset | Rendu |
|---|---|
| `dark_fantasy` | illustration dominante, titre serif dans le tiers inférieur, filet doré, ombre douce (type *Reverend Insanity*) |
| `shadow_slave` | titre énorme en haut, typo bold, contour léger, drop shadow prononcée, auteur en bas |
| `asian_fantasy` | titre latin en bas, caractères chinois/coréens en colonne verticale sur le côté (wuxia / xianxia) |
| `minimal` | titre propre, auteur, quasiment aucun effet, priorité absolue à l'illustration |

Points clés :

- **jamais de déformation** : l'image est mise à l'échelle pour couvrir le
  canvas puis recadrée (crop intelligent avec biais vertical configurable) ;
- **sortie normalisée 2:3**, 1600 × 2400 px par défaut ;
- **taille de titre automatique** : recherche dichotomique de la plus grande
  taille qui tient en 1, 2 ou 3 lignes, avec équilibrage des lignes ;
- **contraste automatique** : la luminosité réelle du fond est mesurée
  *derrière chaque bloc de texte*, et l'ombre / le contour / le dégradé ne sont
  renforcés que là où c'est nécessaire ;
- **Unicode complet** : chaîne de fallback CJK par caractère (coréen, chinois
  simplifié et traditionnel, japonais), aucune police propriétaire n'est
  distribuée avec le plugin ;
- **sauvegarde des anciennes couvertures** : `Restore previous cover` et
  `Restore original cover`, y compris après un redémarrage de calibre.

---

## 1. Installation

Ce plugin fait partie du dépôt [zixload/calibre-plugins](https://github.com/zixload/calibre-plugins).

### Depuis le ZIP

1. Construire le ZIP (voir §5) ou le récupérer dans les *Releases* du dépôt.
2. Dans calibre : **Préférences → Extensions → Charger l'extension à partir
   d'un fichier** (*Preferences → Plugins → Load plugin from file*).
3. Choisir `stylish-cover-generator.zip`.
4. Accepter d'ajouter le bouton à la barre d'outils, puis **redémarrer
   calibre**.

### En ligne de commande (pratique pendant le développement)

```bash
calibre-customize -a dist/stylish-cover-generator.zip   # installer / mettre à jour
calibre-customize -r "Stylish Cover Generator"          # désinstaller
```

Calibre doit être fermé, sinon la nouvelle version ne sera prise en compte
qu'au prochain démarrage.

### Dépendances

Aucune : Pillow est déjà fourni avec calibre. Le plugin n'installe rien et
n'accède pas au réseau.

---

## 2. Utilisation

Sélectionner un ou plusieurs livres, puis utiliser le bouton **Stylish Covers**
de la barre d'outils :

| Entrée de menu | Effet |
|---|---|
| **Generate stylish covers** | génère directement avec les réglages enregistrés, pour tous les livres sélectionnés, avec barre de progression annulable |
| **Preview…** | ouvre la fenêtre d'aperçu (c'est aussi l'action du clic direct sur le bouton) |
| **Generate from a chosen image…** | demande une image sur le disque et l'utilise comme illustration à la place de la couverture actuelle |
| **Restore previous cover** | remet la couverture remplacée lors de la dernière génération |
| **Restore original cover** | remet la couverture d'avant la toute première génération |
| **Settings…** | ouvre la configuration |

### La fenêtre d'aperçu

- l'aperçu est rendu en basse résolution (440 px de large) donc instantané, et
  utilise exactement le même moteur que la sortie finale ;
- titre, auteur, série et titre asiatique sont éditables pour ce livre
  uniquement, sans toucher aux métadonnées de la bibliothèque ;
- **Change image…** remplace l'illustration de ce livre par n'importe quel
  fichier ; **Reset** revient à la couverture du livre ;
- `<` et `>` naviguent dans la sélection ;
- **Apply** applique au livre affiché, **Apply to all** à toute la sélection
  (les réglages rapides modifiés sont enregistrés dans les deux cas).

### Génération par lot

`Generate stylish covers` traite toute la sélection. Au-delà de 5 livres une
confirmation est demandée. Chaque couverture remplacée est sauvegardée avant
écrasement (si l'option est active), donc un lot raté se rattrape avec
`Restore previous cover` sur la même sélection.

Compter environ **0,5 s par couverture** en 1600 × 2400.

---

## 3. Ajouter ses propres polices

Aucune police n'est distribuée avec le plugin, pour des raisons de licence.
Par défaut le plugin choisit automatiquement une police installée sur le
système (Constantia/Georgia pour les serif, Bahnschrift/Segoe pour le display,
Malgun Gothic / YaHei / Yu Gothic pour le CJK).

Pour utiliser les vôtres : **Settings → Fonts**, puis choisir un fichier
`.ttf` / `.otf` (les `.ttc` / `.otc` fonctionnent aussi) pour :

- **Title font** — le titre ;
- **Author font** — auteur et série ;
- **CJK font** — chinois / coréen / japonais.

Le bouton **Check fonts** affiche les polices réellement retenues et la chaîne
de fallback CJK.

### Comment fonctionne le fallback

Le plugin lit la table `cmap` de chaque fichier de police pour connaître les
caractères réellement couverts (aucune dépendance externe) :

1. si une seule police de la chaîne CJK couvre **tout** le texte asiatique,
   elle est utilisée partout — c'est ce qui évite d'avoir deux graisses
   différentes dans un même mot ;
2. sinon le remplacement se fait **caractère par caractère**, en descendant la
   chaîne ;
3. un caractère absent de la police de titre (un idéogramme dans un titre
   latin, par exemple) est automatiquement dessiné avec la police CJK.

Conséquence pratique : une police display latine sans glyphes chinois reste
parfaitement utilisable comme *Title font*.

---

## 4. Créer / modifier des presets

Trois niveaux, du plus simple au plus complet.

### a. Styles enregistrés (dans l'interface)

**Settings → Style → Saved styles → Save current…** mémorise sous un nom le
preset choisi, les positions, les tailles et les intensités d'effets.
`Load` les rappelle, `Delete` les supprime. C'est le moyen normal de garder
plusieurs configurations (une par collection, par exemple).

### b. Presets utilisateur (JSON)

La clé `user_presets` du fichier de configuration accepte des presets complets
qui héritent d'un preset intégré via `base`. Le fichier se trouve dans :

```
%APPDATA%\calibre\plugins\stylish_cover_generator.json
```

Exemple — un *Dark Fantasy* rouge sang, titre plus haut, sans filet :

```json
{
  "user_presets": {
    "blood_fantasy": {
      "label": "Blood Fantasy",
      "base": "dark_fantasy",
      "groups": [
        {"anchor": "bottom", "edge": 0.80, "align": "center", "margin": 0.10,
         "order": ["series", "title", "author", "asian"]}
      ],
      "title": {"color": "#F3E3E3", "size": 0.118},
      "series": {"color": "#9E2B2B"},
      "rule": {"enabled": false},
      "scrims": [{"side": "bottom", "extent": 0.62, "alpha": 0.74, "curve": 1.9}]
    }
  }
}
```

Le preset apparaît alors dans la liste, suffixé `(custom)`. La fusion est
récursive : on ne redéclare que ce que l'on change.

### c. Presets intégrés (code)

Ajouter un dictionnaire dans [`presets.py`](stylish_cover_generator/presets.py)
et l'ajouter à `BUILTIN_PRESETS`. Structure :

| Clé | Rôle |
|---|---|
| `image` | `focus` (`top`/`upper`/`center`/`lower`/`bottom`), `zoom`, `darken`, `saturation`, `contrast`, `vignette`, `mode` (`fill` ou `contain`) |
| `scrims` | liste de dégradés : `side` (`top`/`bottom`/`left`/`right`), `extent`, `alpha`, `curve` |
| `groups` | piles de blocs : `anchor` (`top`/`center`/`bottom`), `edge` (fraction de la hauteur), `align`, `margin`, `order` |
| `title`, `author`, `series`, `asian` | `size`, `gap`, `tracking`, `line_spacing`, `case`, `color`, `max_lines`, `max_height` |
| `rule` | filet décoratif : `enabled`, `width`, `thickness`, `gap`, `color`, `opacity` |
| `effects` | par élément : `shadow`, `shadow_offset`, `shadow_blur`, `stroke`, `stroke_color`, `glow`, `glow_color`, `glow_radius` |

**Toutes les tailles, marges et épaisseurs sont des fractions de la largeur du
canvas**, et les positions verticales des fractions de la hauteur : un preset
rend donc à l'identique quelle que soit la résolution de sortie.

Pour vérifier un preset sans lancer calibre :

```bash
calibre-debug tools/render_demo.py samples
```

(depuis ce dossier) qui écrit un exemple par preset sur fond sombre et sur
fond clair.

---

## 5. Construire le ZIP

Depuis la **racine du dépôt** :

```bash
python build.py stylish-cover-generator   # ce plugin seul
python build.py                           # tous les plugins du dépôt
```

produit `dist/stylish-cover-generator.zip`. Le script vérifie la présence des
deux fichiers indispensables et exclut `tools/`, `samples/`, `__pycache__/` et
les `.pyc`.

Le ZIP contient le **contenu** de `stylish_cover_generator/` à sa racine :

```
__init__.py                                     <- classe InterfaceActionBase
plugin-import-name-stylish_cover_generator.txt  <- fichier vide, obligatoire
action.py  config.py  generator.py  widgets.py
presets.py  textfx.py  imageops.py  fonts.py  backup.py
images/icon.png
```

Le fichier `plugin-import-name-*.txt` est ce qui autorise un plugin
multi-fichiers : sans lui, calibre ne sait pas exposer le paquet
`calibre_plugins.stylish_cover_generator` et les imports échouent.

Outils annexes, à lancer depuis ce dossier (`tools/` n'est jamais inclus dans
le ZIP) :

```bash
calibre-debug tools/make_icon.py          # régénère images/icon.png
calibre-debug tools/render_demo.py        # un exemple par preset
calibre-debug tools/edge_cases.py         # 40 rendus de métadonnées hostiles
calibre-debug tools/gui_smoke.py          # construit les dialogues, sans calibre
calibre-debug tools/library_roundtrip.py  # bibliothèque jetable : lecture,
                                          # génération, sauvegarde, restauration
```

Les trois derniers nécessitent que le plugin soit installé, puisqu'ils passent
par `calibre_plugins.stylish_cover_generator`.

---

## Architecture

Les trois couches sont strictement séparées ; seule la première connaît
calibre, seule la deuxième connaît Qt, et la troisième ne connaît que Pillow.

| Fichier | Rôle | Dépend de |
|---|---|---|
| `__init__.py` | déclaration du plugin | `calibre.customize` |
| `action.py` | barre d'outils, menu, base de données, lot | calibre + Qt |
| `config.py` | réglages persistants + dialogue de configuration | calibre + Qt |
| `widgets.py` | widgets réutilisables, fenêtre d'aperçu | Qt |
| `backup.py` | sauvegarde/restauration des couvertures | calibre (chemin de config) |
| `generator.py` | orchestration du rendu, mise en page, contraste auto | Pillow |
| `presets.py` | données des presets | — |
| `textfx.py` | césure, ajustement de taille, effets de texte, vertical | Pillow |
| `imageops.py` | crop/resize, étalonnage, dégradés, mesure de luminance | Pillow |
| `fonts.py` | découverte des polices, lecture de `cmap`, fallback | Pillow |

Conséquence : `generator.py` et ses dépendances s'utilisent tels quels hors de
calibre (c'est ce que fait `tools/render_demo.py`).

---

## Notes

- **Aucune traduction n'est inventée.** Le titre asiatique vient soit d'une
  colonne personnalisée que vous avez remplie (`#original_title` par défaut),
  soit d'un texte saisi à la main dans les réglages ou dans l'aperçu.
- Les modèles calibre sont acceptés pour le titre et l'auteur
  (`Settings → Metadata`), donc `{title}`, `{series}`, `{#original_title}` et
  les fonctions du langage de modèles fonctionnent.
- Les sauvegardes vivent dans
  `%APPDATA%\calibre\plugins\stylish_cover_generator_backups\`. Les
  couvertures *précédentes* sont limitées à 800 fichiers (les plus anciennes
  sont purgées) ; les couvertures *originales* ne sont jamais purgées.

---

## Licence

GPL-3.0, comme calibre. Aucune police n'est distribuée avec le plugin.
