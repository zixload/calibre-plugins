# calibre-plugins

My [calibre](https://calibre-ebook.com/) plugins. One folder per plugin, one
installable ZIP per plugin.

**To install any of them**: download the ZIP below, then in calibre
**Preferences → Plugins → Load plugin from file** and pick it. calibre asks
which toolbars to put the button in — tick both the main toolbar and the one
shown when a device is connected, they are separate lists. Then **restart
calibre**.

Nothing else to install: everything the plugins need already ships with
calibre.

## Stylish Covers

Builds real webnovel / dark fantasy covers out of the artwork a book already
has and its metadata, and saves the result as the book cover.

![The four presets of Stylish Covers](stylish-covers/docs/presets-comparison.jpg)

<sub>The same illustration and the same metadata run through the four presets,
with no manual tweaking.</sub>

Four presets, automatic typography, automatic contrast behind the text, full
chinese / korean / japanese support, batch mode and one-click restore of the
previous cover.

It also **pushes the covers onto a connected Kobo** without resending the
books, so a cover change never costs you your reading position.

⬇ **[Download stylish-covers.zip (v2.1.0)](https://github.com/zixload/calibre-plugins/releases/download/stylish-covers-v2.1.0/stylish-covers.zip)**
 · [documentation](stylish-covers/)

## Metadata Tidy

Pulls the series name and the volume number out of titles that carry them
(`La guerre du pavot T1`, `Vagabond part 02`, `Vol. 1: Subtitle`) and fills the
Series and Series index fields, so sorting, grouping and cover generation have
something to work with.

Every change is shown in a preview table before anything is written, rows can
be unticked or corrected by hand, and one menu entry undoes the whole run. It
refuses to guess: a title without a volume marker is left strictly alone.

⬇ **[Download metadata-tidy.zip (v1.0.0)](https://github.com/zixload/calibre-plugins/releases/download/metadata-tidy-v1.0.0/metadata-tidy.zip)**
 · [documentation](metadata-tidy/)

## Cross-Check

A metadata source that queries several free APIs at once — AniList, MangaDex,
Kitsu, Open Library and the BnF — compares their answers, and feeds the result
into calibre's usual *Download metadata* dialog. No API key needed.

It exists because the sources calibre ships answer well for published books
and badly for manga, light novels and web novels: asked about *Lord of the
Mysteries*, Amazon offers a diet cookbook, while Cross-Check returns the right
work, its author and its original title 诡秘之主, confirmed by three sources.

Being a metadata source, it adds no toolbar button: it appears in
**Preferences → Metadata download**.

⬇ **[Download metadata-crosscheck.zip (v1.0.0)](https://github.com/zixload/calibre-plugins/releases/download/metadata-crosscheck-v1.0.0/metadata-crosscheck.zip)**
 · [documentation](metadata-crosscheck/)

## Goodreads Export

Writes a CSV that Goodreads' import page accepts: the exact column names it
expects, ratings halved from calibre's 0 to 10 scale, tags turned into
shelves, dates cleaned up and undefined ones left blank.

calibre exports CSV on its own, but with its own headers, its authors joined
by ampersands and its ratings on the wrong scale — which Goodreads rejects
without saying why.

⬇ **[Download goodreads-export.zip (v1.0.0)](https://github.com/zixload/calibre-plugins/releases/download/goodreads-export-v1.0.0/goodreads-export.zip)**
 · [documentation](goodreads-export/)

## Using them together

The plugins cover a chain, and **the order matters**.

| # | Step | Plugin | Why here |
|---|---|---|---|
| 1 | Extract the series and volume number from titles | **Metadata Tidy** | must run **first**: downloading metadata rewrites titles, and `Vagabond part 02` becomes `Vagabond`, taking the volume number with it |
| 2 | Fill authors, tags, description, publisher, year, cover | **Cross-Check**, through calibre's *Download metadata* | no online source knows how your files are split into volumes, which is why step 1 comes before |
| 3 | Build the covers | **Stylish Covers** | now that the series is filled in, presets can print it |
| 4 | Refresh the covers on the Kobo | **Stylish Covers** again | writes the thumbnails without resending the books |
| 5 | Publish the shelf on Goodreads | **Goodreads Export** | last, so the CSV carries the metadata the earlier steps filled in |

The two metadata plugins are complementary, not alternatives: Cross-Check
never returns a series or a volume number for manga and light novels — AniList
treats a whole manga as one work and cannot know that your file is volume 2 of
3. That information only exists in your own titles, which is what Metadata
Tidy reads.

---

Older versions are on the
[Releases](https://github.com/zixload/calibre-plugins/releases) page, and
building from source is covered in [DEVELOPING.md](DEVELOPING.md).

Requires calibre 6 or later. Tested on calibre 9.13 under Windows 11.
Licensed GPL-3.0, like calibre itself.
