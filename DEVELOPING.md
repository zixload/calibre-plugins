# Developing

Notes for working on the plugins themselves. Users installing a plugin do not
need any of this — see the plugin's own README.

## Building

```bash
python build.py                          # every plugin, into dist/
python build.py stylish-cover-generator  # just one
```

Then, with calibre closed:

```bash
calibre-customize -a dist/stylish-cover-generator.zip
calibre-customize -r "Stylish Cover Generator"
```

## Repository layout

```
<plugin-name>/                                  <- dashes, this names the ZIP
├── README.md
├── <package_name>/                             <- underscores, this is the module
│   ├── __init__.py                             <- Plugin subclass
│   ├── plugin-import-name-<package_name>.txt   <- empty file, mandatory
│   └── ...
└── tools/                                      <- dev scripts, kept out of the ZIP
```

`build.py` discovers plugins on its own: in every top level folder it looks
for a package holding `__init__.py` **and** a `plugin-import-name-*.txt`
marker. That marker is what allows a multi-file plugin — without it calibre
does not expose the `calibre_plugins.<package_name>` package and the imports
fail. The ZIP holds the content of the package at its root; `tools/`,
`samples/` and `__pycache__/` are excluded.

The version of record is `version = (x, y, z)` in `__init__.py`. Tags are
prefixed with the plugin name, e.g. `stylish-cover-generator-v1.0.1`.

---

# Stylish Cover Generator

## Architecture

Three strictly separated layers: only the first knows calibre, only the
second knows Qt, and the third knows nothing but Pillow.

| File | Role | Depends on |
|---|---|---|
| `__init__.py` | plugin declaration | `calibre.customize` |
| `action.py` | toolbar, menu, database, batch | calibre + Qt |
| `config.py` | persistent settings + configuration dialog | calibre + Qt |
| `widgets.py` | reusable widgets, preview window | Qt |
| `backup.py` | cover backup and restore | calibre (config path) |
| `generator.py` | render orchestration, layout, auto contrast | Pillow |
| `presets.py` | preset data | — |
| `textfx.py` | wrapping, size fitting, text effects, vertical text | Pillow |
| `imageops.py` | crop/resize, grading, gradients, luminance probing | Pillow |
| `fonts.py` | font discovery, `cmap` reading, fallback | Pillow |

`generator.py` and its dependencies run as-is outside calibre, which is what
`tools/render_demo.py` relies on.

## Tools

Run from the plugin folder:

```bash
calibre-debug tools/render_demo.py        # one example per preset, dark and light
calibre-debug tools/edge_cases.py         # 40 renders of hostile metadata
calibre-debug tools/gui_smoke.py          # builds the dialogs, without calibre
calibre-debug tools/library_roundtrip.py  # throwaway library: read, generate,
                                          # back up, restore
calibre-debug tools/make_icon.py          # regenerates images/icon.png
```

The middle three need the plugin installed, since they import through
`calibre_plugins.stylish_cover_generator`.

## Preset format

A preset is plain data. **Every size, margin and thickness is a fraction of
the canvas width**, and vertical positions are fractions of the height, so a
preset renders identically at any output resolution.

| Key | Role |
|---|---|
| `image` | `focus` (`top`/`upper`/`center`/`lower`/`bottom`), `zoom`, `darken`, `saturation`, `contrast`, `vignette`, `mode` (`fill` or `contain`) |
| `scrims` | list of gradients: `side` (`top`/`bottom`/`left`/`right`), `extent`, `alpha`, `curve` |
| `groups` | stacks of blocks: `anchor` (`top`/`center`/`bottom`), `edge`, `align`, `margin`, `order` |
| `title`, `author`, `series`, `asian` | `size`, `gap`, `tracking`, `line_spacing`, `case`, `color`, `max_lines`, `max_height` |
| `rule` | decorative rule: `enabled`, `width`, `thickness`, `gap`, `color`, `opacity` |
| `effects` | per element: `shadow`, `shadow_offset`, `shadow_blur`, `stroke`, `stroke_color`, `glow`, `glow_color`, `glow_radius` |

New built-in presets go in `presets.py` and into `BUILTIN_PRESETS`.

A preset can also be defined without touching the code, through the
`user_presets` key of `%APPDATA%\calibre\plugins\stylish_cover_generator.json`,
inheriting from a built-in one via `base`. Merging is recursive, so only the
keys you change need to be declared:

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

Such a preset shows up in the list suffixed `(custom)`.

## Font fallback

`fonts.py` reads the `cmap` table of each font file to know which codepoints
it really covers, with no external dependency. If a single font of the CJK
chain covers all of the Asian text it is used throughout — mixing two faces
inside one word looks wrong. Otherwise substitution happens character by
character down the chain.
