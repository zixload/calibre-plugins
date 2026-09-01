# Developing

Notes for working on the plugins themselves. Users installing a plugin do not
need any of this — see the plugin's own README.

## Building

```bash
python build.py                          # every plugin, into dist/
python build.py stylish-covers  # just one
```

Then, with calibre closed:

```bash
calibre-customize -a dist/stylish-covers.zip
calibre-customize -r "Stylish Covers"
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
prefixed with the plugin name, e.g. `stylish-covers-v1.0.2`.

## Releasing

One release per plugin, on its own tag, with its ZIP attached:

```bash
python build.py <plugin>
git tag -a <plugin>-vX.Y.Z -m "<Name> X.Y.Z" && git push origin <plugin>-vX.Y.Z
gh release create <plugin>-vX.Y.Z dist/<plugin>.zip --title "<Name> X.Y.Z" --notes "..."
```

Bump the version whenever the plugin's code changed since its last tag, so a
published ZIP always matches the tag it hangs from. The download links in the
READMEs point at the tagged asset, so they need updating at the same time —
`/releases/latest/` is useless here, since "latest" is whichever plugin was
released last.

---

---

# Stylish Covers

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
| `badges.py` | the personal mark: ornaments, placement, drawing | Pillow |
| `kobo_matching.py` | pairing library books with device books | nothing |
| `kobo_push.py` | finding the device, paths, calling the driver | calibre (device driver) |
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
python tools/test_kobo_matching.py        # 11 device matching cases, no device
```

The middle three need the plugin installed, since they import through
`calibre_plugins.stylish_covers`.

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
`user_presets` key of `%APPDATA%\calibre\plugins\stylish_covers.json`,
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


---

## Pushing covers to a Kobo

### Modules

| File | Role | Depends on |
|---|---|---|
| `__init__.py` | plugin declaration | `calibre.customize` |
| `action.py` | toolbar, menu, the push loop | calibre + Qt |
| `config.py` | persistent settings + configuration dialog | calibre + Qt |
| `pusher.py` | finding the device, paths, calling the driver | calibre (device driver) |
| `matching.py` | pairing library books with device books | nothing |

### What it leans on

The Kobo thumbnail format, the sizes per model and the ImageId lookup are
**not** reimplemented here. `pusher.push_cover` writes the calibre cover to a
temporary file and hands it to the KoboTouch driver:

```python
device._upload_cover(dirname, basename_without_extension, metadata, filepath,
                     uploadgrayscale, dithered_covers=..., keep_cover_aspect=...,
                     letterbox_fs_covers=..., png_covers=..., letterbox_color=...)
```

`_upload_cover` rather than the public `upload_cover`, because the public one
returns immediately when the driver's *Upload covers* option is off — and
pushing covers on demand is the whole point. That is the one calibre internal
this plugin depends on; `push_cover` checks it exists and reports plainly if a
future calibre drops it.

`metadata` needs a `cover` attribute holding a path to an image file. The
driver derives the ContentID from `filepath` and looks the ImageId up in the
device's `KoboReader.sqlite`.

### Tools

```bash
python tools/test_matching.py     # 11 matching cases, no calibre, no device
calibre-debug tools/gui_smoke.py  # dialog + the no-device error paths
calibre-debug tools/make_icon.py  # regenerates the icon
```

Everything except the final write to the device can be exercised without a
Kobo: `matching.py` is duck typed, so the device books are stand-in objects in
the tests.


---

---

# Metadata Tidy

## Architecture

| File | Role | Depends on |
|---|---|---|
| `__init__.py` | plugin declaration | `calibre.customize` |
| `action.py` | toolbar, menu, selection, undo | calibre + Qt |
| `config.py` | persistent settings + configuration dialog | calibre + Qt |
| `widgets.py` | the preview table | Qt |
| `backup.py` | undo store | calibre (config path) |
| `tidy.py` | library metadata to proposals, and back | calibre (db only) |
| `parser.py` | the title rules, the whole brain | nothing |

`parser.py` has no imports beyond `re`, and `tidy.py` needs a database object
but never the GUI, which is what lets both be tested from a script.

## Tools

```bash
python tools/test_parser.py                     # 41 rule cases, no calibre needed
python tools/test_parser.py --library "C:/..."  # dry run over a real library
calibre-debug tools/library_roundtrip.py        # throwaway library: propose,
                                                # apply, verify, undo, verify
calibre-debug tools/gui_smoke.py                # builds the dialogs
calibre-debug tools/make_icon.py                # regenerates the icon
```

`test_parser.py` loads `parser.py` straight from its path, so it runs on a
plain python with no calibre installed.

## Adding a title rule

Rules live in `PATTERNS` in `parser.py`, tried in order. Each regex must name
a `series` group and a `num` group, and may name a `sub` group for the
volume's own subtitle. The resulting title is the subtitle when there is one,
otherwise the series name.

Add the case to `POSITIVE` in `tools/test_parser.py`, and add anything the new
rule must **not** match to `NEGATIVE`. The negative list matters more than the
positive one: a plugin that invents a series is worse than one that misses a
few.

---

# Cross-Check

Unlike the other three, this is a **metadata source**, not an interface
action: the class in `__init__.py` subclasses
`calibre.ebooks.metadata.sources.base.Source` and is the plugin itself, with
no `actual_plugin` indirection.

| File | Role | Depends on |
|---|---|---|
| `__init__.py` | the Source: options, `identify`, `download_cover` | calibre |
| `providers.py` | one adapter per API, each returning Candidates | nothing |
| `candidates.py` | clustering, voting, merging, noise filtering | nothing |

Providers take a `fetch(url, data=None, headers=None)` callable rather than
importing anything, so the plugin passes a urllib fetcher and the tests pass
their own. A provider that fails, times out or changes shape returns nothing
and logs; it never takes the search down with it.

## Adding a source

Write a function `myapi(fetch, title, authors, log) -> [Candidate]` in
`providers.py`, then add `('mykey', 'Label', myapi, 'manga'|'book', enabled)`
to `PROVIDERS` and a matching `Option('use_mykey', 'bool', ...)` in
`__init__.py`. Keyless APIs only.

### Tools

```bash
python tools/test_merge.py            # 13 merging rules, no network
python tools/live_probe.py            # hits the real APIs on a sample
python tools/live_probe.py "a title"  # or on one title
```

`live_probe.py` loads `candidates.py` and `providers.py` straight from their
paths, so it runs on a plain python with no calibre installed.

## Notes on the APIs

- Google Books is excluded on purpose: keyless calls answer HTTP 429 from a
  shared anonymous quota.
- Kitsu speaks JSON:API and answers HTTP 406 unless the request asks for
  `application/vnd.api+json`.
- Jikan proxies MyAnimeList and returns HTTP 504 whenever MAL is unwell, which
  is why it ships disabled.
- NovelUpdates is not usable: it answers HTTP 403 behind Cloudflare.
