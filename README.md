# calibre-plugins

Mes plugins [calibre](https://calibre-ebook.com/). Un dossier par plugin, un
ZIP installable par plugin, un script de build commun.

Développés et testés sur **calibre 9.13 / Qt 6 / Python 3.14 / Pillow 12**,
sous Windows 11. Compatibles calibre 6 et supérieur.

![Les quatre presets de Stylish Cover Generator](stylish-cover-generator/docs/presets-comparison.jpg)

<sub>La même illustration et les mêmes métadonnées passées dans les quatre
presets de *Stylish Cover Generator*, sans aucun réglage manuel.</sub>

## Plugins

| Plugin | Version | Description |
|---|---|---|
| [stylish-cover-generator](stylish-cover-generator/) | 1.0.1 | Fabrique de vraies couvertures de webnovel / dark fantasy à partir de l'illustration existante du livre et de ses métadonnées. Quatre presets, typographie automatique, contraste automatique, support CJK complet. |

## Installation

```bash
python build.py                          # construit tous les plugins dans dist/
python build.py stylish-cover-generator  # ou un seul
```

Puis dans calibre : **Préférences → Extensions → Charger l'extension à partir
d'un fichier**, choisir le ZIP produit dans `dist/`, et redémarrer calibre.

En ligne de commande, pratique pendant le développement (calibre doit être
fermé) :

```bash
calibre-customize -a dist/stylish-cover-generator.zip
calibre-customize -r "Stylish Cover Generator"
```

## Ajouter un plugin au dépôt

```
<nom-du-plugin>/                                  <- tirets, c'est le nom du ZIP
├── README.md
├── <nom_du_package>/                             <- underscores, c'est le module
│   ├── __init__.py                               <- sous-classe de Plugin
│   ├── plugin-import-name-<nom_du_package>.txt   <- fichier vide, obligatoire
│   └── ...
└── tools/                                        <- scripts de dev, hors ZIP
```

`build.py` détecte tout seul les plugins : il cherche, dans chaque dossier de
premier niveau, un package contenant `__init__.py` **et** un marqueur
`plugin-import-name-*.txt`. Ce marqueur est ce qui autorise un plugin
multi-fichiers : sans lui calibre n'expose pas le paquet
`calibre_plugins.<nom_du_package>` et les imports échouent.

Le ZIP contient le **contenu** du package à sa racine ; `tools/`, `samples/` et
`__pycache__/` en sont exclus.

## Versions et tags

La version fait foi dans le `version = (x, y, z)` de `__init__.py` — c'est ce
que lit `build.py` et ce qu'affiche calibre. Les tags sont préfixés par le nom
du plugin, le dépôt en contenant plusieurs :

```
stylish-cover-generator-v1.0.0
```

## Licence

GPL-3.0, comme calibre lui-même.
